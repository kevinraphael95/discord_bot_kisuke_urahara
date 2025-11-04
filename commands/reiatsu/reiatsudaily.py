# ────────────────────────────────────────────────────────────────────────────────#
# 📌 reiatsudaily.py — Commande simple /reiatsudaily et !reiatsudaily
# Objectif : Fausse commande de récompense journalière (troll)
# Catégorie : Fun
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────#

# ────────────────────────────────────────────────────────────────────────────────#
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
from utils.discord_utils import safe_send, safe_respond  # ✅ Utilitaires sécurisés

# ────────────────────────────────────────────────────────────────────────────────#
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class ReiatsuDaily(commands.Cog):
    """
    Commande /reiatsudaily et !reiatsudaily — Fausse récompense journalière (troll)
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="reiatsudaily",
        description="Récompense journalière Reiatsu (ou pas 👀)"
    )
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_reiatsudaily(self, interaction: discord.Interaction):
        """Commande slash troll avec image"""
        image_path = "data/images/not_a_rick_roll.jpg"

        embed = discord.Embed(
            title="🎁 Récompense journalière Reiatsu !",
            description="Tu croyais vraiment recevoir quelque chose ? 😏",
            color=discord.Color.purple()
        )
        file = discord.File(image_path, filename="reward.jpg")
        embed.set_image(url="attachment://reward.jpg")

        await safe_respond(interaction, embed=embed, file=file)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(
        name="reiatsudaily",
        aliases=["rd", "dailyreiatsu"]
    )
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_reiatsudaily(self, ctx: commands.Context):
        """Commande préfixe troll avec image"""
        image_path = "data/images/not_a_rick_roll.jpg"

        embed = discord.Embed(
            title="🎁 Récompense journalière Reiatsu !",
            description="Tu croyais vraiment recevoir quelque chose ? 😏",
            color=discord.Color.purple()
        )
        file = discord.File(image_path, filename="reward.jpg")
        embed.set_image(url="attachment://reward.jpg")

        await safe_send(ctx.channel, embed=embed, file=file)

# ────────────────────────────────────────────────────────────────────────────────#
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = ReiatsuDaily(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Fun"
    await bot.add_cog(cog)


