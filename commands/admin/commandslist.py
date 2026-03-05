# ────────────────────────────────────────────────────────────────────────────────
# 📌 commandslist.py — Commande /commandslist et !commandslist
# Objectif : Génère un README.md avec toutes les commandes triées et formatées
# Catégorie : Admin
# Accès : Administrateurs seulement
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import io

import discord
from discord import app_commands
from discord.ext import commands

from utils.discord_utils import safe_send, safe_respond

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────

class CommandsList(commands.Cog):
    """
    Commande /commandslist et !commandslist — Génère un README.md complet avec toutes les commandes.
    Accessible uniquement aux administrateurs.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction interne commune
    # ────────────────────────────────────────────────────────────────────────────
    def _build_markdown_content(self) -> str:
        """Renvoie le contenu Markdown complet pour README.md avec format compact et lisible."""
        content = "Liste des Commandes\n\n"

        categories = {}
        for cmd in self.bot.commands:
            cat = getattr(cmd, "category", "Autre")
            desc = cmd.help if cmd.help else "Pas de description."
            categories.setdefault(cat, []).append((cmd.name, desc))

        for cat in sorted(categories.keys(), key=lambda c: c.lower()):
            content += f"### 📂 {cat}\n"
            for name, desc in sorted(categories[cat], key=lambda x: x[0].lower()):
                content += f"- **{name} :** {desc}\n"
            content += "\n"

        return content

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="commandslist",
        description="Génère un .md avec toutes les commandes et les envoie en fichier."
    )
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.checks.cooldown(rate=1, per=5.0, key=lambda i: i.user.id)
    async def slash_commandslist(self, interaction: discord.Interaction):
        file = discord.File(io.StringIO(self._build_markdown_content()), filename="Liste des Commandes.md")
        await safe_respond(interaction, "📄 Voici la liste des commandes :", file=file)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(
        name="commandslist",
        help="Génère un .md avec toutes les commandes et les envoie en fichier."
    )
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_commandslist(self, ctx: commands.Context):
        file = discord.File(io.StringIO(self._build_markdown_content()), filename="Liste des Commandes.md")
        await safe_send(ctx.channel, "📄 Voici la liste des commandes :", file=file)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = CommandsList(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Admin"
    await bot.add_cog(cog)
