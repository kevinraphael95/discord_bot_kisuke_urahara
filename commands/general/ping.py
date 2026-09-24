# ================================================================================
# 📌 ping.py
# Objectif : Vérifie la latence du bot
# Catégorie : 🧱 Général
# Accès : Public
# Cooldown : 5s
# ================================================================================

# ================================================================================
# 📦 Imports nécessaires
# ================================================================================
import discord
from discord import app_commands
from discord.ext import commands

from utils.discord_utils import safe_send

# ================================================================================
# 🧠 Cog principal
# ================================================================================
class Ping(commands.Cog):
    """Commande /ping et !ping — Vérifie la latence du bot."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ============================================================================
    # 🔹 Fonction interne commune
    # ============================================================================
    async def _send_ping(self, channel: discord.abc.Messageable):
        try:
            latence = round(self.bot.latency * 1000)
            await safe_send(channel, f"🏓 Pong ! Latence : **{latence} ms**")
        except Exception as e:
            print("[ERREUR ping]", e)
            await safe_send(channel, "❌ Une erreur est survenue lors de l'exécution de la commande.")

    # ============================================================================
    # 🔹 Commande SLASH
    # ============================================================================
    @app_commands.command(
        name="ping",
        description="Affiche la latence actuelle du bot."
    )
    @app_commands.checks.cooldown(rate=1, per=5.0, key=lambda i: i.user.id)
    async def slash_ping(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self._send_ping(interaction.channel)
        await interaction.delete_original_response()

    # ============================================================================
    # 🔹 Commande PREFIX
    # ============================================================================
    @commands.command(name="ping", aliases=["pong", "latence"], help="Affiche la latence actuelle du bot.")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_ping(self, ctx: commands.Context):
        await self._send_ping(ctx.channel)

# ================================================================================
# 🔌 Setup du Cog
# ================================================================================
async def setup(bot: commands.Bot):
    cog = Ping(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Général"
    await bot.add_cog(cog)
