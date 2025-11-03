# ────────────────────────────────────────────────────────────────────────────────
# 📌 jardin.py — Commande interactive /jardin et !jardin
# Objectif : Chaque utilisateur a un jardin persistant avec des fleurs
# Catégorie : Jeu
# Accès : Tout le monde
# Cooldown : Paramétrable par commande
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
from utils.discord_utils import safe_send, safe_respond
from utils.jardin_utils import get_or_create_garden, build_garden_embed
from utils.jardin_ui_utils import JardinView


# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class Jardin(commands.Cog):
    """Commande /jardin et !jardin — Voir son jardin"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _send_garden(self, target_user, viewer_id, respond_func):
        """Affiche le jardin d’un utilisateur donné."""
        try:
            garden = await get_or_create_garden(target_user.id, target_user.name)
            embed = build_garden_embed(garden, viewer_id)
            view = None

            if target_user.id == viewer_id:
                view = JardinView(garden, viewer_id)
                view.update_buttons()

            await respond_func(embed=embed, view=view)

        except Exception as e:
            print(f"[ERREUR jardin] {e}")
            await respond_func("❌ Une erreur est survenue.", ephemeral=True)


    # ──────────────────────────────────────────────────────────────────────────────
    # Commande Slash
    # ──────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="jardin",
        description="Affiche ton jardin ou celui d'un autre utilisateur 🌱"
    )
    @app_commands.checks.cooldown(1, 5.0)
    async def slash_jardin(self, interaction: discord.Interaction, user: discord.User = None):
        target = user or interaction.user
        await self._send_garden(target, interaction.user.id, lambda **kwargs: safe_respond(interaction, **kwargs))


    # ──────────────────────────────────────────────────────────────────────────────
    # Commande Préfixe
    # ──────────────────────────────────────────────────────────────────────────────
    @commands.command(
        name="jardin",
        help="Affiche ton jardin ou celui d'un autre utilisateur 🌱"
    )
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    async def prefix_jardin(self, ctx: commands.Context, user: discord.User = None):
        target = user or ctx.author
        await self._send_garden(target, ctx.author.id, lambda **kwargs: safe_send(ctx.channel, **kwargs))


# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Jardin(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Jeux"
    await bot.add_cog(cog)
