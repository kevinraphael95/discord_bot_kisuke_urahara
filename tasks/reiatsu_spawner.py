# ────────────────────────────────────────────────────────────────────────────────
# 📌 reiatsu_spawner.py — Gestion du spawn des Reiatsu
# Objectif : Gérer l'apparition et la capture des Reiatsu sur les serveurs
# Catégorie : Reiatsu / RPG
# Accès : Tous
# Cooldown : Spawn auto toutes les X minutes (configurable par serveur)
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
import random
import time
import asyncio
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from discord.ext import commands, tasks
from utils.discord_utils import safe_send, safe_delete

# ────────────────────────────────────────────────────────────────────────────────
# ⚙️ Paramètres globaux
# ────────────────────────────────────────────────────────────────────────────────
CONFIG_PATH = Path("data/reiatsu_config.json")
with CONFIG_PATH.open("r", encoding="utf-8") as f:
    CONFIG = json.load(f)

SPAWN_LOOP_INTERVAL  = CONFIG["SPAWN_LOOP_INTERVAL"]
SUPER_REIATSU_CHANCE = CONFIG["SUPER_REIATSU_CHANCE"]
SUPER_REIATSU_GAIN   = CONFIG["SUPER_REIATSU_GAIN"]
NORMAL_REIATSU_GAIN  = CONFIG["NORMAL_REIATSU_GAIN"]
SPAWN_SPEED_RANGES   = CONFIG["SPAWN_SPEED_RANGES"]
DEFAULT_SPAWN_SPEED  = CONFIG["DEFAULT_SPAWN_SPEED"]

DB_PATH = "database/reiatsu.db"


# ────────────────────────────────────────────────────────────────────────────────
# 🛠️ Helper : timestamp UTC actuel (entier)
# ────────────────────────────────────────────────────────────────────────────────
def _now_ts() -> int:
    return int(datetime.now(timezone.utc).timestamp())

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog : ReiatsuSpawner
# ────────────────────────────────────────────────────────────────────────────────
class ReiatsuSpawner(commands.Cog):

    # ──────────────────────────────────────────────────────────────
    def __init__(self, bot: commands.Bot):
        self.bot   = bot
        self.locks: dict[str, asyncio.Lock] = {}
        self.conn  = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()

    async def cog_load(self):
        asyncio.create_task(self._check_on_startup())
        self.spawn_loop.start()

    def cog_unload(self):
        self.spawn_loop.cancel()
        self.conn.close()

    # ──────────────────────────────────────────────────────────────
    # 🔹 Nettoyage au démarrage — supprime les spawns fantômes
    # ──────────────────────────────────────────────────────────────
    async def _check_on_startup(self):
        await self.bot.wait_until_ready()

        self.cursor.execute("SELECT * FROM reiatsu_config")
        configs = self.cursor.fetchall()

        for conf in configs:
            if not conf["is_spawn"] or not conf["message_id"]:
                continue

            guild   = self.bot.get_guild(conf["guild_id"])
            channel = guild.get_channel(conf["channel_id"] or 0) if guild else None
            if not channel:
                continue

            try:
                await channel.fetch_message(conf["message_id"])
            except Exception:
                # Message introuvable → reset propre + nouveau délai immédiat
                self._reset_spawn_config(conf["guild_id"], new_delay=True)
                print(f"[STARTUP] Spawn fantôme nettoyé — guild {conf['guild_id']}")

    # ──────────────────────────────────────────────────────────────
    # 🔹 Boucle principale de spawn
    # ──────────────────────────────────────────────────────────────
    @tasks.loop(seconds=SPAWN_LOOP_INTERVAL)
    async def spawn_loop(self):
        await self.bot.wait_until_ready()
        if not getattr(self.bot, "is_main_instance", True):
            return
        try:
            await self._spawn_tick()
        except Exception as e:
            print(f"[ERREUR spawn_loop] {e}")

    # ──────────────────────────────────────────────────────────────
    async def _spawn_tick(self):
        now = _now_ts()

        self.cursor.execute("SELECT * FROM reiatsu_config")
        configs = self.cursor.fetchall()

        for conf in configs:
            guild_id   = conf["guild_id"]
            channel_id = conf["channel_id"]
            if not channel_id:
                continue

            # ── Calcul du délai attendu ────────────────────────────
            spawn_speed      = conf["spawn_speed"] or DEFAULT_SPAWN_SPEED
            min_d, max_d     = SPAWN_SPEED_RANGES.get(spawn_speed, SPAWN_SPEED_RANGES[DEFAULT_SPAWN_SPEED])
            spawn_delay      = conf["spawn_delay"] or random.randint(min_d, max_d)
            last_spawn_str   = conf["last_spawn_at"]

            if last_spawn_str:
                try:
                    last_ts = int(datetime.fromisoformat(last_spawn_str).timestamp())
                except Exception:
                    last_ts = 0
            else:
                last_ts = 0

            elapsed     = now - last_ts
            should_spawn = (not conf["is_spawn"]) and (elapsed >= spawn_delay)

            if should_spawn:
                channel = self.bot.get_channel(channel_id)
                if channel:
                    await self._spawn_message(channel, guild_id)

            # ── Faux reiatsu Illusionniste ─────────────────────────
            channel = self.bot.get_channel(channel_id)
            if channel:
                # ⚠️ Vérifie qu’aucun faux spawn actif pour ce joueur
                self.cursor.execute("""
                    SELECT user_id FROM reiatsu
                    WHERE classe = 'Illusionniste' AND active_skill = 1 AND fake_spawn_id IS NULL
                """)
                players = self.cursor.fetchall()
                for player in players:
                    # Vérifie qu’il n’y a pas déjà de spawn existant dans le serveur
                    self.cursor.execute("""
                        SELECT 1 FROM reiatsu WHERE fake_spawn_guild_id = ?
                        AND fake_spawn_id IS NOT NULL AND user_id = ?
                    """, (guild_id, player["user_id"]))
                    if self.cursor.fetchone():
                        continue  # un faux spawn existe déjà
                    await self._spawn_message(
                        channel,
                        guild_id=guild_id,
                        is_fake=True,
                        owner_id=player["user_id"]
                    )

    # ──────────────────────────────────────────────────────────────
    # 🔹 Envoi d'un message de spawn (vrai ou faux)
    # ──────────────────────────────────────────────────────────────
    async def _spawn_message(
        self,
        channel: discord.TextChannel,
        guild_id: int,
        is_fake: bool = False,
        owner_id: int | None = None
    ):
        embed = discord.Embed(
            title="💠 Un Reiatsu sauvage apparaît !",
            description="Cliquez sur la réaction 💠 pour l'absorber.",
            color=discord.Color.purple()
        )

        message = await safe_send(channel, embed=embed)
        if not message:
            return

        try:
            await message.add_reaction("💠")
        except discord.HTTPException:
            pass

        if is_fake:
            self.cursor.execute(
                "UPDATE reiatsu SET fake_spawn_id = ?, fake_spawn_guild_id = ? WHERE user_id = ?",
                (message.id, channel.guild.id, owner_id)
            )
        else:
            spawn_speed  = self._get_spawn_speed(guild_id)
            min_d, max_d = SPAWN_SPEED_RANGES.get(spawn_speed, SPAWN_SPEED_RANGES[DEFAULT_SPAWN_SPEED])
            next_delay   = random.randint(min_d, max_d)

            self.cursor.execute("""
                UPDATE reiatsu_config
                SET is_spawn = 1,
                    last_spawn_at = ?,
                    message_id = ?,
                    spawn_delay = ?
                WHERE guild_id = ?
            """, (_now_iso(), message.id, next_delay, guild_id))

        self.conn.commit()

        if is_fake:
            asyncio.create_task(
                self._delete_fake_after_delay(channel, message.id, owner_id)
            )
        else:
            spawn_speed  = self._get_spawn_speed(guild_id)
            min_d, max_d = SPAWN_SPEED_RANGES.get(spawn_speed, SPAWN_SPEED_RANGES[DEFAULT_SPAWN_SPEED])
            next_delay   = random.randint(min_d, max_d)

            self.cursor.execute("""
                UPDATE reiatsu_config
                SET is_spawn = 1,
                    last_spawn_at = ?,
                    message_id = ?,
                    spawn_delay = ?
                WHERE guild_id = ?
            """, (_now_iso(), message.id, next_delay, guild_id))

        self.conn.commit()

        if is_fake:
            asyncio.create_task(
                self._delete_fake_after_delay(channel, message.id, owner_id)
            )

    # ──────────────────────────────────────────────────────────────
    def _get_spawn_speed(self, guild_id: int) -> str:
        self.cursor.execute(
            "SELECT spawn_speed FROM reiatsu_config WHERE guild_id = ?", (guild_id,)
        )
        row = self.cursor.fetchone()
        return (row["spawn_speed"] if row and row["spawn_speed"] else DEFAULT_SPAWN_SPEED)

    # ──────────────────────────────────────────────────────────────
    # 🔹 Suppression automatique d'un faux reiatsu après 3 minutes
    # ──────────────────────────────────────────────────────────────
    async def _delete_fake_after_delay(
        self,
        channel: discord.TextChannel,
        message_id: int,
        owner_id: int
    ):
        await asyncio.sleep(180)

        self.cursor.execute(
            "SELECT fake_spawn_id FROM reiatsu WHERE user_id = ?", (owner_id,)
        )
        row = self.cursor.fetchone()
        if not row or not row["fake_spawn_id"]:
            return

        try:
            msg = await channel.fetch_message(message_id)
            await safe_delete(msg)
        except Exception:
            pass

        self.cursor.execute(
            "UPDATE reiatsu SET fake_spawn_id = NULL, fake_spawn_guild_id = NULL, active_skill = 0 WHERE user_id = ?",
            (owner_id,)
        )
        self.conn.commit()

    # ──────────────────────────────────────────────────────────────
    # 🔹 Spawn faux reiatsu pour les Illusionnistes actifs
    # ──────────────────────────────────────────────────────────────
    async def _spawn_faux_reiatsu(self, channel: discord.TextChannel, guild_id: int):
        self.cursor.execute("""
            SELECT user_id FROM reiatsu
            WHERE classe = 'Illusionniste'
            AND active_skill = 1
            AND fake_spawn_id IS NULL
        """)
        players = self.cursor.fetchall()

        for player in players:
            await self._spawn_message(
                channel,
                guild_id=guild_id,
                is_fake=True,
                owner_id=player["user_id"]
            )

    # ──────────────────────────────────────────────────────────────
    # 🔹 Calcul du gain lors d'une absorption
    # ──────────────────────────────────────────────────────────────
    def _calculate_gain(self, user_id: int) -> tuple[int, bool, str | None]:
        self.cursor.execute(
            "SELECT classe, points, bonus5, active_skill FROM reiatsu WHERE user_id = ?",
            (user_id,)
        )
        row = self.cursor.fetchone()

        if row:
            classe         = row["classe"] or None
            current_points = row["points"] or 0
            bonus5         = row["bonus5"] or 0
            active_skill   = row["active_skill"]
        else:
            classe, current_points, bonus5, active_skill = None, 0, 0, 0

        # ── Détermination du type de reiatsu ──────────────────────
        if classe == "Absorbeur" and active_skill:
            is_super = True
            self.cursor.execute(
                "UPDATE reiatsu SET active_skill = 0 WHERE user_id = ?", (user_id,)
            )
        else:
            is_super = random.randint(1, 100) <= SUPER_REIATSU_CHANCE

        gain = SUPER_REIATSU_GAIN if is_super else NORMAL_REIATSU_GAIN

        # ── Modificateurs de classe ────────────────────────────────
        if not is_super:
            if classe == "Absorbeur":
                gain += 4
            elif classe == "Parieur":
                gain = 0 if random.random() < 0.5 else random.randint(5, 12)
            else:
                # Bonus5 : tous les 5 reiatsu normaux → +6 au 5ème
                bonus5 += 1
                if bonus5 >= 5:
                    gain   = 6
                    bonus5 = 0
        else:
            bonus5 = 0

        new_total = current_points + gain

        # ── BUG CORRIGÉ : on ne réécrit pas username (évite d'écraser avec "")
        self.cursor.execute("""
            INSERT INTO reiatsu (user_id, username, points, classe, bonus5)
            VALUES (?, '', ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                points = excluded.points,
                bonus5 = excluded.bonus5
        """, (user_id, new_total, classe or "", bonus5))

        self.conn.commit()

        return gain, is_super, classe

    # ──────────────────────────────────────────────────────────────
    # 🔹 Feedback visuel après absorption
    # ──────────────────────────────────────────────────────────────
    async def _send_feedback(
        self,
        channel: discord.TextChannel,
        user: discord.Member,
        gain: int,
        is_super: bool,
        classe: str | None
    ):
        if is_super:
            await safe_send(channel, f"🌟 {user.mention} a absorbé un **Super Reiatsu** et gagné **+{gain}** reiatsu !")
        elif classe == "Parieur" and gain == 0:
            await safe_send(channel, f"🎲 {user.mention} a tenté d'absorber un reiatsu mais a raté (passif Parieur) !")
        else:
            await safe_send(channel, f"💠 {user.mention} a absorbé le Reiatsu et gagné **+{gain}** reiatsu !")

    # ──────────────────────────────────────────────────────────────
    # 🔹 Helper : reset config spawn après capture
    # ──────────────────────────────────────────────────────────────
    def _reset_spawn_config(self, guild_id: int, new_delay: bool = True):
        """Remet is_spawn à 0 et génère un nouveau délai aléatoire."""
        next_delay = None
        if new_delay:
            spawn_speed  = self._get_spawn_speed(guild_id)
            min_d, max_d = SPAWN_SPEED_RANGES.get(spawn_speed, SPAWN_SPEED_RANGES[DEFAULT_SPAWN_SPEED])
            next_delay   = random.randint(min_d, max_d)

        self.cursor.execute("""
            UPDATE reiatsu_config
            SET is_spawn = 0,
                message_id = NULL,
                last_spawn_at = ?,
                spawn_delay = ?
            WHERE guild_id = ?
        """, (_now_iso(), next_delay, guild_id))
        self.conn.commit()

    # ──────────────────────────────────────────────────────────────
    # 🔹 Listener réaction — capture du Reiatsu
    # ──────────────────────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id:
            return
        if str(payload.emoji) != "💠":
            return

        guild_id   = payload.guild_id
        message_id = payload.message_id
        user_id    = payload.user_id

        # ── Identifie si vrai ou faux reiatsu ─────────────────────
        self.cursor.execute("""
            SELECT * FROM reiatsu_config
            WHERE guild_id = ? AND message_id = ? AND is_spawn = 1
        """, (guild_id, message_id))
        conf = self.cursor.fetchone()

        self.cursor.execute(
            "SELECT user_id FROM reiatsu WHERE fake_spawn_id = ?", (message_id,)
        )
        fake_row = self.cursor.fetchone()

        if not conf and not fake_row:
            return

        # ── Verrou anti-double capture ─────────────────────────────
        lock_key = f"{guild_id}-{message_id}"
        if lock_key not in self.locks:
            self.locks[lock_key] = asyncio.Lock()

        async with self.locks[lock_key]:

            # Re-vérifie que le reiatsu est toujours disponible
            if conf:
                self.cursor.execute("""
                    SELECT is_spawn FROM reiatsu_config
                    WHERE guild_id = ? AND message_id = ?
                """, (guild_id, message_id))
                current = self.cursor.fetchone()
                if not current or not current["is_spawn"]:
                    return
            else:
                self.cursor.execute(
                    "SELECT fake_spawn_id FROM reiatsu WHERE fake_spawn_id = ?", (message_id,)
                )
                if not self.cursor.fetchone():
                    return

            # ── Récupère channel et membre ────────────────────────
            channel = self.bot.get_channel(payload.channel_id)
            if not channel:
                return

            guild = self.bot.get_guild(guild_id)
            if not guild:
                return

            user = guild.get_member(user_id) or await guild.fetch_member(user_id)
            if not user:
                return

            # ── Calcul du gain ────────────────────────────────────
            gain, is_super, classe = self._calculate_gain(user_id)

            # ── Supprime le message de spawn ──────────────────────
            try:
                msg = await channel.fetch_message(message_id)
                await safe_delete(msg)
            except Exception:
                pass

            # ── Reset DB ──────────────────────────────────────────
            if conf:
                # BUG CORRIGÉ : génère immédiatement le prochain délai
                # pour éviter un respawn quasi-instantané au prochain tick
                self._reset_spawn_config(guild_id, new_delay=True)
            else:
                self.cursor.execute("""
                    UPDATE reiatsu
                    SET fake_spawn_id = NULL, fake_spawn_guild_id = NULL, active_skill = 0
                    WHERE fake_spawn_id = ?
                """, (message_id,))
                self.conn.commit()

            # ── Libère le verrou ──────────────────────────────────
            del self.locks[lock_key]

            # ── Feedback ─────────────────────────────────────────
            await self._send_feedback(channel, user, gain, is_super, classe)

            print(f"[SPAWN] {user} a capturé un reiatsu (+{gain}) — guild {guild_id}")


# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    await bot.add_cog(ReiatsuSpawner(bot))
