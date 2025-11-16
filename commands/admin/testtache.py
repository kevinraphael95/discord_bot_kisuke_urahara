# ────────────────────────────────────────────────────────────────────────────────
# 📌 testtache.py — Commande simple /testtache et !testtache
# Objectif : Tester les 3 épreuves interactives (mini-jeux)
# Catégorie : Fun
# Accès : Tous
# Cooldown : 1 utilisation / 10 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
from utils.discord_utils import safe_send, safe_respond
from utils.taches import lancer_3_taches

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class TestTache(commands.Cog):
    """
    Commande /testtache et !testtache — Tester les 3 épreuves interactives
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="testtache",
        description="🕹️ Teste les 3 épreuves interactives dans un embed."
    )
    @app_commands.checks.cooldown(1, 10.0, key=lambda i: i.user.id)
    async def slash_testtache(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🔹 Test des épreuves",
            description=f"{interaction.user.mention}, prépare-toi à tester 3 épreuves !",
            color=discord.Color.blue()
        )
        embed.add_field(name="Préparation...", value="Les épreuves vont commencer...", inline=False)
        msg = await interaction.response.send_message(embed=embed, ephemeral=False)
        msg_obj = await interaction.original_response()

        async def update_embed(e: discord.Embed):
            await msg_obj.edit(embed=e)

        try:
            victoire = await lancer_3_taches(interaction, embed, update_embed)
        except Exception as ex:
            await safe_respond(interaction, f"⚠️ Une erreur est survenue : {ex}")
            return

        result = discord.Embed(
            title="🎯 Résultat du test",
            description="✅ Toutes les épreuves réussies !" if victoire else "❌ Certaines épreuves ont échoué...",
            color=discord.Color.green() if victoire else discord.Color.red()
        )
        await msg_obj.edit(embed=result)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="testtache")
    @commands.cooldown(1, 10.0, commands.BucketType.user)
    async def prefix_testtache(self, ctx: commands.Context):
        embed = discord.Embed(
            title="🔹 Test des épreuves",
            description=f"{ctx.author.mention}, prépare-toi à tester 3 épreuves !",
            color=discord.Color.blue()
        )
        embed.add_field(name="Préparation...", value="Les épreuves vont commencer...", inline=False)
        msg = await safe_send(ctx.channel, embed=embed)

        async def update_embed(e: discord.Embed):
            await msg.edit(embed=e)

        try:
            victoire = await lancer_3_taches(ctx, embed, update_embed)
        except Exception as ex:
            await safe_send(ctx.channel, f"⚠️ Une erreur est survenue : {ex}")
            return

        result = discord.Embed(
            title="🎯 Résultat du test",
            description="✅ Toutes les épreuves réussies !" if victoire else "❌ Certaines épreuves ont échoué...",
            color=discord.Color.green() if victoire else discord.Color.red()
        )
        await msg.edit(embed=result)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = TestTache(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Fun"
    await bot.add_cog(cog)
