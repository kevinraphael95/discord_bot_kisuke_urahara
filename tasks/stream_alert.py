# ================================================================================
# 📌 stream_alert.py — Notifications Twitch (lives) + YouTube (nouvelles vidéos)
# Objectif : Suivre autant de chaînes que voulu, par serveur, chacune avec son
#            salon d'annonce et son rôle à ping (optionnel)
# Catégorie : Tasks / Fun
# Accès : Task automatique — commande !!notif réservée aux administrateurs
#         (alias : !!streamalert)
# Cooldown : /
# ================================================================================
# ⚙️ Variables .env :
#   ENABLE_STREAM_ALERT=True        → active les boucles (à mettre UNIQUEMENT sur la tablette)
#   TWITCH_CLIENT_ID=...            → dev.twitch.tv/console (facultatif : sans ça, YouTube seul)
#   TWITCH_CLIENT_SECRET=...        → idem (New Secret)
#   (YouTube : aucune clé nécessaire, on lit les flux RSS publics)
#
# 🗄️ Table créée automatiquement dans database/reiatsu.db :
#   notif_follows (id, guild_id, platform, handle, display, channel_id, role_id,
#                  last_id, last_published, fail_count)
#     platform       = 'twitch' | 'youtube'
#     handle         = pseudo Twitch (minuscules) | ID de chaîne YouTube (UC...)
#     last_id        = dernier stream / dernière vidéo annoncé(e) (évite les doublons)
#     last_published = date de la dernière vidéo YouTube annoncée (évite les
#                      ré-annonces si une vidéo est supprimée)
#     fail_count     = échecs d'envoi consécutifs (salon inaccessible)
#
# 🛠️ Commandes (admin) :
#   !!notif                                          → liste + aide
#   !!notif add twitch <pseudo> #salon [@role]
#   !!notif add youtube <@chaîne | lien | id> #salon [@role]
#   !!notif remove <id>                              → l'id est visible dans la liste
#   !!notif list
# ================================================================================

# ================================================================================
# 📦 Imports nécessaires
# ================================================================================
import logging
import os
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import aiohttp
import discord
from discord.ext import commands, tasks

from utils.discord_utils import safe_send
from utils.init_db import get_conn

log = logging.getLogger(__name__)

# ================================================================================
# ⚙️ Paramètres globaux
# ================================================================================
TWITCH_INTERVAL = 60        # secondes entre deux vérifs Twitch
YOUTUBE_INTERVAL = 300      # secondes entre deux vérifs YouTube (RSS, pas de quota)

MAX_FOLLOWS_PER_GUILD = 25  # garde-fou par serveur
YT_MAX_AGE_HOURS = 48       # on n'annonce pas une vidéo plus vieille que ça
YT_MAX_BURST = 3            # max de vidéos annoncées d'un coup pour une chaîne
MAX_FAILS = 20              # échecs d'envoi consécutifs (Forbidden) avant suppression du follow

TOKEN_URL = "https://id.twitch.tv/oauth2/token"
STREAMS_URL = "https://api.twitch.tv/helix/streams"
USERS_URL = "https://api.twitch.tv/helix/users"
YT_FEED_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={}"

TWITCH_PURPLE = 0x9146FF
YOUTUBE_RED = 0xFF0000

# Cookies de consentement : évite la page "avant d'accéder à YouTube" (UE)
YT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    "Cookie": "CONSENT=YES+1; SOCS=CAI",
}
ATOM_NS = {
    "a": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
    "media": "http://search.yahoo.com/mrss/",
}

UC_RE = re.compile(r"UC[\w-]{22}")
TWITCH_LOGIN_RE = re.compile(r"^\w{1,25}$")

USAGE = (
    "📡 **Notifications Twitch / YouTube**\n"
    "• `!!notif add twitch <pseudo> #salon [@role]`\n"
    "• `!!notif add youtube <@chaîne | lien | id> #salon [@role]`\n"
    "• `!!notif remove <id>`\n"
    "• `!!notif list`"
)


# ================================================================================
# 🗄️ Helpers base de données
# ================================================================================
def _query(sql: str, args: tuple = ()) -> list[dict]:
    """Exécute une requête et renvoie les lignes sous forme de dicts."""
    conn = get_conn()
    try:
        cur = conn.execute(sql, args)
        rows = []
        if cur.description:
            cols = [c[0] for c in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        conn.commit()
        return rows
    finally:
        conn.close()


def _init_table():
    _query(
        """
        CREATE TABLE IF NOT EXISTS notif_follows (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id       INTEGER NOT NULL,
            platform       TEXT    NOT NULL,
            handle         TEXT    NOT NULL,
            display        TEXT,
            channel_id     INTEGER NOT NULL,
            role_id        INTEGER,
            last_id        TEXT,
            last_published TEXT,
            fail_count     INTEGER NOT NULL DEFAULT 0,
            UNIQUE (guild_id, platform, handle)
        )
        """
    )

    # Migration : ajoute les nouvelles colonnes sur une table déjà existante
    existing = {r["name"] for r in _query("PRAGMA table_info(notif_follows)")}
    if "last_published" not in existing:
        _query("ALTER TABLE notif_follows ADD COLUMN last_published TEXT")
    if "fail_count" not in existing:
        _query("ALTER TABLE notif_follows ADD COLUMN fail_count INTEGER NOT NULL DEFAULT 0")


def _all_follows(platform: str) -> list[dict]:
    return _query("SELECT * FROM notif_follows WHERE platform = ?", (platform,))


def _set_last(follow_id: int, last_id: str, published: datetime | None = None):
    """Mémorise la dernière annonce (et sa date pour YouTube)."""
    if published is not None:
        _query(
            "UPDATE notif_follows SET last_id = ?, last_published = ? WHERE id = ?",
            (str(last_id), published.isoformat(), follow_id),
        )
    else:
        _query("UPDATE notif_follows SET last_id = ? WHERE id = ?", (str(last_id), follow_id))


def _delete_follow(follow_id: int):
    _query("DELETE FROM notif_follows WHERE id = ?", (follow_id,))


def _parse_dt(value: str | None) -> datetime:
    try:
        dt = datetime.fromisoformat(value)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return datetime.now(timezone.utc)


def _parse_dt_or_none(value: str | None) -> datetime | None:
    try:
        dt = datetime.fromisoformat(value)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


# ================================================================================
# 🧠 Cog : StreamAlert
# ================================================================================
class StreamAlert(commands.Cog):
    """Annonce les lives Twitch et les nouvelles vidéos YouTube des chaînes suivies."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.session: aiohttp.ClientSession | None = None
        self.client_id = os.getenv("TWITCH_CLIENT_ID")
        self.client_secret = os.getenv("TWITCH_CLIENT_SECRET")
        self._token: str | None = None
        self._token_expires = 0.0

    @property
    def twitch_ok(self) -> bool:
        return bool(self.client_id and self.client_secret)

    # ──────────────────────────────────────────────────────────
    # 🔌 Cycle de vie
    # ──────────────────────────────────────────────────────────
    async def cog_load(self):
        _init_table()
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15))

        if os.getenv("ENABLE_STREAM_ALERT", "False").lower() != "true":
            log.info("[stream_alert] Désactivé (ENABLE_STREAM_ALERT != True).")
            return

        if self.twitch_ok:
            self.twitch_loop.start()
        else:
            log.warning("[stream_alert] Clés Twitch manquantes : Twitch désactivé, YouTube seul.")
        self.youtube_loop.start()

    async def cog_unload(self):
        self.twitch_loop.cancel()
        self.youtube_loop.cancel()
        if self.session and not self.session.closed:
            await self.session.close()

    async def cog_check(self, ctx: commands.Context) -> bool:
        if ctx.guild is None:
            raise commands.NoPrivateMessage()
        if not ctx.author.guild_permissions.administrator:
            raise commands.MissingPermissions(["administrator"])
        return True

    # ──────────────────────────────────────────────────────────
    # 🔑 Twitch : token + requêtes
    # ──────────────────────────────────────────────────────────
    async def _get_token(self, force: bool = False) -> str:
        if not force and self._token and time.time() < self._token_expires - 60:
            return self._token

        async with self.session.post(
            TOKEN_URL,
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "client_credentials",
            },
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()

        self._token = data["access_token"]
        self._token_expires = time.time() + data.get("expires_in", 3600)
        return self._token

    async def _twitch_get(self, url: str, params: list[tuple[str, str]]) -> dict:
        for attempt in range(2):
            token = await self._get_token(force=(attempt == 1))
            headers = {"Client-Id": self.client_id, "Authorization": f"Bearer {token}"}
            async with self.session.get(url, params=params, headers=headers) as resp:
                if resp.status == 401 and attempt == 0:
                    continue  # token expiré/révoqué → on en redemande un
                resp.raise_for_status()
                return await resp.json()
        return {}

    async def _twitch_lives(self, logins: list[str]) -> dict[str, dict]:
        """Renvoie {login: stream} pour les chaînes actuellement en live (100 max par requête)."""
        lives: dict[str, dict] = {}
        for i in range(0, len(logins), 100):
            chunk = logins[i : i + 100]
            params = [("user_login", l) for l in chunk] + [("first", "100")]
            data = await self._twitch_get(STREAMS_URL, params)
            for s in data.get("data", []):
                if s.get("type") == "live":
                    lives[s["user_login"].lower()] = s
        return lives

    async def _twitch_user(self, login: str) -> dict | None:
        data = await self._twitch_get(USERS_URL, [("login", login)])
        users = data.get("data", [])
        return users[0] if users else None

    # ──────────────────────────────────────────────────────────
    # 📺 YouTube : flux RSS + résolution des chaînes
    # ──────────────────────────────────────────────────────────
    async def _fetch_feed(self, channel_id: str) -> tuple[str, list[dict]]:
        """Renvoie (nom de la chaîne, vidéos de la plus récente à la plus ancienne)."""
        async with self.session.get(YT_FEED_URL.format(channel_id), headers=YT_HEADERS) as resp:
            resp.raise_for_status()
            text = await resp.text()

        root = ET.fromstring(text)
        name = root.findtext("a:title", default="", namespaces=ATOM_NS)
        entries = []
        for en in root.findall("a:entry", ATOM_NS):
            vid = en.findtext("yt:videoId", namespaces=ATOM_NS)
            if not vid:
                continue
            link = en.find("a:link", ATOM_NS)
            thumb = en.find("media:group/media:thumbnail", ATOM_NS)
            entries.append(
                {
                    "id": vid,
                    "title": en.findtext("a:title", default="Sans titre", namespaces=ATOM_NS),
                    "url": link.get("href") if link is not None else f"https://www.youtube.com/watch?v={vid}",
                    "thumb": thumb.get("url") if thumb is not None else f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg",
                    "published": _parse_dt(en.findtext("a:published", namespaces=ATOM_NS)),
                }
            )
        return name, entries

    async def _resolve_youtube(self, query: str) -> tuple[str, str, list[dict]] | None:
        """Accepte un ID (UC...), un lien /channel/UC..., un @handle ou un lien de chaîne.
        Renvoie (channel_id, nom, vidéos) ou None si introuvable."""
        q = query.strip()
        cid = None

        m = UC_RE.search(q)
        if m and (q == m.group(0) or "/channel/" in q):
            cid = m.group(0)
        else:
            if q.startswith("http"):
                url = q
            elif q.startswith("@"):
                url = f"https://www.youtube.com/{q}"
            else:
                url = f"https://www.youtube.com/@{q}"

            host = (urlparse(url).hostname or "").lower()
            if not (host == "youtube.com" or host.endswith(".youtube.com")):
                return None

            try:
                async with self.session.get(url, headers=YT_HEADERS) as resp:
                    if resp.status != 200:
                        return None
                    html = await resp.text()
            except aiohttp.ClientError:
                return None

            m = (
                re.search(r'<link rel="canonical" href="https://www\.youtube\.com/channel/(UC[\w-]{22})"', html)
                or re.search(r'"externalId":"(UC[\w-]{22})"', html)
                or re.search(r'"channelId":"(UC[\w-]{22})"', html)
            )
            if not m:
                return None
            cid = m.group(1)

        try:
            name, entries = await self._fetch_feed(cid)
        except (aiohttp.ClientError, ET.ParseError):
            return None
        return cid, name or cid, entries

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
            _delete_follow(follow["id"])
            return False

        except discord.Forbidden:
            # Plus les droits : peut être temporaire, on compte les échecs
            fails = (follow.get("fail_count") or 0) + 1
            if fails >= MAX_FAILS:
                log.warning("[stream_alert] Salon %s inaccessible depuis trop longtemps → follow #%s retiré.",
                            follow["channel_id"], follow["id"])
                _delete_follow(follow["id"])
            else:
                follow["fail_count"] = fails
                _query("UPDATE notif_follows SET fail_count = ? WHERE id = ?", (fails, follow["id"]))
                # On ne log qu'au premier échec pour ne pas spammer
                if fails == 1:
                    log.warning("[stream_alert] Pas la permission d'écrire dans %s (follow #%s).",
                                follow["channel_id"], follow["id"])
            return False

        if not msg:
            return False

        # Succès : on remet le compteur d'échecs à zéro
        if follow.get("fail_count"):
            follow["fail_count"] = 0
            _query("UPDATE notif_follows SET fail_count = 0 WHERE id = ?", (follow["id"],))
        return True

    # ──────────────────────────────────────────────────────────
    # 🔁 Boucle Twitch
    # ──────────────────────────────────────────────────────────
    async def _check_twitch(self):
        follows = _all_follows("twitch")
        if not follows:
            return

        logins = sorted({f["handle"] for f in follows})
        lives = await self._twitch_lives(logins)

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
                _set_last(f["id"], stream["id"])
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
        follows = _all_follows("youtube")
        if not follows:
            return

        by_channel: dict[str, list[dict]] = {}
        for f in follows:
            by_channel.setdefault(f["handle"], []).append(f)

        for cid, group in by_channel.items():
            try:
                name, entries = await self._fetch_feed(cid)
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
        last_dt = _parse_dt_or_none(f.get("last_published"))

        # Nouvelles vidéos = plus récentes que la dernière annoncée.
        # On compare sur la DATE (et pas seulement l'ID) : si la dernière vidéo
        # annoncée est supprimée, on ne ré-annonce pas les anciennes.
        new = []
        for e in entries:  # de la plus récente à la plus ancienne
            if e["id"] == f["last_id"]:
                break
            if now - e["published"] > max_age:
                break
            if last_dt and e["published"] <= last_dt:
                break
            new.append(e)

        # On envoie dans l'ordre chronologique (la plus ancienne des nouvelles d'abord)
        for video in reversed(new[:YT_MAX_BURST]):
            ok = await self._announce(
                f,
                f"📺 **{author}** vient de publier une vidéo !",
                self._youtube_embed(video, author),
            )
            if not ok:
                return  # on réessaiera au prochain tour
            _set_last(f["id"], video["id"], video["published"])
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

    # ──────────────────────────────────────────────────────────
    # 🛠️ Commandes admin : !!notif [add | remove | list]
    # ──────────────────────────────────────────────────────────
    @commands.group(
        name="notif",
        aliases=["streamalert"],
        invoke_without_command=True,
        help="Gère les notifications Twitch (lives) et YouTube (vidéos).",
    )
    async def notif(self, ctx: commands.Context):
        await self._send_list(ctx, with_usage=True)

    @notif.command(name="list", aliases=["liste"])
    async def notif_list(self, ctx: commands.Context):
        await self._send_list(ctx)

    async def _send_list(self, ctx: commands.Context, with_usage: bool = False):
        rows = _query(
            "SELECT * FROM notif_follows WHERE guild_id = ? ORDER BY platform, display",
            (ctx.guild.id,),
        )
        lines = []
        for r in rows:
            icon = "🟣 Twitch" if r["platform"] == "twitch" else "📺 YouTube"
            role = f" • <@&{r['role_id']}>" if r["role_id"] else ""
            warn = " ⚠️" if r.get("fail_count") else ""
            lines.append(f"`#{r['id']}` {icon} — **{r['display'] or r['handle']}** → <#{r['channel_id']}>{role}{warn}")

        twitch_state = "🟢" if self.twitch_loop.is_running() else "🔴 (désactivé)"
        yt_state = "🟢" if self.youtube_loop.is_running() else "🔴 (désactivé)"
        body = "\n".join(lines) if lines else "*Aucune chaîne suivie sur ce serveur.*"
        text = f"{body}\n\nTwitch : {twitch_state} • YouTube : {yt_state}"
        if any(r.get("fail_count") for r in rows):
            text += "\n⚠️ = le bot n'arrive pas à écrire dans ce salon (permissions ?)"
        if with_usage:
            text = f"{USAGE}\n\n{text}"
        await safe_send(ctx.channel, text)

    @notif.command(name="add")
    async def notif_add(
        self,
        ctx: commands.Context,
        plateforme: str = None,
        cible: str = None,
        salon: str = None,
        role: str = None,
    ):
        if not (plateforme and cible and salon):
            return await safe_send(ctx.channel, USAGE)

        plateforme = plateforme.lower()
        if plateforme == "yt":
            plateforme = "youtube"
        if plateforme not in ("twitch", "youtube"):
            return await safe_send(ctx.channel, "❌ Plateforme inconnue : `twitch` ou `youtube`.")

        # --- Salon + rôle ---
        try:
            channel = await commands.TextChannelConverter().convert(ctx, salon)
            role_obj = await commands.RoleConverter().convert(ctx, role) if role else None
        except commands.BadArgument:
            return await safe_send(ctx.channel, "❌ Salon ou rôle introuvable.\n" + USAGE)

        # --- Garde-fou : nombre max de chaînes par serveur ---
        count = _query("SELECT COUNT(*) AS n FROM notif_follows WHERE guild_id = ?", (ctx.guild.id,))[0]["n"]

        # --- Résolution de la chaîne ---
        last_id = None
        last_published = None
        if plateforme == "twitch":
            if not self.twitch_ok:
                return await safe_send(ctx.channel, "❌ Twitch n'est pas configuré (clés manquantes dans le `.env`).")

            # Accepte "pseudo", "@pseudo", "twitch.tv/pseudo", "https://twitch.tv/pseudo?sr=a"...
            login = cible.strip().split("?")[0].split("#")[0].rstrip("/").split("/")[-1].lstrip("@").lower()
            if not TWITCH_LOGIN_RE.match(login):
                return await safe_send(ctx.channel, "❌ Pseudo Twitch invalide.")
            try:
                user = await self._twitch_user(login)
            except aiohttp.ClientError:
                return await safe_send(ctx.channel, "❌ Impossible de joindre l'API Twitch, réessaie plus tard.")
            if not user:
                return await safe_send(ctx.channel, f"❌ Chaîne Twitch `{login}` introuvable.")
            handle, display = user["login"].lower(), user["display_name"]

        else:
            res = await self._resolve_youtube(cible)
            if not res:
                return await safe_send(
                    ctx.channel,
                    "❌ Chaîne YouTube introuvable. Donne un `@handle`, un lien de chaîne ou un ID `UC...`.",
                )
            handle, display, entries = res
            # On "amorce" avec la dernière vidéo pour ne pas annoncer l'ancien contenu
            if entries:
                last_id = entries[0]["id"]
                last_published = entries[0]["published"].isoformat()

        exists = _query(
            "SELECT id FROM notif_follows WHERE guild_id = ? AND platform = ? AND handle = ?",
            (ctx.guild.id, plateforme, handle),
        )
        if not exists and count >= MAX_FOLLOWS_PER_GUILD:
            return await safe_send(ctx.channel, f"❌ Limite atteinte ({MAX_FOLLOWS_PER_GUILD} chaînes par serveur).")

        _query(
            """
            INSERT INTO notif_follows
                (guild_id, platform, handle, display, channel_id, role_id, last_id, last_published)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (guild_id, platform, handle) DO UPDATE SET
                display = excluded.display,
                channel_id = excluded.channel_id,
                role_id = excluded.role_id,
                fail_count = 0
            """,
            (ctx.guild.id, plateforme, handle, display, channel.id,
             role_obj.id if role_obj else None, last_id, last_published),
        )

        verbe = "mise à jour" if exists else "ajoutée"
        ping = f" (ping {role_obj.mention})" if role_obj else ""
        await safe_send(ctx.channel, f"✅ **{display}** ({plateforme}) {verbe} → {channel.mention}{ping}.")

    @notif.command(name="remove", aliases=["del", "delete", "supprimer"])
    async def notif_remove(self, ctx: commands.Context, follow_id: int = None):
        if follow_id is None:
            return await safe_send(ctx.channel, "Usage : `!!notif remove <id>` (l'id est dans `!!notif list`).")

        rows = _query(
            "SELECT display, handle FROM notif_follows WHERE id = ? AND guild_id = ?",
            (follow_id, ctx.guild.id),
        )
        if not rows:
            return await safe_send(ctx.channel, f"❌ Aucune chaîne avec l'id `#{follow_id}` sur ce serveur.")

        _query("DELETE FROM notif_follows WHERE id = ? AND guild_id = ?", (follow_id, ctx.guild.id))
        await safe_send(ctx.channel, f"🔕 **{rows[0]['display'] or rows[0]['handle']}** retirée.")


# ================================================================================
# 🔌 Setup
# ================================================================================
async def setup(bot: commands.Bot):
    await bot.add_cog(StreamAlert(bot))
