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
from datetime import datetime
from dateutil import parser
from pathlib import Path
from discord.ext import commands, tasks
from utils.supabase_client import supabase
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
CLASSES = CONFIG["CLASSES"]

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog : ReiatsuSpawner
# ────────────────────────────────────────────────────────────────────────────────
class ReiatsuSpawner(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.locks = {}

    async def cog_load(self):
        asyncio.create_task(self._check_on_startup())
        self.spawn_loop.start()

    def cog_unload(self):
        self.spawn_loop.cancel()

    # ──────────────────────────────────────────────────────────────
    async def _check_on_startup(self):
        await self.bot.wait_until_ready()
        configs = supabase.table("reiatsu_config").select("*").execute()
        for conf in configs.data:
            if not conf.get("is_spawn") or not conf.get("message_id"):
                continue
            guild = self.bot.get_guild(int(conf["guild_id"]))
            if not guild:
                continue
            channel = guild.get_channel(int(conf.get("channel_id") or 0))
            if not channel:
                continue
            try:
                await channel.fetch_message(int(conf["message_id"]))
            except Exception:
                supabase.table("reiatsu_config").update({
                    "is_spawn": False,
                    "message_id": None
                }).eq("guild_id", int(conf["guild_id"])).execute()
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

    async def _spawn_tick(self):
        now = int(time.time())
        configs = supabase.table("reiatsu_config").select("*").execute()
        for conf in configs.data:
            guild_id = int(conf["guild_id"])
            channel_id = conf.get("channel_id")
            if not channel_id:
                continue

            last_spawn_str = conf.get("last_spawn_at")
            spawn_speed = conf.get("spawn_speed") or DEFAULT_SPAWN_SPEED
            min_delay, max_delay = SPAWN_SPEED_RANGES.get(spawn_speed, SPAWN_SPEED_RANGES[DEFAULT_SPAWN_SPEED])
            delay = conf.get("spawn_delay") or random.randint(min_delay, max_delay)
            should_spawn = not last_spawn_str or (now - int(parser.parse(last_spawn_str).timestamp()) >= delay)

            if should_spawn and not conf.get("is_spawn", False):
                channel = self.bot.get_channel(int(channel_id))
                if channel:
                    await self._spawn_message(channel, guild_id)

            channel = self.bot.get_channel(int(channel_id))
            if channel:
                await self._spawn_faux_reiatsu(channel)

    # ──────────────────────────────────────────────────────────────
    async def _spawn_message(self, channel, guild_id: int, is_fake=False, owner_id=None):
        # Message identique pour vrai et faux Reiatsu
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
            supabase.table("reiatsu").update({"fake_spawn_id": str(message.id)}).eq("user_id", owner_id).execute()
            asyncio.create_task(self._delete_fake_after_delay(channel, message, owner_id))
        else:
            supabase.table("reiatsu_config").update({
                "is_spawn": True,
                "last_spawn_at": datetime.utcnow().isoformat(timespec="seconds"),
                "message_id": str(message.id)
            }).eq("guild_id", guild_id).execute()

    # ──────────────────────────────────────────────────────────────
    async def _delete_fake_after_delay(self, channel, message, owner_id):
        await asyncio.sleep(180)  # 3 minutes
        
        # Vérifie toujours que le fake existe encore
        data = supabase.table("reiatsu").select("fake_spawn_id").eq("user_id", owner_id).execute()
        if not data.data:
            print(f"[FAKE] Aucun fake trouvé pour user {owner_id}")
            return
        
        fake_id = data.data[0].get("fake_spawn_id")
        if not fake_id:
            print(f"[FAKE] Pas de fake_spawn_id enregistré pour user {owner_id}")
            return

        try:
            # Refetch le message depuis Discord (objet original peut être expiré)
            msg = await channel.fetch_message(int(fake_id))
            await safe_delete(msg)
            print(f"[FAKE DELETE] Suppression réussie du faux reiatsu {fake_id}")
        except Exception as e:
            print(f"[FAKE DELETE] Échec suppression message {fake_id} → {e}")

        # Nettoie la DB, même si le message n'existe plus
        supabase.table("reiatsu").update({
            "fake_spawn_id": None,
            "active_skill": False
        }).eq("user_id", owner_id).execute()


    # ──────────────────────────────────────────────────────────────
    async def _spawn_faux_reiatsu(self, channel: discord.TextChannel):
        players = supabase.table("reiatsu").select("*").eq("classe", "Illusionniste").execute()
        for player in players.data:
            if player.get("active_skill") and not player.get("fake_spawn_id"):
                await self._spawn_message(channel, guild_id=None, is_fake=True, owner_id=int(player["user_id"]))

    # ──────────────────────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if str(payload.emoji) != "💠" or payload.user_id == self.bot.user.id:
            return

        guild_id = int(payload.guild_id)
        if guild_id not in self.locks:
            self.locks[guild_id] = asyncio.Lock()

        async with self.locks[guild_id]:
            conf_data = supabase.table("reiatsu_config").select("*").eq("guild_id", guild_id).execute()
            if not conf_data.data:
                return
            conf = conf_data.data[0]

            guild = self.bot.get_guild(payload.guild_id)
            channel = guild.get_channel(payload.channel_id)
            user = guild.get_member(payload.user_id)
            if not channel or not user:
                return

            # ── Vérification faux Reiatsu
            player_list = supabase.table("reiatsu").select("*").eq("classe", "Illusionniste").execute()
            for p in player_list.data:
                fake_id = p.get("fake_spawn_id")
                if fake_id and payload.message_id == int(fake_id):
                    owner_id = int(p["user_id"])
                    if payload.user_id == owner_id:
                        return  # L’illusionniste ne peut pas absorber son propre faux Reiatsu
                    owner = guild.get_member(owner_id)
                    if owner:
                        gain = 50
                        user_data = supabase.table("reiatsu").select("points").eq("user_id", owner_id).execute()
                        current_points = user_data.data[0]["points"] if user_data.data else 0
                        supabase.table("reiatsu").update({
                            "points": current_points + gain,
                            "fake_spawn_id": None,
                            "active_skill": False
                        }).eq("user_id", owner_id).execute()
                        await safe_send(channel, f"🎭 {user.mention} a absorbé un **faux Reiatsu** ! {owner.mention} gagne **+{gain}** reiatsu !")
                    try:
                        msg = await channel.fetch_message(payload.message_id)
                        await safe_delete(msg)
                    except Exception:
                        pass
                    return

            # ── Reiatsu normal
            if not conf.get("is_spawn") or payload.message_id != int(conf.get("message_id")):
                return

            gain, is_super, bonus5, classe, new_total = self._calculate_gain(user.id)
            self._update_player(user, gain, bonus5, new_total, classe)
            await self._send_feedback(channel, user, gain, is_super, classe)

            # Recalcule du delay
            spawn_speed = conf.get("spawn_speed") or DEFAULT_SPAWN_SPEED
            min_delay, max_delay = SPAWN_SPEED_RANGES.get(spawn_speed, SPAWN_SPEED_RANGES[DEFAULT_SPAWN_SPEED])
            new_delay = random.randint(min_delay, max_delay)
            msg_id = conf.get("message_id")

            supabase.table("reiatsu_config").update({
                "is_spawn": False,
                "message_id": None,
                "spawn_delay": new_delay,
                # 🔥 Ajoute cette ligne :
                "last_spawn_at": datetime.utcnow().isoformat(timespec="seconds")
            }).eq("guild_id", guild_id).execute()


            try:
                if msg_id:
                    message = await channel.fetch_message(int(msg_id))
                    await safe_delete(message)
            except Exception as e:
                print(f"[WARN] Impossible de delete message spawn {msg_id}: {e}")

    # ───────────────────────────────────────────────────────────────
    def _calculate_gain(self, user_id: int, is_fake=False):
        user_data = supabase.table("reiatsu").select("classe", "points", "bonus5", "active_skill").eq("user_id", user_id).execute()
        if user_data.data:
            classe = user_data.data[0].get("classe")
            current_points = user_data.data[0].get("points", 0)
            bonus5 = user_data.data[0].get("bonus5", 0) or 0
            active_skill = user_data.data[0].get("active_skill", False)
        else:
            classe = None
            current_points = 0
            bonus5 = 0
            active_skill = False

        if classe == "Absorbeur" and active_skill and not is_fake:
            is_super = True
            supabase.table("reiatsu").update({"active_skill": False}).eq("user_id", user_id).execute()
        else:
            is_super = random.randint(1, 100) <= SUPER_REIATSU_CHANCE

        gain = SUPER_REIATSU_GAIN if is_super else NORMAL_REIATSU_GAIN

        if not is_super:
            if classe == "Absorbeur":
                gain += 4
            elif classe == "Parieur":
                gain = 0 if random.random() < 0.5 else random.randint(5, 12)
            elif classe == "Illusionniste":
                pass
            else:
                bonus5 += 1
                if bonus5 >= 5:
                    gain = 6
                    bonus5 = 0
        else:
            bonus5 = 0

        return gain, is_super, bonus5, classe, current_points + gain

    def _update_player(self, user, gain, bonus5, new_total, classe):
        user_id = int(user.id)
        user_data = supabase.table("reiatsu").select("user_id").eq("user_id", user_id).execute()
        if user_data.data:
            supabase.table("reiatsu").update({"points": new_total, "bonus5": bonus5}).eq("user_id", user_id).execute()
        else:
            supabase.table("reiatsu").insert({
                "user_id": user_id,
                "username": user.name,
                "points": gain,
                "classe": classe,
                "bonus5": 1
            }).execute()

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
