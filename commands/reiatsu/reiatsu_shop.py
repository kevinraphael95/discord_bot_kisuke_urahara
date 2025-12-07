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
        self.active_effects = {
            "zomb": {},   # {user_id: guild_id}
            "rename": {}, # {user_id: {"guild_id": int, "nick": str, "use_webhook": bool}}
            "mute": {}    # {user_id: {"guild_id": int, "end_time": datetime}}
        }

        # Shop items
        self.shop_items = {
            "zombification": {"emoji": "🧟‍♂️", "name": "Zombification", "price": 750, "duration": 86400,
                              "description": "Ajoute 'arrrg cerveau...' à tes messages."},
            "mute_temp": {"emoji": "🔇", "name": "Mute Temporaire", "price": 1000, "duration": 3600,
                          "description": "Timeout le joueur pendant X temps."},
            "rename_2j": {"emoji": "🪞", "name": "Rename 2J", "price": 800, "duration": 172800,
                          "description": "Force le pseudo et empêche de le changer pendant 2 jours."}
        }

        self.load_effects_from_db()
        self.clean_expired_effects.start()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Chargement des effets depuis la DB
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
                    key = eff["effect_key"]
                    if key == "zomb":
                        self.active_effects["zomb"][user_id] = guild_id
                    elif key == "rename":
                        self.active_effects["rename"][user_id] = {"guild_id": guild_id,
                                                                  "nick": eff.get("forced_nick"),
                                                                  "use_webhook": False}
                    elif key == "mute":
                        self.active_effects["mute"][user_id] = {"guild_id": guild_id, "end_time": end_time}

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commandes
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(name="reiatsushop", description="Affiche le shop et achète des effets")
    async def slash_reiatsushop(self, interaction: discord.Interaction, effect: str = None,
                                 member: discord.Member = None, new_nick: str = None):
        await self.handle_shop(interaction, effect, member, new_nick, is_slash=True)

    @commands.command(name="reiatsushop", aliases=["rtsshop"])
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_reiatsushop(self, ctx: commands.Context, effect: str = None,
                                  member: discord.Member = None, *, new_nick: str = None):
        await self.handle_shop(ctx, effect, member, new_nick, is_slash=False)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Handler commun
    # ────────────────────────────────────────────────────────────────────────────
    async def handle_shop(self, ctx_or_inter, effect, member, new_nick, is_slash: bool):
        send_func = safe_respond if is_slash else safe_send
        user = ctx_or_inter.user if is_slash else ctx_or_inter.author

        # Affichage du shop
        if not effect or not member:
            embed = discord.Embed(
                title="💸 ReiatsuShop",
                description="Voici les objets disponibles :" if is_slash else
                            "Voici les objets disponibles :\n💡 Pour acheter : `!!reiatsushop <zomb|mute|rename> @membre [nouveau pseudo]`",
                color=discord.Color.gold()
            )
            for item in self.shop_items.values():
                embed.add_field(
                    name=f"{item['emoji']} **{item['name']}** — `{item['price']} reiatsu`",
                    value=f"🕒 Durée : `{self.format_duration(item['duration'])}`\n💬 {item['description']}",
                    inline=False
                )
            await send_func(ctx_or_inter, embed=embed)
            return

        # Validation
        effect = effect.lower()
        if effect not in ["zomb", "mute", "rename"]:
            await send_func(ctx_or_inter, "❌ Effet invalide. Choisis `zomb`, `mute` ou `rename`.",
                            ephemeral=is_slash)
            return
        if effect == "rename" and not new_nick:
            await send_func(ctx_or_inter, "❌ Pour rename, indique le nouveau pseudo.", ephemeral=is_slash)
            return

        profile = ensure_profile(user.id, user.display_name)
        item_key = {"zomb": "zombification", "mute": "mute_temp", "rename": "rename_2j"}[effect]
        item = self.shop_items[item_key]

        if profile.get("points", 0) < item["price"]:
            await send_func(ctx_or_inter, f"❌ Pas assez de reiatsu pour **{item['name']}** !", ephemeral=is_slash)
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
    # 🔹 Application des effets
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

        # Application en mémoire et Discord
        if effect == "zomb":
            self.active_effects["zomb"][member.id] = guild_id
        elif effect == "rename":
            self.active_effects["rename"][member.id] = {"guild_id": guild_id, "nick": new_nick, "use_webhook": False}
            await self._apply_rename(member, new_nick)
        elif effect == "mute":
            await self._apply_mute(member, item["duration"], guild_id, end_time)

        # Supprimer automatiquement après la durée
        asyncio.create_task(self._remove_effect_after(member.id, effect, item["duration"]))

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Helpers internes pour effets
    # ────────────────────────────────────────────────────────────────────────────
    async def _apply_rename(self, member: discord.Member, new_nick: str):
        try:
            await member.edit(nick=new_nick)
        except discord.Forbidden:
            self.active_effects["rename"][member.id]["use_webhook"] = True

    async def _apply_mute(self, member: discord.Member, duration: int, guild_id: int, end_time: datetime.datetime):
        if member.guild.me.guild_permissions.moderate_members:
            try:
                await member.timeout(datetime.timedelta(seconds=duration))
            except discord.Forbidden:
                self.active_effects["mute"][member.id] = {"guild_id": guild_id, "end_time": end_time}
        else:
            self.active_effects["mute"][member.id] = {"guild_id": guild_id, "end_time": end_time}

    async def _remove_effect_after(self, user_id: int, effect: str, duration: int):
        await asyncio.sleep(duration)
        self.active_effects["zomb"].pop(user_id, None)
        self.active_effects["rename"].pop(user_id, None)
        self.active_effects["mute"].pop(user_id, None)

        profile = ensure_profile(user_id, "")
        effects = profile.get("shop_effets") or []
        now = datetime.datetime.utcnow()
        effects = [e for e in effects if e["effect_key"] != effect or datetime.datetime.fromisoformat(e["end_time"]) > now]
        supabase.table("reiatsu").update({"shop_effets": effects}).eq("user_id", user_id).execute()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Listeners pour fallback et effets actifs
    # ────────────────────────────────────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        guild_id = message.guild.id
        user_id = message.author.id

        # Mute fallback
        mute_data = self.active_effects["mute"].get(user_id)
        if mute_data and mute_data["guild_id"] == guild_id:
            await message.delete()
            return

        # Zombification
        if self.active_effects["zomb"].get(user_id) == guild_id:
            if not message.content.startswith(("!!", "$", "dun", "Dun")) and random.randint(1, 3) == 1:
                await self._send_webhook(message, message.content + " arrrg cerveau...")
                await message.delete()

        # Rename fallback
        rename_data = self.active_effects["rename"].get(user_id)
        if rename_data and rename_data["guild_id"] == guild_id and rename_data.get("use_webhook"):
            await self._send_webhook(message, message.content, username=rename_data["nick"])
            await message.delete()

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        data = self.active_effects["rename"].get(after.id)
        if data and data["guild_id"] == after.guild.id and after.display_name != data["nick"]:
            if not data.get("use_webhook"):
                try:
                    await after.edit(nick=data["nick"])
                except:
                    self.active_effects["rename"][after.id]["use_webhook"] = True

    async def _send_webhook(self, message: discord.Message, content: str, username: str = None):
        webhook = await message.channel.create_webhook(name=username or f"tmp-{message.author.name}")
        try:
            await webhook.send(username=username or message.author.display_name,
                               avatar_url=message.author.display_avatar.url,
                               content=content)
        finally:
            await webhook.delete()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Nettoyage périodique
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
                    key = e["effect_key"]
                    self.active_effects[key].pop(user_id, None)

            if len(new_effects) != len(effects):
                supabase.table("reiatsu").update({"shop_effets": new_effects}).eq("user_id", user_id).execute()

    @clean_expired_effects.before_loop
    async def before_clean_expired_effects(self):
        await self.bot.wait_until_ready()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Helper pour formater la durée
    # ────────────────────────────────────────────────────────────────────────────
    def format_duration(self, seconds: int) -> str:
        days, remainder = divmod(seconds, 86400)
        hours, _ = divmod(remainder, 3600)
        return " ".join(filter(None, [f"{days}j" if days else "", f"{hours}h" if hours else ""])) or "0h"

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = ReiatsuShop(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Reiatsu"
    await bot.add_cog(cog)
