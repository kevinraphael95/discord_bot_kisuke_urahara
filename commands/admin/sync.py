# ────────────────────────────────────────────────────────────────────────────────
# 📌 sync.py — Commande simple /sync et !sync
# Objectif : Synchroniser les commandes slash avec Discord (serveur ou global)
# Catégorie : Admin
# Accès : Owner uniquement
# Cooldown : 1 utilisation / 10 secondes / utilisateur
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

class Sync(commands.Cog):
    """
    Commandes /sync et !sync — Synchronise les commandes slash (serveur ou global).
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction interne commune
    # ────────────────────────────────────────────────────────────────────────────
    async def _sync_logic(self, guild: discord.Guild | None, scope: str | None) -> str:
        if scope and scope.lower() == "global":
            synced = await self.bot.tree.sync()
            return f"🌍 **{len(synced)} commandes globales synchronisées avec Discord !**"

        if guild:
            self.bot.tree.copy_global_to(guild=guild)
            synced = await self.bot.tree.sync(guild=guild)
            return f"🏠 **{len(synced)} commandes synchronisées uniquement pour ce serveur !**"

        return "❌ Impossible de synchroniser localement en dehors d'un serveur."

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(name="sync",description="Synchronise les commandes slash (serveur ou global).")
    @app_commands.describe(scope="Tape 'global' pour synchroniser toutes les guildes.")
    @app_commands.check(lambda i: i.client.is_owner(i.user))
    @app_commands.checks.cooldown(rate=1, per=10.0, key=lambda i: i.user.id)
    async def slash_sync(self, interaction: discord.Interaction, scope: str = None):
        msg = await self._sync_logic(interaction.guild, scope)
        await safe_respond(interaction, msg, ephemeral=True)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="sync",help="Synchronise les commandes slash (serveur ou global).")
    @commands.is_owner()
    @commands.cooldown(1, 10.0, commands.BucketType.user)
    async def prefix_sync(self, ctx: commands.Context, scope: str = None):
        msg = await self._sync_logic(ctx.guild, scope)
        await safe_send(ctx.channel, msg)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Sync(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Admin"
    await bot.add_cog(cog)
