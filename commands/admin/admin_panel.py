# ────────────────────────────────────────────────────────────────────────────────
# 📌 admin_panel.py
# Objectif : Afficher un embed avec un bouton vers le panneau admin
# Catégorie : Admin
# Accès : Admin uniquement
# Cooldown : 5s
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import logging
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button

from utils.discord_utils import safe_send, safe_respond
from utils.init_db import get_conn

log = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────────────────────────
# 🗄️ Accès base de données locale
# ────────────────────────────────────────────────────────────────────────────────

def db_get_tunnel_url() -> str | None:
    """Récupère l'URL du tunnel Cloudflare stockée en base."""
    try:
        conn   = get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM config WHERE key = 'tunnel_url'")
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None
    except Exception as e:
        log.exception("[admin_panel] Erreur lecture tunnel_url : %s", e)
        return None

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ UI — View avec bouton
# ────────────────────────────────────────────────────────────────────────────────

class AdminPanelView(View):
    """View contenant le bouton vers le panneau admin."""
    def __init__(self, url: str):
        super().__init__(timeout=120)
        self.add_item(Button(
            label="Accéder au panneau admin",
            url=url,
            style=discord.ButtonStyle.link
        ))

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────

class AdminPanelCog(commands.Cog):
    """Commandes /adminpanel et !adminpanel — Affiche le lien vers le panneau admin."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction interne commune
    # ────────────────────────────────────────────────────────────────────────────
    def _build_embed_and_view(self) -> tuple[discord.Embed, AdminPanelView | None]:
        """Construit l'embed et la view en lisant l'URL depuis la base."""
        url = db_get_tunnel_url()

        embed = discord.Embed(
            title="🔒 Panneau Admin",
            description="Clique sur le bouton ci-dessous pour accéder au panneau d'administration.",
            color=discord.Color.blue()
        )
        embed.set_footer(text="⚠️ Accès réservé aux administrateurs.")

        if not url:
            embed.add_field(
                name="⚠️ Tunnel indisponible",
                value="Aucune URL de tunnel trouvée. Relance le bot avec `start.sh`.",
                inline=False
            )
            return embed, None

        embed.add_field(name="🌐 URL active", value=f"`{url}`", inline=False)
        return embed, AdminPanelView(url)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="adminpanel",
        description="Afficher le lien du panneau admin."
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def slash_admin_panel(self, interaction: discord.Interaction):
        embed, view = self._build_embed_and_view()
        await interaction.response.send_message(
            embed=embed,
            view=view if view else discord.utils.MISSING,
            ephemeral=True
        )

    @slash_admin_panel.error
    async def slash_admin_panel_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await safe_respond(interaction, "❌ Tu n'as pas la permission.", ephemeral=True)
        else:
            log.exception("[/adminpanel] Erreur non gérée : %s", error)
            await safe_respond(interaction, "❌ Une erreur est survenue.", ephemeral=True)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(
        name="adminpanel",
        help="🔒 Affiche le lien du panneau admin."
    )
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def prefix_admin_panel(self, ctx: commands.Context):
        embed, view = self._build_embed_and_view()
        await safe_send(ctx.channel, embed=embed, view=view)

    @prefix_admin_panel.error
    async def prefix_admin_panel_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.MissingPermissions):
            await safe_send(ctx.channel, "❌ Tu n'as pas la permission.")
        elif isinstance(error, commands.CommandOnCooldown):
            await safe_send(ctx.channel, f"⏳ Attends encore {error.retry_after:.1f}s.")
        else:
            log.exception("[!adminpanel] Erreur non gérée : %s", error)
            await safe_send(ctx.channel, "❌ Une erreur est survenue.")

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = AdminPanelCog(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Admin"
    await bot.add_cog(cog)
