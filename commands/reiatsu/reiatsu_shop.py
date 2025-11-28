# ────────────────────────────────────────────────────────────────────────────────
# 📌 reiatsushop.py — Commande /reiatsushop et !reiatsushop
# Objectif : Acheter des effets du ReiatsuShop et les activer immédiatement sur un membre
# Catégorie : Reiatsu
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import asyncio
import discord
from discord import app_commands
from discord.ext import commands, tasks
from utils.discord_utils import safe_send, safe_respond
from utils.supabase_client import supabase
from utils.reiatsu_utils import ensure_profile
import datetime
import random

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class ReiatsuShop(commands.Cog):
    """Commande /reiatsushop et !reiatsushop — Affiche le shop et applique les effets"""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        # Effets actifs en mémoire
        self.active_zombie = {}  # {user_id: guild_id}
        self.active_rename = {}  # {user_id: {"guild_id": int, "nick": str, "use_webhook": bool}}

        # Shop items
        self.shop_items = {
            "zombification": {"emoji": "🧟‍♂️", "name": "Zombification", "price": 750, "duration": 86400,
                              "description": "Ajoute 'arrrg cerveau...' à tes messages."},
            "mute_temp": {"emoji": "🔇", "name": "Mute Temporaire", "price": 1000, "duration": 3600,
                          "description": "Timeout le joueur pendant X temps."},
            "rename_2j": {"emoji": "🪞", "name": "Rename 2J", "price": 800, "duration": 172800,
                          "description": "Force le pseudo et empêche de le changer pendant 2 jours."}
        }

        self.clean_expired_effects.start()
        self.load_effects_from_db()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Charger les effets actifs depuis la DB
    # ────────────────────────────────────────────────────────────────────────────
    def load_effects_from_db(self):
        res = supabase.table("reiatsu").select("user_id, shop_effets").execute()
        now = datetime.datetime.utcnow()
        for profile in res.data:
            user_id = int(profile["user_id"])
            for eff in profile.get("shop_effets") or []:
                end_time = datetime.datetime.fromisoformat(eff["end_time"])
                guild_id = eff.get("guild_id")
                if end_time > now and guild_id:
                    if eff["effect_key"] == "zomb":
                        self.active_zombie[user_id] = guild_id
                    elif eff["effect_key"] == "rename":
                        self.active_rename[user_id] = {"guild_id": guild_id, "nick": eff.get("forced_nick"), "use_webhook": False}

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(name="reiatsushop", description="Affiche le shop et achète des effets")
    async def slash_reiatsushop(self, interaction: discord.Interaction, effect: str = None,
                                 member: discord.Member = None, new_nick: str = None):
        await self.handle_shop(interaction, effect, member, new_nick, is_slash=True)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="reiatsushop", aliases=["rtsshop"])
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_reiatsushop(self, ctx: commands.Context, effect: str = None,
                                  member: discord.Member = None, *, new_nick: str = None):
        await self.handle_shop(ctx, effect, member, new_nick, is_slash=False)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Handler commun pour slash et prefix
    # ────────────────────────────────────────────────────────────────────────────
    async def handle_shop(self, ctx_or_inter, effect, member, new_nick, is_slash: bool):
        send_func = safe_respond if is_slash else safe_send
        user = ctx_or_inter.user if is_slash else ctx_or_inter.author

        if not effect or not member:
            embed = discord.Embed(title="💸 ReiatsuShop",
                                  description="Voici les objets disponibles :" if is_slash else
                                  "Voici les objets disponibles :\n💡 Pour acheter : `!!reiatsushop <zomb|mute|rename> @membre [nouveau pseudo]`",
                                  color=discord.Color.gold())
            for item in self.shop_items.values():
                embed.add_field(name=f"{item['emoji']} **{item['name']}** — `{item['price']} reiatsu`",
                                value=f"🕒 Durée : `{self.format_duration(item['duration'])}`\n💬 {item['description']}",
                                inline=False)
            await send_func(ctx_or_inter, embed=embed)
            return

        effect = effect.lower()
        if effect not in ["zomb", "mute", "rename"]:
            await send_func(ctx_or_inter, "❌ Effet invalide. Choisis `zomb`, `mute` ou `rename`.",
                            ephemeral=is_slash if is_slash else False)
            return

        if effect == "rename" and not new_nick:
            await send_func(ctx_or_inter, "❌ Pour rename, indique le nouveau pseudo.",
                            ephemeral=is_slash if is_slash else False)
            return

        profile = ensure_profile(user.id, user.display_name)
        item_key = {"zomb": "zombification", "mute": "mute_temp", "rename": "rename_2j"}[effect]
        item = self.shop_items[item_key]

        if profile.get("points", 0) < item["price"]:
            await send_func(ctx_or_inter, f"❌ Pas assez de reiatsu pour **{item['name']}** !",
                            ephemeral=is_slash if is_slash else False)
            return

        # Débit des points
        profile["points"] -= item["price"]
        supabase.table("reiatsu").update({"points": profile["points"]}).eq("user_id", user.id).execute()

        # Application de l'effet
        await self.apply_effect(member, effect, ctx_or_inter.guild.id, new_nick=new_nick)

        embed = discord.Embed(
            description=f"✅ **{member.display_name}** affecté par **{item['name']}** !\n💰 Points restants : `{profile['points']}`",
            color=discord.Color.green()
        )
        await send_func(ctx_or_inter, embed=embed)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Appliquer un effet et stocker en DB
    # ────────────────────────────────────────────────────────────────────────────
    async def apply_effect(self, member: discord.Member, effect: str, guild_id: int, new_nick: str = None):
        item = self.shop_items[{"zomb": "zombification", "mute": "mute_temp", "rename": "rename_2j"}[effect]]
        start_time = datetime.datetime.utcnow()
        end_time = start_time + datetime.timedelta(seconds=item["duration"])

        profile = ensure_profile(member.id, member.display_name)
        effects = profile.get("shop_effets") or []

        effect_data = {"effect_key": effect, "start_time": start_time.isoformat(),
                       "end_time": end_time.isoformat(), "guild_id": guild_id}
        if effect == "rename":
            effect_data["forced_nick"] = new_nick

        effects.append(effect_data)
        supabase.table("reiatsu").update({"shop_effets": effects}).eq("user_id", member.id).execute()

        # Mise à jour mémoire
        if effect == "zomb":
            self.active_zombie[member.id] = guild_id
        elif effect == "rename" and new_nick:
            self.active_rename[member.id] = {"guild_id": guild_id, "nick": new_nick, "use_webhook": False}
            try:
                await member.edit(nick=new_nick)
            except:
                self.active_rename[member.id]["use_webhook"] = True
        elif effect == "mute":
            if member.guild.me.guild_permissions.moderate_members:
                await member.timeout(item["duration"])

        async def remove_effect():
            await asyncio.sleep(item["duration"])
            self.active_zombie.pop(member.id, None)
            self.active_rename.pop(member.id, None)

            profile = ensure_profile(member.id, member.display_name)
            effects = profile.get("shop_effets") or []
            effects = [e for e in effects if e["effect_key"] != effect or datetime.datetime.fromisoformat(e["end_time"]) > datetime.datetime.utcnow()]
            supabase.table("reiatsu").update({"shop_effets": effects}).eq("user_id", member.id).execute()

        asyncio.create_task(remove_effect())

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Listener unique pour messages et rename fallback
    # ────────────────────────────────────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        # Zomb effect
        if self.active_zombie.get(message.author.id) == message.guild.id:
            if not message.content.startswith(("!!", "$", "dun", "Dun")) and random.randint(1, 3) == 1:
                webhook = await message.channel.create_webhook(name=f"tmp-{message.author.name}")
                try:
                    await webhook.send(username=message.author.display_name,
                                       avatar_url=message.author.display_avatar.url,
                                       content=message.content + " arrrg cerveau...")
                finally:
                    await webhook.delete()
                await message.delete()
                return

        # Rename fallback via webhook
        data = self.active_rename.get(message.author.id)
        if data and data["guild_id"] == message.guild.id and data.get("use_webhook"):
            webhook = await message.channel.create_webhook(name=data["nick"])
            try:
                await webhook.send(username=data["nick"],
                                   avatar_url=message.author.display_avatar.url,
                                   content=message.content)
            finally:
                await webhook.delete()
            await message.delete()

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        data = self.active_rename.get(after.id)
        if data and data["guild_id"] == after.guild.id and after.display_name != data["nick"]:
            if not data.get("use_webhook"):
                try:
                    await after.edit(nick=data["nick"])
                except:
                    self.active_rename[after.id]["use_webhook"] = True

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Nettoyer les effets expirés périodiquement
    # ────────────────────────────────────────────────────────────────────────────
    @tasks.loop(minutes=5)
    async def clean_expired_effects(self):
        now = datetime.datetime.utcnow()
        res = supabase.table("reiatsu").select("user_id, shop_effets").execute()
        for profile in res.data:
            user_id = int(profile["user_id"])
            effects = profile.get("shop_effets") or []
            new_effects = []
            for e in effects:
                end_time = datetime.datetime.fromisoformat(e["end_time"])
                if end_time > now:
                    new_effects.append(e)
                else:
                    if e["effect_key"] == "zomb":
                        self.active_zombie.pop(user_id, None)
                    elif e["effect_key"] == "rename":
                        self.active_rename.pop(user_id, None)
            if len(new_effects) != len(effects):
                supabase.table("reiatsu").update({"shop_effets": new_effects}).eq("user_id", user_id).execute()

    @clean_expired_effects.before_loop
    async def before_clean_expired_effects(self):
        await self.bot.wait_until_ready()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Helper pour formater la durée
    # ────────────────────────────────────────────────────────────────────────────
    def format_duration(self, seconds):
        days, remainder = divmod(seconds, 86400)
        hours, _ = divmod(remainder, 3600)
        parts = [f"{days}j" if days else "", f"{hours}h" if hours else ""]
        return " ".join(filter(None, parts)) or "0h"

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = ReiatsuShop(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Reiatsu"
    await bot.add_cog(cog)
