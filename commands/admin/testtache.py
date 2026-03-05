# ────────────────────────────────────────────────────────────────────────────────
# 📌 testtache.py — Commande simple /testtache et !testtache
# Objectif : Tester les 3 épreuves interactives (mini-jeux)
# Catégorie : Admin
# Accès : Tous
# Cooldown : 1 utilisation / 10 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands

from utils.discord_utils import safe_send, safe_edit, safe_respond
from utils.taches import TACHES

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────

class TestTache(commands.Cog):
    """
    Commandes /testtache et !testtache — Teste automatiquement toutes les tâches.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction interne commune
    # ────────────────────────────────────────────────────────────────────────────
    async def _run_taches(self, ctx_or_interaction, msg: discord.Message, embed: discord.Embed):
        """Lance toutes les tâches et met à jour l'embed au fur et à mesure."""
        async def update_embed(e: discord.Embed):
            await safe_edit(msg, embed=e)

        reussites = True

        for i, tache in enumerate(TACHES, start=1):
            nom = f"Épreuve {i}"
            embed.set_field_at(0, name=nom, value="🔹 En cours...", inline=False)
            await update_embed(embed)

            try:
                ok = await tache(ctx_or_interaction, embed, update_embed, i)
            except Exception:
                ok = False

            embed.set_field_at(0, name=nom, value="✅ Réussie" if ok else "❌ Ratée", inline=False)
            await update_embed(embed)
            reussites = reussites and ok

        result = discord.Embed(
            title="🎯 Résultat du test",
            description="🎉 Toutes les épreuves ont été validées !" if reussites else "💀 Certaines épreuves ont échoué…",
            color=discord.Color.green() if reussites else discord.Color.red()
        )
        await safe_edit(msg, embed=result)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="testtache",
        description="🕹️ Teste toutes les épreuves pour la commande hollow."
    )
    @app_commands.checks.cooldown(rate=1, per=10.0, key=lambda i: i.user.id)
    async def slash_testtache(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🔹 Test des épreuves",
            description=f"{interaction.user.mention}, lancement de **toutes les épreuves** détectées !",
            color=discord.Color.blue()
        )
        embed.add_field(name="Préparation...", value="Détection des tâches...", inline=False)
        await safe_respond(interaction, embed=embed)
        msg = await interaction.original_response()
        await self._run_taches(interaction, msg, embed)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(
        name="testtache",
        help="🕹️ Teste toutes les épreuves pour la commande hollow."
    )
    @commands.cooldown(1, 10.0, commands.BucketType.user)
    async def prefix_testtache(self, ctx: commands.Context):
        embed = discord.Embed(
            title="🔹 Test des épreuves",
            description=f"{ctx.author.mention}, lancement de **toutes les épreuves détectées** !",
            color=discord.Color.blue()
        )
        embed.add_field(name="Préparation...", value="Détection des tâches...", inline=False)
        msg = await safe_send(ctx.channel, embed=embed)
        await self._run_taches(ctx, msg, embed)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = TestTache(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Admin"
    await bot.add_cog(cog)
