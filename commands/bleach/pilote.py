# ────────────────────────────────────────────────────────────────────────────────
# 📌 pilote.py — Commande interactive /pilote et !pilote
# Objectif : Lire le pilote de Bleach avec pagination et navigation interactive
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
from discord.ui import View, Button
import os

from utils.discord_utils import safe_send, safe_edit, safe_respond, safe_delete  

# ────────────────────────────────────────────────────────────────────────────────
# 📂 Gestion des pages du pilote
# ────────────────────────────────────────────────────────────────────────────────
PILOTE_FOLDER = os.path.join("data", "images", "pilote")

def get_pages():
    """Retourne la liste triée des fichiers images du pilote."""
    try:
        return sorted(os.listdir(PILOTE_FOLDER))
    except Exception as e:
        print(f"[ERREUR PILOTE] Impossible de charger {PILOTE_FOLDER} : {e}")
        return []

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ UI — Pagination avec boutons
# ────────────────────────────────────────────────────────────────────────────────
class PiloteView(View):
    def __init__(self, bot, pages, start_page=1, user=None):
        super().__init__(timeout=120)
        self.bot = bot
        self.pages = pages
        self.current_page = max(1, min(start_page, len(pages)))
        self.message = None
        self.user = user  # seul l’auteur contrôle

    async def update_page(self):
        """Met à jour l’embed avec la page actuelle."""
        file_path = os.path.join(PILOTE_FOLDER, self.pages[self.current_page - 1])
        file = discord.File(file_path, filename=self.pages[self.current_page - 1])

        embed = discord.Embed(
            title=f"Bleach - Pilote (Page {self.current_page}/{len(self.pages)})",
            description="⬅️ Précédent | ➡️ Suivant | ❌ Fermer",
            color=discord.Color.orange()
        )
        embed.set_image(url=f"attachment://{self.pages[self.current_page - 1]}")

        await safe_edit(self.message, embed=embed, attachments=[file], view=self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Seul l’auteur de la commande peut utiliser les boutons."""
        if self.user and interaction.user.id != self.user.id:
            await safe_respond(interaction, "❌ Tu n’es pas autorisé à contrôler cette lecture.", ephemeral=True)
            return False
        return True

    # Boutons
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
class PiloteBleach(commands.Cog):
    """
    Commande /pilote et !pilote — Lire le pilote de Bleach avec pagination
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction interne pour lancer la lecture
    # ────────────────────────────────────────────────────────────────────────────
    async def _start_pilote(self, channel, user, start_page=1):
        pages = get_pages()
        if not pages:
            await safe_send(channel, "❌ Impossible de charger les pages du pilote.")
            return

        view = PiloteView(self.bot, pages, start_page=start_page, user=user)

        file_path = os.path.join(PILOTE_FOLDER, pages[start_page - 1])
        file = discord.File(file_path, filename=pages[start_page - 1])
        embed = discord.Embed(
            title=f"Bleach - Pilote (Page {start_page}/{len(pages)})",
            description="⬅️ Précédent | ➡️ Suivant | ❌ Fermer",
            color=discord.Color.orange()
        )
        embed.set_image(url=f"attachment://{pages[start_page - 1]}")

        view.message = await safe_send(channel, embed=embed, file=file, view=view)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="pilote",
        description="📖 Lire le pilote de Bleach."
    )
    @app_commands.describe(page="Numéro de page pour commencer la lecture (facultatif)")
    @app_commands.checks.cooldown(rate=1, per=5.0, key=lambda i: i.user.id)
    async def slash_pilote(self, interaction: discord.Interaction, page: int = 1):
        await interaction.response.defer()
        await self._start_pilote(interaction.channel, interaction.user, start_page=page)
        await interaction.delete_original_response()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="pilote", help="📖 Lire le pilote de Bleach.")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_pilote(self, ctx: commands.Context, page: int = 1):
        await self._start_pilote(ctx.channel, ctx.author, start_page=page)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = PiloteBleach(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Bleach"
    await bot.add_cog(cog)