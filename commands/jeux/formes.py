# ================================================================================
# 📌 memory_formes.py — Commande Memory : retenir et choisir les formes
# Objectif : Jouer à un mini jeu mémoire avec une gridview de boutons
# Modes : Solo (1 joueur) et Multi (Buzzer pour prendre la main)
# Catégorie : Jeux
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ================================================================================

# ================================================================================
# 📦 Imports nécessaires
# ================================================================================
import asyncio
import logging
import random

import discord
from discord import app_commands
from discord.ext import commands

from utils.discord_utils import safe_send, safe_edit
from utils.jeux_utils import parse_mode

log = logging.getLogger(__name__)

# ================================================================================
# 🧠 Cog principal
# ================================================================================
class MemoryFormes(commands.Cog):
    """Commande /formes et !formes — Jouez au mini-jeu mémoire"""

    FORMS = ["❤️", "💙", "🤍", "🟥", "🟦", "⬜", "🔴", "🔵", "⚪"]

    # Disposition : 3 boutons par ligne
    LAYOUT = [
        ["❤️", "💙", "🤍"],
        ["🟥", "🟦", "⬜"],
        ["🔴", "🔵", "⚪"],
    ]

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ============================================================================
    # 🔹 Commande SLASH
    # ============================================================================
    @app_commands.command(
        name="formes",
        description="Jouez au mini-jeu mémoire avec des formes et couleurs."
    )
    @app_commands.describe(mode="Tapez 'm' ou 'multi' pour le mode multijoueur")
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_memory_formes(self, interaction: discord.Interaction, mode: str = None):
        multi = parse_mode(mode)
        await self.start_game(interaction, multi=multi)

    # ============================================================================
    # 🔹 Commande PREFIX
    # ============================================================================
    @commands.command(name="formes", help="Jouez au mini-jeu mémoire avec des formes et couleurs.")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_memory_formes(self, ctx: commands.Context, *, arg: str = None):
        multi = parse_mode(arg)
        await self.start_game(ctx, multi=multi)

    # ============================================================================
    # 🔹 Fonction principale du jeu
    # ============================================================================
    async def start_game(self, ctx_or_interaction, multi: bool = False):
        is_interaction = isinstance(ctx_or_interaction, discord.Interaction)
        user = ctx_or_interaction.user if is_interaction else ctx_or_interaction.author
        channel = ctx_or_interaction.channel

        sequence = random.sample(self.FORMS, random.randint(4, 6))
        sequence_str = " ".join(sequence)
        mode_text = "Multijoueur 🌍" if multi else "Solo 🧍‍♂️"

        embed = discord.Embed(
            title=f"🧠 Test de Mémoire - Mode {mode_text}",
            description=f"Retenez bien cette suite !\n\n# {sequence_str}\n\nDisparition dans **5**s...",
            color=discord.Color.blurple()
        )
        embed.set_footer(text=f"Partie lancée par : {user.display_name}")

        if is_interaction:
            await ctx_or_interaction.response.send_message(embed=embed)
            msg = await ctx_or_interaction.original_response()
        else:
            msg = await channel.send(embed=embed)

        # Compte à rebours de 5 secondes
        for i in range(4, 0, -1):
            await asyncio.sleep(1)
            embed.description = f"Retenez bien cette suite !\n\n# {sequence_str}\n\nDisparition dans **{i}**s..."
            try:
                await safe_edit(msg, embed=embed)
            except discord.NotFound:
                return

        await asyncio.sleep(1)

        # Création de la Vue selon le mode
        if multi:
            view = MemoryMultiView(sequence, self.LAYOUT, user.id, msg)
        else:
            view = MemorySoloView(sequence, self.LAYOUT, user.id, user.display_name, msg)

        game_embed = view.build_embed()

        try:
            await safe_edit(msg, embed=game_embed, view=view)
        except discord.NotFound:
            msg = await safe_send(channel, embed=game_embed, view=view)
            view.game_message = msg


# ================================================================================
# 🔹 View MODE SOLO
# ================================================================================
class MemorySoloView(discord.ui.View):
    def __init__(self, sequence: list[str], layout: list[list[str]], user_id: int, user_name: str, message: discord.Message = None):
        super().__init__(timeout=60)
        self.sequence = sequence
        self.user_id = user_id
        self.user_name = user_name
        self.user_sequence: list[str] = []
        self.game_message = message

        for row_idx, row_symbols in enumerate(layout):
            for symbol in row_symbols:
                self.add_item(MemoryButton(symbol, row=row_idx))

        self.add_item(DeleteLastButton(row=len(layout)))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.defer()
            return False
        return True

    def build_embed(self) -> discord.Embed:
        progress_bar = " ".join(self.user_sequence + ["⬛"] * (len(self.sequence) - len(self.user_sequence)))

        embed = discord.Embed(
            title="🧠 Test de Mémoire - Mode Solo 🧍‍♂️",
            description=(
                f"Clique sur les formes **dans le bon ordre**.\n\n"
                f"**Progression :**\n{progress_bar}\n\n"
                f"**{len(self.user_sequence)} / {len(self.sequence)}**"
            ),
            color=discord.Color.orange()
        )
        embed.set_footer(text=f"Joueur : {self.user_name}")
        return embed

    async def refresh(self, interaction: discord.Interaction):
        finished = len(self.user_sequence) >= len(self.sequence)

        if finished:
            for item in self.children:
                if isinstance(item, discord.ui.Button):
                    item.disabled = True

            correct = (self.user_sequence == self.sequence)
            given = " ".join(self.user_sequence)
            good = " ".join(self.sequence)

            if correct:
                embed = discord.Embed(
                    title="🧠 Test de Mémoire - Mode Solo 🧍‍♂️ — Gagné !",
                    description=f"🎉 **Bravo {self.user_name} !** Tu as reproduit la bonne suite !\n\n✅ **Suite :** {good}",
                    color=discord.Color.green()
                )
            else:
                embed = discord.Embed(
                    title="🧠 Test de Mémoire - Mode Solo 🧍‍♂️ — Terminé",
                    description=f"❌ **Raté !**\n\n**Ta réponse :** {given}\n**Bonne suite :** {good}",
                    color=discord.Color.red()
                )
            embed.set_footer(text="Partie terminée")
            self.stop()
        else:
            embed = self.build_embed()

        try:
            await safe_edit(interaction.message, embed=embed, view=self)
        except discord.NotFound:
            pass

    async def on_timeout(self):
        if self.game_message:
            for item in self.children:
                if isinstance(item, discord.ui.Button):
                    item.disabled = True

            good = " ".join(self.sequence)
            embed = discord.Embed(
                title="⏰ Temps écoulé !",
                description=f"**La bonne suite était :** {good}",
                color=discord.Color.dark_gray()
            )
            embed.set_footer(text="Partie terminée")
            try:
                await safe_edit(self.game_message, embed=embed, view=self)
            except discord.NotFound:
                pass


# ================================================================================
# 🔹 View MODE MULTI (avec Buzzer)
# ================================================================================
class MemoryMultiView(discord.ui.View):
    def __init__(self, sequence: list[str], layout: list[list[str]], author_id: int, message: discord.Message = None):
        super().__init__(timeout=120)
        self.sequence = sequence
        self.layout = layout
        self.author_id = author_id
        self.game_message = message

        self.current_player: discord.User | discord.Member | None = None
        self.user_sequence: list[str] = []
        self.attempts: list[str] = []  # Historique des erreurs

        # Bouton Buzzer initial
        self.add_item(BuzzerFormesButton())

    def build_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="🧠 Test de Mémoire - Mode Multijoueur 🌍",
            color=discord.Color.blurple()
        )

        if self.current_player:
            progress_bar = " ".join(self.user_sequence + ["⬛"] * (len(self.sequence) - len(self.user_sequence)))
            embed.description = (
                f"🎯 **{self.current_player.mention} a la main !**\n"
                f"Clique sur les formes dans le bon ordre.\n\n"
                f"**Progression :**\n{progress_bar}\n\n"
                f"**{len(self.user_sequence)} / {len(self.sequence)}**"
            )
            embed.color = discord.Color.orange()
        else:
            embed.description = "Clique sur **🔔 Buzzer** pour prendre la main et proposer ta réponse !"

        if self.attempts:
            embed.add_field(name="Essais manqués", value="\n".join(self.attempts), inline=False)

        return embed

    async def buzz(self, interaction: discord.Interaction):
        """Déclenché lorsqu'un joueur buzze."""
        self.current_player = interaction.user
        self.user_sequence = []

        # Remplacement des boutons : grille de formes + bouton supprimer
        self.clear_items()
        for row_idx, row_symbols in enumerate(self.layout):
            for symbol in row_symbols:
                self.add_item(MemoryButton(symbol, row=row_idx))
        self.add_item(DeleteLastButton(row=len(self.layout)))

        await interaction.response.defer()
        await safe_edit(interaction.message, embed=self.build_embed(), view=self)

    async def refresh(self, interaction: discord.Interaction):
        """Vérifie la progression du joueur qui a la main."""
        if interaction.user.id != self.current_player.id:
            await interaction.response.defer()
            return

        finished = len(self.user_sequence) >= len(self.sequence)

        if finished:
            correct = (self.user_sequence == self.sequence)
            good = " ".join(self.sequence)

            if correct:
                for item in self.children:
                    if isinstance(item, discord.ui.Button):
                        item.disabled = True

                embed = discord.Embed(
                    title="🧠 Test de Mémoire - Mode Multijoueur 🌍 — Gagné !",
                    description=f"🏆 **{self.current_player.mention}** a trouvé la bonne suite !\n\n✅ **Suite :** {good}",
                    color=discord.Color.green()
                )
                embed.set_footer(text="Partie terminée")
                self.stop()
                await safe_edit(interaction.message, embed=embed, view=self)
            else:
                # Mauvaise réponse : retour au buzzer pour les autres
                given = " ".join(self.user_sequence)
                self.attempts.append(f"❌ {self.current_player.display_name} : {given}")

                self.current_player = None
                self.user_sequence = []

                self.clear_items()
                self.add_item(BuzzerFormesButton())

                await safe_edit(interaction.message, embed=self.build_embed(), view=self)
        else:
            await safe_edit(interaction.message, embed=self.build_embed(), view=self)

    async def on_timeout(self):
        if self.game_message:
            for item in self.children:
                if isinstance(item, discord.ui.Button):
                    item.disabled = True

            good = " ".join(self.sequence)
            embed = discord.Embed(
                title="⏰ Temps écoulé !",
                description=f"**La bonne suite était :** {good}",
                color=discord.Color.dark_gray()
            )
            embed.set_footer(text="Partie terminée")
            try:
                await safe_edit(self.game_message, embed=embed, view=self)
            except discord.NotFound:
                pass


# ================================================================================
# 🔹 Composants UI (Boutons)
# ================================================================================
class BuzzerFormesButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="🔔 Buzzer", style=discord.ButtonStyle.success)

    async def callback(self, interaction: discord.Interaction):
        view: MemoryMultiView = self.view
        await view.buzz(interaction)


class MemoryButton(discord.ui.Button):
    def __init__(self, symbol: str, row: int = 0):
        super().__init__(label=symbol, style=discord.ButtonStyle.secondary, row=row)
        self.symbol = symbol

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if isinstance(view, MemorySoloView):
            if len(view.user_sequence) < len(view.sequence):
                view.user_sequence.append(self.symbol)
            await interaction.response.defer()
            await view.refresh(interaction)
        elif isinstance(view, MemoryMultiView):
            if view.current_player and interaction.user.id == view.current_player.id:
                if len(view.user_sequence) < len(view.sequence):
                    view.user_sequence.append(self.symbol)
            await interaction.response.defer()
            await view.refresh(interaction)


class DeleteLastButton(discord.ui.Button):
    def __init__(self, row: int = 4):
        super().__init__(label="⬅️ Supprimer", style=discord.ButtonStyle.danger, row=row)

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if isinstance(view, MemorySoloView):
            if view.user_sequence:
                view.user_sequence.pop()
            await interaction.response.defer()
            await view.refresh(interaction)
        elif isinstance(view, MemoryMultiView):
            if view.current_player and interaction.user.id == view.current_player.id:
                if view.user_sequence:
                    view.user_sequence.pop()
            await interaction.response.defer()
            await view.refresh(interaction)


# ================================================================================
# 🔌 Setup du Cog
# ================================================================================
async def setup(bot: commands.Bot):
    cog = MemoryFormes(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Jeux"
    await bot.add_cog(cog)
