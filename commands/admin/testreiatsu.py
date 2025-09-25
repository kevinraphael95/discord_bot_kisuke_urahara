# ────────────────────────────────────────────────────────────────────────────────
# 📌 test_reiatsu.py — Commande interactive /testreiatsu et !testreiatsu
# Objectif : Vérifier que les réactions 💠 sont bien captées par le bot
# Catégorie : Debug
# Accès : Admins / Développeurs
# Cooldown : 5 secondes
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
import os

from utils.discord_utils import safe_send  

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal — TestReaction
# ────────────────────────────────────────────────────────────────────────────────
class TestReaction(commands.Cog):
    """
    Commande /testreiatsu et !testreiatsu — Envoie un embed test avec 💠
    et vérifie si l’événement on_raw_reaction_add est bien capté.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction interne commune
    # ────────────────────────────────────────────────────────────────────────────
    async def _send_test_embed(self, channel: discord.abc.Messageable):
        embed = discord.Embed(
            title="💠 Test Reiatsu",
            description="Clique sur 💠 pour vérifier que la réaction est captée.",
            color=discord.Color.blue()
        )
        message = await safe_send(channel, embed=embed)
        if message:
            await message.add_reaction("💠")

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="testreiatsu",
        description="Teste la détection des réactions 💠."
    )
    @app_commands.checks.cooldown(rate=1, per=5.0, key=lambda i: i.user.id)
    async def slash_testreiatsu(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self._send_test_embed(interaction.channel)
        await interaction.delete_original_response()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="testreiatsu")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_testreiatsu(self, ctx: commands.Context):
        await self._send_test_embed(ctx.channel)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Listener — Détection des réactions
    # ────────────────────────────────────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        print(f"[DEBUG] Event capté → emoji={payload.emoji}, user={payload.user_id}, msg={payload.message_id}")

        if payload.emoji.name != "💠" or payload.user_id == self.bot.user.id:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        channel = guild.get_channel(payload.channel_id)
        user = guild.get_member(payload.user_id)
        if not channel or not user:
            return

        await safe_send(channel, f"✅ {user.mention} a bien cliqué sur 💠 !")

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = TestReaction(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Admin"
    await bot.add_cog(cog)
