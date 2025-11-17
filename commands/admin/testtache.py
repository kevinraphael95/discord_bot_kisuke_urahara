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
from utils.discord_utils import safe_send
from utils.taches import TACHES  # Auto-import de toutes les tâches définies
# TACHES = [lancer_emoji, lancer_reflexe, lancer_fleche, ...]

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class TestTache(commands.Cog):
    """
    Commande /testtache et !testtache — Teste automatiquement toutes les tâches
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ───────────────────────────────────────────────────────────────
    # 🔹 SLASH COMMAND
    # ───────────────────────────────────────────────────────────────
    @app_commands.command(
        name="testtache",
        description="🕹️ Teste toutes les tâches interactives dynamiquement."
    )
    @app_commands.checks.cooldown(1, 10.0, key=lambda i: i.user.id)
    async def slash_testtache(self, interaction: discord.Interaction):

        embed = discord.Embed(
            title="🔹 Test des épreuves",
            description=f"{interaction.user.mention}, lancement de **toutes les épreuves** détectées !",
            color=discord.Color.blue()
        )
        embed.add_field(name="Préparation...", value="Détection des tâches...", inline=False)

        await interaction.response.send_message(embed=embed)
        msg = await interaction.original_response()

        async def update_embed(e: discord.Embed):
            await msg.edit(embed=e)

        # ─────── Détection auto des tâches ───────
        liste_taches = TACHES  # Importé depuis utils/taches.py

        reussites = True

        for i, tache in enumerate(liste_taches, start=1):

            nom = f"Épreuve {i}"

            # Mise en forme identique à Hollow
            embed.set_field_at(0, name=nom, value="🔹 En cours...", inline=False)
            await update_embed(embed)

            try:
                ok = await tache(interaction, embed, update_embed, i)
            except Exception:
                ok = False

            embed.set_field_at(0, name=nom, value="✅ Réussie" if ok else "❌ Ratée", inline=False)
            await update_embed(embed)

            reussites = reussites and ok

        # ─────── Résultat final ───────
        result = discord.Embed(
            title="🎯 Résultat du test",
            description=(
                "🎉 Toutes les épreuves ont été validées !" if reussites
                else "💀 Certaines épreuves ont échoué…"
            ),
            color=discord.Color.green() if reussites else discord.Color.red()
        )
        await msg.edit(embed=result)

    # ───────────────────────────────────────────────────────────────
    # 🔹 PREFIX COMMAND
    # ───────────────────────────────────────────────────────────────
    @commands.command(name="testtache")
    @commands.cooldown(1, 10.0, commands.BucketType.user)
    async def prefix_testtache(self, ctx: commands.Context):

        embed = discord.Embed(
            title="🔹 Test des épreuves",
            description=f"{ctx.author.mention}, lancement de **toutes les épreuves détectées** !",
            color=discord.Color.blue()
        )
        embed.add_field(name="Préparation...", value="Détection des tâches...", inline=False)

        msg = await safe_send(ctx.channel, embed=embed)

        async def update_embed(e: discord.Embed):
            await msg.edit(embed=e)

        liste_taches = TACHES

        reussites = True

        for i, tache in enumerate(liste_taches, start=1):

            nom = f"Épreuve {i}"

            embed.set_field_at(0, name=nom, value="🔹 En cours...", inline=False)
            await update_embed(embed)

            try:
                ok = await tache(ctx, embed, update_embed, i)
            except Exception:
                ok = False

            embed.set_field_at(0, name=nom, value="✅ Réussie" if ok else "❌ Ratée", inline=False)
            await update_embed(embed)

            reussites = reussites and ok

        result = discord.Embed(
            title="🎯 Résultat du test",
            description="🎉 Toutes les épreuves réussies !" if reussites else "💀 Certaines ont échoué…",
            color=discord.Color.green() if reussites else discord.Color.red()
        )
        await msg.edit(embed=result)


# ───────────────────────────────────────────────────────────────
# 🔌 Setup du COG
# ───────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = TestTache(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Admin"
    await bot.add_cog(cog)


