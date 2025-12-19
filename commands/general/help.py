# ────────────────────────────────────────────────────────────────────────────────
# 📌 help.py — Commande interactive !help
# Objectif : Afficher dynamiquement l’aide des commandes avec pagination
# Catégorie : Général
# Accès : Public
# Cooldown : 1 utilisation / 5 sec / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands
import math
from bot import get_prefix
from utils.discord_utils import safe_send, safe_edit, safe_respond

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ UI — Pagination des commandes
# ────────────────────────────────────────────────────────────────────────────────
class HelpPaginatorView(discord.ui.View):
    """Permet de naviguer entre les pages d'une catégorie de commandes."""
    def __init__(self, bot, category: str, commands_list: list, prefix: str):
        super().__init__(timeout=None)
        self.bot = bot
        self.category = category
        self.commands = commands_list
        self.prefix = prefix
        self.page = 0
        self.per_page = 10
        self.total_pages = max(1, math.ceil(len(self.commands) / self.per_page))

        # Ajout des boutons de navigation si plusieurs pages
        if self.total_pages > 1:
            self.add_item(PrevButton(self))
            self.add_item(NextButton(self))

    def create_embed(self) -> discord.Embed:
        """Crée un embed pour la page courante."""
        embed = discord.Embed(
            title=f"📂 {self.category} — Page {self.page + 1}/{self.total_pages}",
            color=discord.Color.blurple()
        )
        start, end = self.page * self.per_page, (self.page + 1) * self.per_page
        for cmd in self.commands[start:end]:
            embed.add_field(name=f"`{self.prefix}{cmd.name}`", value=cmd.help or "Pas de description.", inline=False)
        embed.set_footer(text=f"Utilise {self.prefix}help <commande> pour plus de détails.")
        return embed

class PrevButton(discord.ui.Button):
    """Bouton pour aller à la page précédente d'une catégorie."""
    def __init__(self, paginator: HelpPaginatorView):
        super().__init__(label="◀️", style=discord.ButtonStyle.primary)
        self.paginator = paginator

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        if self.paginator.page > 0:
            self.paginator.page -= 1
            await safe_edit(interaction.message, embed=self.paginator.create_embed(), view=self.paginator)

class NextButton(discord.ui.Button):
    """Bouton pour aller à la page suivante d'une catégorie."""
    def __init__(self, paginator: HelpPaginatorView):
        super().__init__(label="▶️", style=discord.ButtonStyle.primary)
        self.paginator = paginator

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        if self.paginator.page < self.paginator.total_pages - 1:
            self.paginator.page += 1
            await safe_edit(interaction.message, embed=self.paginator.create_embed(), view=self.paginator)

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal avec gestion centralisée des erreurs et cooldown
# ────────────────────────────────────────────────────────────────────────────────
class HelpCommand(commands.Cog):
    """Commande !help — Affiche les commandes par catégorie avec pagination."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="help", aliases=["h"], help="Affiche la liste des commandes ou une commande spécifique.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def help_func(self, ctx: commands.Context, commande: str = None):
        """Affiche l'aide soit pour une commande spécifique, soit la liste paginée complète."""
        prefix = get_prefix(self.bot, ctx.message)

        # 🔍 Aide pour commande spécifique
        if commande:
            cmd = self.bot.get_command(commande)
            if not cmd:
                return await safe_send(ctx.channel, f"❌ La commande `{commande}` n'existe pas.")

            embed = discord.Embed(
                title=f"ℹ️ Aide pour `{prefix}{cmd.name}`",
                color=discord.Color.green()
            )
            embed.add_field(name="📄 Description", value=cmd.help or "Pas de description.", inline=False)
            if cmd.aliases:
                embed.add_field(name="🔁 Alias", value=", ".join(f"`{a}`" for a in cmd.aliases), inline=False)
            embed.set_footer(text="📌 Syntaxe : <obligatoire> [optionnel]")
            return await safe_send(ctx.channel, embed=embed)

        # 📜 Liste des commandes par catégorie
        categories = {}
        for cmd in self.bot.commands:
            if cmd.hidden:
                continue
            cat = getattr(cmd, "category", "Autres")
            categories.setdefault(cat, []).append(cmd)

        # Crée un embed par catégorie et envoie la première page
        for cat, cmds in categories.items():
            paginator = HelpPaginatorView(self.bot, cat, sorted(cmds, key=lambda c: c.name), prefix)
            await safe_send(ctx.channel, f"📂 Catégorie : **{cat}**", embed=paginator.create_embed(), view=paginator)

    def cog_load(self):
        """Assigne la catégorie Général à la commande au chargement du cog."""
        self.help_func.category = "Général"

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = HelpCommand(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Général"
    await bot.add_cog(cog)
