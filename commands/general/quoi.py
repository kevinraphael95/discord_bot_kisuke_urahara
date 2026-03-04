# ────────────────────────────────────────────────────────────────────────────────
# 📌 feur.py
# Objectif : Répond "feur"
# Catégorie : Général
# Accès : Tous
# Cooldown : 3 secondes
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands

from utils.discord_utils import safe_send, safe_respond  

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class Feur(commands.Cog):
    """
    Commande /feur et !feur — Répond simplement "feur"
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="quoi",
        description="Répond feur."
    )
    @app_commands.checks.cooldown(rate=1, per=3.0, key=lambda i: i.user.id)
    async def slash_feur(self, interaction: discord.Interaction):
        await safe_respond(interaction, "feur!!")

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="quoi", help="Répond feur.")
    @commands.cooldown(1, 3.0, commands.BucketType.user)
    async def prefix_feur(self, ctx: commands.Context):
        await safe_send(ctx.channel, "feur!!")

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Feur(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Général"
    await bot.add_cog(cog)
