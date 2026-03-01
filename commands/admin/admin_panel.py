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
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button

from utils.discord_utils import safe_send, safe_edit, safe_respond, safe_delete  

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ UI — View avec bouton
# ────────────────────────────────────────────────────────────────────────────────
ADMIN_PANEL_LINK = "https://observation-named-selected-clerk.trycloudflare.com/"

class AdminPanelView(View):
    """View contenant le bouton vers le panneau admin"""
    def __init__(self):
        super().__init__(timeout=120)
        button = Button(
            label="Accéder au panneau admin",
            url=ADMIN_PANEL_LINK,
            style=discord.ButtonStyle.link
        )
        self.add_item(button)

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal avec cooldowns centralisés
# ────────────────────────────────────────────────────────────────────────────────
class AdminPanelCog(commands.Cog):
    """
    Commande /adminpanel et !adminpanel — Affiche un embed avec un bouton vers le panneau admin
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction interne commune
    # ────────────────────────────────────────────────────────────────────────────
    async def _send_admin_panel(self, channel: discord.abc.Messageable):
        embed = discord.Embed(
            title="🔒 Panneau Admin",
            description="Clique sur le bouton ci-dessous pour accéder au panneau d'administration.",
            color=discord.Color.blue()
        )
        embed.set_footer(text="⚠️ Accès réservé aux administrateurs.")
        view = AdminPanelView()
        await safe_send(channel, embed=embed, view=view)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="adminpanel",
        description="Afficher le lien du panneau admin"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def slash_admin_panel(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🔒 Panneau Admin",
            description="Clique sur le bouton ci-dessous pour accéder au panneau d'administration.",
            color=discord.Color.blue()
        )
        embed.set_footer(text="⚠️ Accès réservé aux administrateurs.")
        view = AdminPanelView()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="adminpanel")
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def prefix_admin_panel(self, ctx: commands.Context):
        await self._send_admin_panel(ctx.channel)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = AdminPanelCog(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Admin"
    await bot.add_cog(cog)
