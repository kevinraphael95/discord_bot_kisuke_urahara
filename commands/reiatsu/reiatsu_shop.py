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
import json

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class ReiatsuShop(commands.Cog):
    """
    Commande /reiatsushop et !reiatsushop — Affiche les objets et applique leurs effets
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        # Effets actifs en mémoire
        self.active_zombie = set()
        self.active_rename = {}

        # Shop items
        self.shop_items = {
            "zombification": {
                "emoji": "🧟‍♂️",
                "name": "Zombification",
                "price": 750,
                "duration": 86400,
                "description": "Ajoute 'arrrg cerveau...' à tes messages."
            },
            "mute_temp": {
                "emoji": "🔇",
                "name": "Mute Temporaire",
                "price": 1000,
                "duration": 3600,
                "description": "Timeout le joueur pendant X temps."
            },
            "rename_7d": {
                "emoji": "🪞",
                "name": "Rename 7J",
                "price": 800,
                "duration": 604800,
                "description": "Force le pseudo et empêche de le changer pendant 7 jours."
            }
        }

        # Lancer la task de nettoyage des effets expirés
        self.clean_expired_effects.start()
        self.load_effects_from_db()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Pré-charger les effets actifs depuis la DB
    # ────────────────────────────────────────────────────────────────────────────
    def load_effects_from_db(self):
        """Charge tous les effets actifs en mémoire au démarrage du bot"""
        res = supabase.table("reiatsu").select("user_id, shop_effets").execute()
        for profile in res.data:
            effects = profile.get("shop_effets") or []
            now = datetime.datetime.utcnow()
            for eff in effects:
                end_time = datetime.datetime.fromisoformat(eff["end_time"])
                if end_time > now:
                    if eff["effect_key"] == "zomb":
                        self.active_zombie.add(int(profile["user_id"]))
                    elif eff["effect_key"] == "rename":
                        self.active_rename[int(profile["user_id"])] = None

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="reiatsushop",
        description="Affiche les objets disponibles et active leurs effets."
    )
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_reiatsushop(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="💸 ReiatsuShop",
            description="Voici les objets disponibles :",
            color=discord.Color.gold()
        )
        for key, item in self.shop_items.items():
            embed.add_field(
                name=f"{item['emoji']} **{item['name']}** — `{item['price']} reiatsu`",
                value=f"🕒 Durée : `{self.format_duration(item['duration'])}`\n💬 {item['description']}",
                inline=False
            )
        await safe_respond(interaction, embed=embed)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="reiatsushop", aliases=["rtsshop"])
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_reiatsushop(self, ctx: commands.Context, effect: str = None, member: discord.Member = None):
        """
        Utilisation : !!reiatsushop <zomb|mute|rename> @membre
        Active immédiatement l'effet sur le membre mentionné
        """
        if effect is None or member is None:
            embed = discord.Embed(
                title="💸 ReiatsuShop",
                description="Voici les objets disponibles :",
                color=discord.Color.gold()
            )
            for key, item in self.shop_items.items():
                embed.add_field(
                    name=f"{item['emoji']} **{item['name']}** — `{item['price']} reiatsu`",
                    value=f"🕒 Durée : `{self.format_duration(item['duration'])}`\n💬 {item['description']}",
                    inline=False
                )
            await safe_send(ctx.channel, embed=embed)
            return

        effect = effect.lower()
        if effect not in ["zomb", "mute", "rename"]:
            await safe_send(ctx.channel, "❌ Effet invalide. Choisis `zomb`, `mute` ou `rename`.")
            return

        await self.apply_effect(member, effect)
        await safe_send(ctx.channel, f"✅ {member.mention} est affecté par **{effect}** pour la durée correspondante !")

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Appliquer un effet et stocker en DB
    # ────────────────────────────────────────────────────────────────────────────
    async def apply_effect(self, member: discord.Member, effect: str):
        item_key = {"zomb":"zombification","mute":"mute_temp","rename":"rename_7d"}[effect]
        item = self.shop_items[item_key]
        start_time = datetime.datetime.utcnow()
        end_time = start_time + datetime.timedelta(seconds=item["duration"])

        # ⚡ S'assurer que le profil existe et récupérer shop_effets
        profile = ensure_profile(member.id, member.display_name)
        effects = profile.get("shop_effets") or []

        # Ajouter l'effet au JSON
        effects.append({
            "effect_key": effect,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        })
        supabase.table("reiatsu").update({"shop_effets": effects}).eq("user_id", member.id).execute()

        # Activer en mémoire
        if effect == "zomb":
            self.active_zombie.add(member.id)
        elif effect == "rename":
            self.active_rename[member.id] = member.display_name
        elif effect == "mute":
            if member.guild.me.guild_permissions.moderate_members:
                await member.timeout(item["duration"])

        # Task pour retirer l'effet en mémoire et DB
        async def remove_effect():
            await asyncio.sleep(item["duration"])
            self.active_zombie.discard(member.id)
            self.active_rename.pop(member.id, None)

            # ⚡ S'assurer que le profil existe avant nettoyage
            profile = ensure_profile(member.id, member.display_name)
            effects = profile.get("shop_effets") or []
            effects = [e for e in effects if e["effect_key"] != effect or datetime.datetime.fromisoformat(e["end_time"]) > datetime.datetime.utcnow()]
            supabase.table("reiatsu").update({"shop_effets": effects}).eq("user_id", member.id).execute()

        asyncio.create_task(remove_effect())

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Listeners pour appliquer certains effets
    # ────────────────────────────────────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        if message.author.id in self.active_zombie:
            new_content = message.content + " arrrg cerveau..."
            await message.channel.send(f"{message.author.mention} dit : {new_content}")
            await message.delete()

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if after.id in self.active_rename:
            forced_nick = self.active_rename.get(after.id)
            if forced_nick and after.display_name != forced_nick:
                try:
                    await after.edit(nick=forced_nick)
                except:
                    pass  # Pas la permission

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Task pour nettoyer les effets expirés périodiquement
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
                        self.active_zombie.discard(user_id)
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
        parts = []
        if days > 0:
            parts.append(f"{days}j")
        if hours > 0:
            parts.append(f"{hours}h")
        return " ".join(parts) if parts else "0h"

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = ReiatsuShop(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Reiatsu"
    await bot.add_cog(cog)
