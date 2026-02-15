# ────────────────────────────────────────────────────────────────────────────────
# 📌 reiatsu_spawner.py — Gestion du spawn des Reiatsu
# Objectif : Gérer l’apparition et la capture des Reiatsu sur les serveurs
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
from datetime import datetime
from dateutil import parser
from pathlib import Path
from discord.ext import commands, tasks
from utils.discord_utils import safe_send, safe_delete

# ────────────────────────────────────────────────────────────────────────────────
# ⚙️ Paramètres globaux
# ────────────────────────────────────────────────────────────────────────────────
CONFIG_PATH = Path("data/reiatsu_config.json")
with CONFIG_PATH.open("r", encoding="utf-8") as f:
    CONFIG = json.load(f)

SPAWN_LOOP_INTERVAL = CONFIG["SPAWN_LOOP_INTERVAL"]
SUPER_REIATSU_CHANCE = CONFIG["SUPER_REIATSU_CHANCE"]
SUPER_REIATSU_GAIN = CONFIG["SUPER_REIATSU_GAIN"]
NORMAL_REIATSU_GAIN = CONFIG["NORMAL_REIATSU_GAIN"]
SPAWN_SPEED_RANGES = CONFIG["SPAWN_SPEED_RANGES"]
DEFAULT_SPAWN_SPEED = CONFIG["DEFAULT_SPAWN_SPEED"]

DB_PATH = "database/reiatsu.db"

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog : ReiatsuSpawner
# ────────────────────────────────────────────────────────────────────────────────
class ReiatsuSpawner(commands.Cog):

    # ──────────────────────────────────────────────────────────────
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.locks = {}
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()

    async def cog_load(self):
        asyncio.create_task(self._check_on_startup())
        self.spawn_loop.start()

    def cog_unload(self):
        self.spawn_loop.cancel()
        self.conn.close()

    # ──────────────────────────────────────────────────────────────
    async def _check_on_startup(self):
        await self.bot.wait_until_ready()

        self.cursor.execute("SELECT * FROM reiatsu_config")
        configs = self.cursor.fetchall()

        for conf in configs:
            if not conf["is_spawn"] or not conf["message_id"]:
                continue

            guild = self.bot.get_guild(conf["guild_id"])
            if not guild:
                continue

            channel = guild.get_channel(conf["channel_id"] or 0)
            if not channel:
                continue

            try:
                await channel.fetch_message(conf["message_id"])
            except Exception:
                self.cursor.execute("""
                    UPDATE reiatsu_config
                    SET is_spawn = 0, message_id = NULL
                    WHERE guild_id = ?
                """, (conf["guild_id"],))
                self.conn.commit()
                print(f"[RESET] Reiatsu fantôme nettoyé pour guild {conf['guild_id']}")

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
        now = int(time.time())

        self.cursor.execute("SELECT * FROM reiatsu_config")
        configs = self.cursor.fetchall()

        for conf in configs:
            guild_id = conf["guild_id"]
            channel_id = conf["channel_id"]
            if not channel_id:
                continue

            last_spawn_str = conf["last_spawn_at"]
            spawn_speed = conf["spawn_speed"] or DEFAULT_SPAWN_SPEED
            min_delay, max_delay = SPAWN_SPEED_RANGES.get(
                spawn_speed,
                SPAWN_SPEED_RANGES[DEFAULT_SPAWN_SPEED]
            )

            delay = conf["spawn_delay"] or random.randint(min_delay, max_delay)

            should_spawn = (
                not last_spawn_str or
                (now - int(parser.parse(last_spawn_str).timestamp()) >= delay)
            )

            if should_spawn and not conf["is_spawn"]:
                channel = self.bot.get_channel(channel_id)
                if channel:
                    await self._spawn_message(channel, guild_id)

            channel = self.bot.get_channel(channel_id)
            if channel:
                await self._spawn_faux_reiatsu(channel)

    # ──────────────────────────────────────────────────────────────
    async def _spawn_message(self, channel, guild_id: int, is_fake=False, owner_id=None):

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
            self.cursor.execute("""
                UPDATE reiatsu
                SET fake_spawn_id = ?
                WHERE user_id = ?
            """, (message.id, owner_id))
        else:
            self.cursor.execute("""
                UPDATE reiatsu_config
                SET is_spawn = 1,
                    last_spawn_at = ?,
                    message_id = ?
                WHERE guild_id = ?
            """, (
                datetime.utcnow().isoformat(timespec="seconds"),
                message.id,
                guild_id
            ))

        self.conn.commit()

        if is_fake:
            asyncio.create_task(
                self._delete_fake_after_delay(channel, message.id, owner_id)
            )

    # ──────────────────────────────────────────────────────────────
    async def _delete_fake_after_delay(self, channel, message_id, owner_id):
        await asyncio.sleep(180)

        self.cursor.execute("""
            SELECT fake_spawn_id FROM reiatsu WHERE user_id = ?
        """, (owner_id,))
        row = self.cursor.fetchone()

        if not row or not row["fake_spawn_id"]:
            return

        try:
            msg = await channel.fetch_message(message_id)
            await safe_delete(msg)
        except Exception:
            pass

        self.cursor.execute("""
            UPDATE reiatsu
            SET fake_spawn_id = NULL,
                active_skill = 0
            WHERE user_id = ?
        """, (owner_id,))
        self.conn.commit()

    # ──────────────────────────────────────────────────────────────
    async def _spawn_faux_reiatsu(self, channel: discord.TextChannel):
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
                guild_id=None,
                is_fake=True,
                owner_id=player["user_id"]
            )

    # ──────────────────────────────────────────────────────────────
    def _calculate_gain(self, user_id: int):

        self.cursor.execute("""
            SELECT classe, points, bonus5, active_skill
            FROM reiatsu
            WHERE user_id = ?
        """, (user_id,))
        row = self.cursor.fetchone()

        if row:
            classe = row["classe"]
            current_points = row["points"] or 0
            bonus5 = row["bonus5"] or 0
            active_skill = row["active_skill"]
        else:
            classe = None
            current_points = 0
            bonus5 = 0
            active_skill = 0

        if classe == "Absorbeur" and active_skill:
            is_super = True
            self.cursor.execute("""
                UPDATE reiatsu
                SET active_skill = 0
                WHERE user_id = ?
            """, (user_id,))
        else:
            is_super = random.randint(1, 100) <= SUPER_REIATSU_CHANCE

        gain = SUPER_REIATSU_GAIN if is_super else NORMAL_REIATSU_GAIN

        if not is_super:
            if classe == "Absorbeur":
                gain += 4
            elif classe == "Parieur":
                gain = 0 if random.random() < 0.5 else random.randint(5, 12)
            else:
                bonus5 += 1
                if bonus5 >= 5:
                    gain = 6
                    bonus5 = 0
        else:
            bonus5 = 0

        new_total = current_points + gain

        self.cursor.execute("""
            INSERT INTO reiatsu (user_id, username, points, classe, bonus5)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                points = ?,
                bonus5 = ?
        """, (
            user_id,
            "",
            new_total,
            classe,
            bonus5,
            new_total,
            bonus5
        ))

        self.conn.commit()

        return gain, is_super, classe

    # ──────────────────────────────────────────────────────────────
    async def _send_feedback(self, channel, user, gain, is_super, classe):
        if is_super:
            await safe_send(channel, f"🌟 {user.mention} a absorbé un **Super Reiatsu** et gagné **+{gain}** reiatsu !")
        else:
            if classe == "Parieur" and gain == 0:
                await safe_send(channel, f"🎲 {user.mention} a tenté d’absorber un reiatsu mais a raté (passif Parieur) !")
            else:
                await safe_send(channel, f"💠 {user.mention} a absorbé le Reiatsu et gagné **+{gain}** reiatsu !")

# ───────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ───────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    await bot.add_cog(ReiatsuSpawner(bot))
