# ────────────────────────────────────────────────────────────────────────────────
# 📌 reiatsushop.py — Commande /reiatsushop et !reiatsushop
# Objectif : Afficher la liste des objets disponibles dans le ReiatsuShop
# Catégorie : Reiatsu
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
from utils.discord_utils import safe_send, safe_respond
from utils.shop_utils import load_shop_items

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class ReiatsuShop(commands.Cog):
    """
    Commande /reiatsushop et !reiatsushop — Affiche les objets achetables du shop Reiatsu
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="reiatsushop",
        description="Affiche la liste des objets disponibles dans le ReiatsuShop."
    )
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_reiatsushop(self, interaction: discord.Interaction):
        """Commande slash ReiatsuShop"""
        items = load_shop_items()

        embed = discord.Embed(
            title="💸 ReiatsuShop",
            description="Voici les objets mystiques que tu peux acheter avec ton Reiatsu.",
            color=discord.Color.gold()
        )

        for key, item in items.items():
            embed.add_field(
                name=f"{item['emoji']} **{item['name']}** — `{item['price']} reiatsu`",
                value=f"🕒 Durée : `{item['duration'] // 3600}h`\n💬 {item['description']}",
                inline=False
            )

        await safe_respond(interaction, embed=embed)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="reiatsushop")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_reiatsushop(self, ctx: commands.Context):
        """Commande préfixe ReiatsuShop"""
        items = load_shop_items()

        embed = discord.Embed(
            title="💸 ReiatsuShop",
            description="Voici les objets mystiques que tu peux acheter avec ton Reiatsu.",
            color=discord.Color.gold()
        )

        for key, item in items.items():
            embed.add_field(
                name=f"{item['emoji']} **{item['name']}** — `{item['price']} reiatsu`",
                value=f"🕒 Durée : `{item['duration'] // 3600}h`\n💬 {item['description']}",
                inline=False
            )

        await safe_send(ctx.channel, embed=embed)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = ReiatsuShop(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Reiatsu"
    await bot.add_cog(cog)
