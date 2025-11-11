# ────────────────────────────────────────────────────────────────────────────────
# 📌 emoji_command.py — Commande interactive !emoji / !e et /emoji
# Objectif : Afficher un ou plusieurs emojis du serveur via une commande
# Catégorie : Général
# Accès : Public
# Cooldown : 1 utilisation / 3 sec / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button
import random
import re
from utils.discord_utils import safe_send, safe_respond  

# ────────────────────────────────────────────────────────────────────────────────
# 🎮 View pour la pagination
# ────────────────────────────────────────────────────────────────────────────────
class EmojiPaginator(View):
    """View interactive pour naviguer entre plusieurs pages d'emojis."""

    def __init__(self, pages: list[discord.Embed], timeout: int = 90):
        super().__init__(timeout=timeout)
        self.pages = pages
        self.index = 0  # page actuelle

    async def update(self, interaction: discord.Interaction):
        """Met à jour l’embed affiché avec la page courante."""
        await interaction.response.edit_message(embed=self.pages[self.index], view=self)

    @discord.ui.button(label="⬅️", style=discord.ButtonStyle.secondary)
    async def previous(self, interaction: discord.Interaction, button: Button):
        """Bouton pour aller à la page précédente."""
        self.index = (self.index - 1) % len(self.pages)
        await self.update(interaction)

    @discord.ui.button(label="➡️", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, button: Button):
        """Bouton pour aller à la page suivante."""
        self.index = (self.index + 1) % len(self.pages)
        await self.update(interaction)

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal avec centralisation des erreurs et cooldowns
# ────────────────────────────────────────────────────────────────────────────────
class EmojiCommand(commands.Cog):
    """Commande !emoji / !e et /emoji — Affiche un ou plusieurs emojis du serveur."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonctions internes
    # ────────────────────────────────────────────────────────────────────────────
    def _parse_emoji_input(self, raw_input: tuple[str]) -> list[str]:
        """Transforme un texte comme ':woah::woah:' en ['woah','woah']."""
        joined = "".join(raw_input)
        return re.findall(r":([a-zA-Z0-9_]+):", joined)

    def _find_emojis(self, emoji_inputs: list[str], current_guild: discord.Guild):
        """
        Cherche les emojis demandés :
        - Priorité au serveur actuel
        - Sinon recherche sur les autres serveurs
        """
        found, not_found = [], []
        for name in emoji_inputs:
            name_lower = name.lower()

            # Cherche dans le serveur actuel
            match = discord.utils.find(lambda e: e.name.lower() == name_lower and e.available, current_guild.emojis)

            # Cherche dans les autres serveurs si non trouvé
            if not match:
                other_guilds = [g for g in self.bot.guilds if g.id != current_guild.id]
                for g in random.sample(other_guilds, len(other_guilds)):
                    match = discord.utils.find(lambda e: e.name.lower() == name_lower and e.available, g.emojis)
                    if match:
                        break

            if match:
                found.append(str(match))
            else:
                not_found.append(f":{name}:")
        return found, not_found

    def _build_pages(self, guilds: list[discord.Guild]) -> list[discord.Embed]:
        """
        Construit les pages d'emojis par serveur :
        - Chaque serveur : animés d'abord, puis non animés
        - 40 emojis max par page
        """
        pages = []

        for g in guilds:
            animated = [str(e) for e in g.emojis if e.animated and e.available]
            static = [str(e) for e in g.emojis if not e.animated and e.available]

            def create_pages(emojis_list, title_suffix, color):
                chunks = [emojis_list[i:i+40] for i in range(0, len(emojis_list), 40)]
                for i, chunk in enumerate(chunks, start=1):
                    embed = discord.Embed(
                        title=f"🎭 Emojis {title_suffix} — {g.name}",
                        description=" ".join(chunk),
                        color=color
                    )
                    if len(chunks) > 1:
                        embed.set_footer(text=f"Page {i}/{len(chunks)} pour {g.name}")
                    pages.append(embed)

            if animated:
                create_pages(animated, "animés", discord.Color.orange())
            if static:
                create_pages(static, "non animés", discord.Color.blue())

        return pages

    async def _send_emojis_safe(self, channel, guild, emoji_names: tuple[str]):
        """
        Fonction interne centralisée :
        - Envoie les emojis demandés ou tous les emojis paginés par serveur
        - Gère les erreurs
        """
        try:
            if emoji_names:
                emoji_inputs = self._parse_emoji_input(emoji_names)
                found, not_found = self._find_emojis(emoji_inputs, guild)
                if found:
                    await safe_send(channel, " ".join(found))
                if not_found:
                    await safe_send(channel, f"❌ Emojis introuvables : {', '.join(not_found)}")
            else:
                guilds = [guild] + [g for g in self.bot.guilds if g.id != guild.id]
                pages = self._build_pages(guilds)
                if not pages:
                    await safe_send(channel, "❌ Aucun emoji trouvé sur les serveurs.")
                    return
                view = EmojiPaginator(pages)
                await safe_send(channel, embed=pages[0], view=view)
        except Exception as e:
            print(f"[ERREUR affichage emojis] {e}")
            await safe_send(channel, "❌ Une erreur est survenue lors de l'affichage des emojis.")

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(
        name="emoji",
        aliases=["e"],
        help="Montre un ou plusieurs emojis du serveur ou de tous les serveurs.",
        description="Affiche les emojis demandés ou tous les emojis du serveur (animés puis non animés) si aucun argument."
    )
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.user)
    async def prefix_emoji(self, ctx: commands.Context, *emoji_names):
        """Commande préfixe qui affiche les emojis du serveur."""
        if ctx.message:
            try:
                await ctx.message.delete()
            except (discord.Forbidden, discord.HTTPException):
                pass
        await self._send_emojis_safe(ctx.channel, ctx.guild, emoji_names)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="emoji",
        description="Montre un ou plusieurs emojis du serveur ou de tous les serveurs."
    )
    @app_commands.describe(emojis="Noms des emojis à afficher, séparés par des espaces ou répétés (ex: :woah::woah:)")
    @app_commands.checks.cooldown(1, 3.0, key=lambda i: i.user.id)
    async def slash_emoji(self, interaction: discord.Interaction, *, emojis: str = ""):
        """Commande slash qui affiche les emojis du serveur ou de tous les serveurs."""
        await interaction.response.defer()
        emoji_inputs = self._parse_emoji_input((emojis,))
        await self._send_emojis_safe(interaction.channel, interaction.guild, emoji_inputs)
        try:
            await interaction.delete_original_response()
        except Exception:
            pass

    @slash_emoji.autocomplete("emojis")
    async def autocomplete_emojis(self, interaction: discord.Interaction, current: str):
        """Propose les noms d'emojis disponibles pour l'autocomplétion."""
        suggestions = [e.name for e in interaction.guild.emojis if e.available]
        return [app_commands.Choice(name=s, value=s) for s in suggestions if current.lower() in s.lower()][:25]

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = EmojiCommand(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Général"
    await bot.add_cog(cog)
