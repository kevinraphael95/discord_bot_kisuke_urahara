# ────────────────────────────────────────────────────────────────────────────────
# 📌 scans.py — Commande interactive /scans et !scans
# Objectif : Lire des scans depuis data/images/scans/<nom_dossier>
# Catégorie : Bleach
# Accès : Tous
# Cooldown : 1 commande toutes les 5s par utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button, Select
import os

from utils.discord_utils import safe_send, safe_edit, safe_respond, safe_delete  

# ────────────────────────────────────────────────────────────────────────────────
# 📂 Gestion des scans
# ────────────────────────────────────────────────────────────────────────────────
SCANS_FOLDER = os.path.join("data", "images", "scans")

def get_folders():
    """Retourne la liste des dossiers disponibles dans scans/."""
    try:
        return sorted([f for f in os.listdir(SCANS_FOLDER) if os.path.isdir(os.path.join(SCANS_FOLDER, f))])
    except Exception as e:
        print(f"[ERREUR SCANS] Impossible de charger {SCANS_FOLDER} : {e}")
        return []

def get_pages(folder):
    """Retourne les fichiers triés dans data/images/scans/<folder>."""
    target = os.path.join(SCANS_FOLDER, folder)
    try:
        return sorted(os.listdir(target))
    except Exception as e:
        print(f"[ERREUR SCANS] Impossible de charger {target} : {e}")
        return []

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ UI — Menu déroulant pour choisir le dossier
# ────────────────────────────────────────────────────────────────────────────────
class FolderSelect(Select):
    def __init__(self, cog, interaction_user):
        self.cog = cog
        self.interaction_user = interaction_user
        folders = get_folders()
        options = [discord.SelectOption(label=f, description=f"Dossier {f}") for f in folders]
        super().__init__(placeholder="📁 Choisis un dossier de scans", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.interaction_user.id:
            return await safe_respond(interaction, "❌ Ce menu n’est pas pour toi.", ephemeral=True)
        folder = self.values[0]
        await interaction.response.defer()
        await self.cog._start_scan(interaction.channel, interaction.user, folder, start_page=1)
        await safe_delete(self.view.message)
        self.view.stop()

class FolderSelectView(View):
    def __init__(self, cog, user):
        super().__init__(timeout=60)
        self.user = user
        self.message = None
        self.add_item(FolderSelect(cog, user))

    async def on_timeout(self):
        if self.message:
            await safe_edit(self.message, content="⏳ Menu expiré.", view=None)

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ UI — Pagination des pages
# ────────────────────────────────────────────────────────────────────────────────
class ScanView(View):
    def __init__(self, bot, folder, pages, start_page=1, user=None):
        super().__init__(timeout=120)
        self.bot = bot
        self.folder = folder
        self.pages = pages
        self.current_page = max(1, min(start_page, len(pages)))
        self.message = None
        self.user = user

    async def update_page(self):
        file_path = os.path.join(SCANS_FOLDER, self.folder, self.pages[self.current_page - 1])
        file = discord.File(file_path, filename=self.pages[self.current_page - 1])
        embed = discord.Embed(
            title=f"📖 Scan : {self.folder} — Page {self.current_page}/{len(self.pages)}",
            description="⬅️ Précédent | ➡️ Suivant | ❌ Fermer",
            color=discord.Color.orange()
        )
        embed.set_image(url=f"attachment://{self.pages[self.current_page - 1]}")
        await safe_edit(self.message, embed=embed, attachments=[file], view=self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.user and interaction.user.id != self.user.id:
            await safe_respond(interaction, "❌ Tu n’es pas autorisé à contrôler cette lecture.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="⬅️", style=discord.ButtonStyle.secondary)
    async def previous(self, interaction: discord.Interaction, button: Button):
        if self.current_page > 1:
            self.current_page -= 1
            await self.update_page()
        await interaction.response.defer()

    @discord.ui.button(label="➡️", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, button: Button):
        if self.current_page < len(self.pages):
            self.current_page += 1
            await self.update_page()
        await interaction.response.defer()

    @discord.ui.button(label="❌", style=discord.ButtonStyle.danger)
    async def close(self, interaction: discord.Interaction, button: Button):
        await safe_delete(self.message)
        self.stop()

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message:
            await safe_edit(self.message, view=self)

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class ScansBleach(commands.Cog):
    """
    Commande /scans et !scans — Lire des dossiers de scans
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction interne pour lancer la lecture
    # ────────────────────────────────────────────────────────────────────────────
    async def _start_scan(self, channel, user, folder, start_page=1):
        available = get_folders()
        if folder not in available:
            await safe_send(channel, f"❌ Dossier introuvable.\n📁 Dossiers disponibles : `{', '.join(available)}`")
            return
        pages = get_pages(folder)
        if not pages:
            await safe_send(channel, f"❌ Aucun fichier trouvé dans `{folder}`.")
            return
        view = ScanView(self.bot, folder, pages, start_page=start_page, user=user)
        file_path = os.path.join(SCANS_FOLDER, folder, pages[start_page - 1])
        file = discord.File(file_path, filename=pages[start_page - 1])
        embed = discord.Embed(
            title=f"📖 Scan : {folder} — Page {start_page}/{len(pages)}",
            description="⬅️ Précédent | ➡️ Suivant | ❌ Fermer",
            color=discord.Color.orange()
        )
        embed.set_image(url=f"attachment://{pages[start_page - 1]}")
        view.message = await safe_send(channel, embed=embed, file=file, view=view)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="scans",
        description="📖 Lire un dossier de scans (ex: pilote, chapitre_enfer...)."
    )
    @app_commands.describe(
        dossier="Nom du dossier dans data/images/scans/",
        page="Page de départ"
    )
    @app_commands.checks.cooldown(rate=1, per=5.0, key=lambda i: i.user.id)
    async def slash_scans(self, interaction: discord.Interaction, dossier: str | None = None, page: int = 1):
        await interaction.response.defer()
        if dossier is None:
            view = FolderSelectView(self, interaction.user)
            msg = await safe_send(interaction.channel, "📁 Choisis un dossier :", view=view)
            view.message = msg
            await interaction.delete_original_response()
            return
        await self._start_scan(interaction.channel, interaction.user, dossier, start_page=page)
        await interaction.delete_original_response()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="scans", help="📖 Lire un dossier de scans.")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_scans(self, ctx: commands.Context, dossier: str | None = None, page: int = 1):
        if dossier is None:
            view = FolderSelectView(self, ctx.author)
            msg = await safe_send(ctx.channel, "📁 Choisis un dossier :", view=view)
            view.message = msg
            return
        await self._start_scan(ctx.channel, ctx.author, dossier, start_page=page)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = ScansBleach(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Bleach"
    await bot.add_cog(cog)
