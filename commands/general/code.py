# ================================================================================
# 📌 code.py — Commande simple /code et !code
# Objectif : Affiche un lien cliquable vers le code source du bot
# Catégorie : Général
# Accès : Public
# Cooldown : Paramétrable par commande
# ================================================================================

# ================================================================================
# 📦 Imports nécessaires
# ================================================================================
import discord
from discord import app_commands
from discord.ext import commands
from utils.discord_utils import safe_send, safe_respond  

# ================================================================================
# 🧠 Cog principal avec centralisation erreurs et cooldowns
# ================================================================================
class CodeCommand(commands.Cog):
    """
    Commande /code et !code — Affiche un lien vers le code source du bot
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.github_url = "https://github.com/kevinraphael95/kisuke"

    # ============================================================================
    # 🔹 Fonction interne commune
    # ============================================================================
    async def _send_code_safe(self, channel: discord.abc.Messageable):
        """Envoie l’embed avec le bouton GitHub."""
        embed = discord.Embed(
            title="📂 Code source du bot",
            description="Voici le lien vers le dépôt GitHub contenant **tout le code** du bot.",
            color=discord.Color.blurple()
        )
        embed.set_thumbnail(url="https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png")
        embed.set_footer(text="Kisuke Urahara")

        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="🔗 Voir sur GitHub", url=self.github_url, style=discord.ButtonStyle.link))

        await safe_send(channel, embed=embed, view=view)

    # ============================================================================
    # 🔹 Commande SLASH
    # ============================================================================
    @app_commands.command(
        name="code",
        description="Affiche un lien cliquable vers le code source du bot."
    )
    @app_commands.checks.cooldown(rate=1, per=3.0, key=lambda i: i.user.id)
    async def slash_code(self, interaction: discord.Interaction):
        """Commande slash principale."""
        await self._send_code_safe(interaction.channel)
        await safe_respond(interaction, "✅ Voici le code source :", ephemeral=True)

    # ============================================================================
    # 🔹 Commande PREFIX
    # ============================================================================
    @commands.command(name="code", help="Affiche un lien vers le code source du bot.")
    @commands.cooldown(1, 3.0, commands.BucketType.user)
    async def prefix_code(self, ctx: commands.Context):
        """Commande préfixe principale."""
        await self._send_code_safe(ctx.channel)

# ================================================================================
# 🔌 Setup du Cog
# ================================================================================
async def setup(bot: commands.Bot):
    cog = CodeCommand(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Général"
    await bot.add_cog(cog)
