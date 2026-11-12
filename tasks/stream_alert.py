# ================================================================================
# 📌 stream_alert.py — Task : annonces Twitch (lives) + YouTube (nouvelles vidéos)
# Objectif : Boucles de fond qui vérifient les chaînes suivies et annoncent
#            les lives / nouvelles vidéos dans les salons configurés
# Catégorie : Tasks
# Accès : Automatique (aucune commande — voir commands/notif.py)
# Cooldown : /
# ================================================================================
# ⚙️ Variables .env :
#   ENABLE_STREAM_ALERT=True        → active les boucles (à mettre UNIQUEMENT sur la tablette)
#   TWITCH_CLIENT_ID=...            → dev.twitch.tv/console (facultatif : sans ça, YouTube seul)
#   TWITCH_CLIENT_SECRET=...        → idem
# ================================================================================

# ================================================================================
# 📦 Modules standards
# ================================================================================
import logging
import os
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

# ================================================================================
# 📦  Modules tiers
# ================================================================================
import aiohttp
import discord
from discord.ext import commands, tasks

# ================================================================================
# 📦 Modules internes
# ================================================================================
from utils.discord_anti429 import safe_send
from utils.stream_notif import (
    MAX_FAILS,
    TWITCH_INTERVAL,
    TWITCH_PURPLE,
    YOUTUBE_INTERVAL,
    YOUTUBE_RED,
    YT_MAX_AGE_HOURS,
    YT_MAX_BURST,
    StreamClient,
    all_follows,
    delete_follow,
    init_table,
    parse_dt_or_none,
    query,
    set_last,
)

# ================================================================================
# 🪵 Logger
# ================================================================================
log = logging.getLogger(__name__)

# ================================================================================
# 🧠 Cog : StreamAlertTask
# ================================================================================
class StreamAlertTask(commands.Cog):
    """Annonce les lives Twitch et les nouvelles vidéos YouTube des chaînes suivies."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.client = StreamClient()

    # ──────────────────────────────────────────────────────────
    # 🔌 Cycle de vie
    # ──────────────────────────────────────────────────────────
    async def cog_load(self):
        init_table()
        await self.client.start()

        if os.getenv("ENABLE_STREAM_ALERT", "False").lower() != "true":
            log.info("[stream_alert] Désactivé (ENABLE_STREAM_ALERT != True).")
            return

        if self.client.twitch_ok:
            self.twitch_loop.start()
        else:
            log.warning("[stream_alert] Clés Twitch manquantes : Twitch désactivé, YouTube seul.")
        self.youtube_loop.start()

    async def cog_unload(self):
        self.twitch_loop.cancel()
        self.youtube_loop.cancel()
        await self.client.close()

    # ──────────────────────────────────────────────────────────
    # 🎨 Embeds
    # ──────────────────────────────────────────────────────────
    @staticmethod
    def _twitch_embed(stream: dict, login: str) -> discord.Embed:
        name = stream.get("user_name") or login
        embed = discord.Embed(
            title=f"🔴 {name} est en live !",
            url=f"https://www.twitch.tv/{login}",
            description=stream.get("title") or "Pas de titre",
            color=TWITCH_PURPLE,
        )
        embed.add_field(name="🎮 Jeu", value=stream.get("game_name") or "Inconnu", inline=True)
        embed.add_field(name="👀 Viewers", value=str(stream.get("viewer_count", 0)), inline=True)

        thumb = stream.get("thumbnail_url")
        if thumb:
            thumb = thumb.replace("{width}", "1280").replace("{height}", "720")
            embed.set_image(url=f"{thumb}?t={int(time.time())}")  # ?t= évite le cache Discord
        return embed

    @staticmethod
    def _youtube_embed(video: dict, author: str) -> discord.Embed:
        embed = discord.Embed(
            title=video["title"],
            url=video["url"],
            description=f"📺 Nouvelle vidéo de **{author}**",
            color=YOUTUBE_RED,
            timestamp=video["published"],
        )
        embed.set_image(url=video["thumb"])
        return embed

    # ──────────────────────────────────────────────────────────
    # 📤 Envoi d'une annonce (renvoie True si le message est parti)
    # ──────────────────────────────────────────────────────────
    async def _announce(self, follow: dict, text: str, embed: discord.Embed) -> bool:
        try:
            channel = self.bot.get_channel(follow["channel_id"]) or await self.bot.fetch_channel(follow["channel_id"])
            mention = ""
            guild = getattr(channel, "guild", None)
            if follow["role_id"] and guild:
                role = guild.get_role(follow["role_id"])
                if role:
                    mention = f"{role.mention} "
            msg = await safe_send(channel, content=f"{mention}{text}", embed=embed)

        except discord.NotFound:
            # Salon supprimé : définitif, on retire le follow
            log.warning("[stream_alert] Salon %s supprimé → follow #%s retiré.",
                        follow["channel_id"], follow["id"])
            delete_follow(follow["id"])
            return False

        except discord.Forbidden:
            # Plus les droits : peut être temporaire, on compte les échecs
            fails = (follow.get("fail_count") or 0) + 1
            if fails >= MAX_FAILS:
                log.warning("[stream_alert] Salon %s inaccessible depuis trop longtemps → follow #%s retiré.",
                            follow["channel_id"], follow["id"])
                delete_follow(follow["id"])
            else:
                follow["fail_count"] = fails
                query("UPDATE notif_follows SET fail_count = ? WHERE id = ?", (fails, follow["id"]))
                if fails == 1:  # un seul log pour ne pas spammer
                    log.warning("[stream_alert] Pas la permission d'écrire dans %s (follow #%s).",
                                follow["channel_id"], follow["id"])
            return False

        if not msg:
            return False

        # Succès : on remet le compteur d'échecs à zéro
        if follow.get("fail_count"):
            follow["fail_count"] = 0
            query("UPDATE notif_follows SET fail_count = 0 WHERE id = ?", (follow["id"],))
        return True

    # ──────────────────────────────────────────────────────────
    # 🔁 Boucle Twitch
    # ──────────────────────────────────────────────────────────
    async def _check_twitch(self):
        follows = all_follows("twitch")
        if not follows:
            return

        logins = sorted({f["handle"] for f in follows})
        lives = await self.client.twitch_lives(logins)

        for f in follows:
            stream = lives.get(f["handle"])
            if stream is None:
                continue  # hors ligne : on garde last_id (pas de re-ping après micro-coupure)
            if str(stream["id"]) == f["last_id"]:
                continue  # déjà annoncé

            name = stream.get("user_name") or f["handle"]
            ok = await self._announce(
                f,
                f"🔴 **{name}** est en live sur Twitch !",
                self._twitch_embed(stream, f["handle"]),
            )
            if ok:
                set_last(f["id"], stream["id"])
                log.info("[stream_alert] Live %s annoncé (follow #%s).", stream["id"], f["id"])

    @tasks.loop(seconds=TWITCH_INTERVAL)
    async def twitch_loop(self):
        try:
            await self._check_twitch()
        except (aiohttp.ClientError, TimeoutError) as e:
            log.warning("[stream_alert] Twitch injoignable : %s", e)
        except Exception:
            log.exception("[stream_alert] Erreur pendant la vérification Twitch")

    @twitch_loop.before_loop
    async def _before_twitch_loop(self):
        await self.bot.wait_until_ready()

    # ──────────────────────────────────────────────────────────
    # 🔁 Boucle YouTube
    # ──────────────────────────────────────────────────────────
    async def _check_youtube(self):
        follows = all_follows("youtube")
        if not follows:
            return

        by_channel: dict[str, list[dict]] = {}
        for f in follows:
            by_channel.setdefault(f["handle"], []).append(f)

        for cid, group in by_channel.items():
            try:
                name, entries = await self.client.fetch_feed(cid)
            except (aiohttp.ClientError, TimeoutError, ET.ParseError) as e:
                log.warning("[stream_alert] Flux YouTube indisponible pour %s : %s", cid, e)
                continue
            except Exception:
                log.exception("[stream_alert] Erreur inattendue sur le flux YouTube %s", cid)
                continue
            if not entries:
                continue

            for f in group:
                await self._announce_videos(f, name or f["display"] or cid, entries)

    async def _announce_videos(self, f: dict, author: str, entries: list[dict]):
        now = datetime.now(timezone.utc)
        max_age = timedelta(hours=YT_MAX_AGE_HOURS)
        last_dt = parse_dt_or_none(f.get("last_published"))

        # Nouvelles vidéos = plus récentes que la dernière annoncée (comparaison
        # sur la DATE : si la dernière vidéo est supprimée, pas de ré-annonce).
        new = []
        for e in entries:  # de la plus récente à la plus ancienne
            if e["id"] == f["last_id"]:
                break
            if now - e["published"] > max_age:
                break
            if last_dt and e["published"] <= last_dt:
                break
            new.append(e)

        # Ordre chronologique : la plus ancienne des nouvelles d'abord
        for video in reversed(new[:YT_MAX_BURST]):
            ok = await self._announce(
                f,
                f"📺 **{author}** vient de publier une vidéo !",
                self._youtube_embed(video, author),
            )
            if not ok:
                return  # on réessaiera au prochain tour
            set_last(f["id"], video["id"], video["published"])
            f["last_id"] = video["id"]
            log.info("[stream_alert] Vidéo %s annoncée (follow #%s).", video["id"], f["id"])

    @tasks.loop(seconds=YOUTUBE_INTERVAL)
    async def youtube_loop(self):
        try:
            await self._check_youtube()
        except Exception:
            log.exception("[stream_alert] Erreur pendant la vérification YouTube")

    @youtube_loop.before_loop
    async def _before_youtube_loop(self):
        await self.bot.wait_until_ready()


# ================================================================================
# 🔌 Setup
# ================================================================================
async def setup(bot: commands.Bot):
    await bot.add_cog(StreamAlertTask(bot))
