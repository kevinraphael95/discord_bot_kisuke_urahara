# ================================================================================
# 📌 mot_contraint.py — Commande interactive /mot_contraint et !mot_contraint
# Objectif : Trouver un mot qui commence et se termine par les lettres données
# Catégorie : Jeux
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ================================================================================

# ================================================================================
# 📦 Imports nécessaires
# ================================================================================
import asyncio
import random
from typing import Dict, List, Set

import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, Modal, TextInput, View
from spellchecker import SpellChecker

from utils.discord_utils import safe_edit, safe_respond, safe_send

# ================================================================================
# 🌐 Initialisation & Optimisation du SpellChecker
# ================================================================================
spell = SpellChecker(language="fr")
# Pré-chargement des mots dans un set O(1) pour maximiser les performances
VALID_WORDS_SET: Set[str] = set(spell.word_frequency.dictionary.keys())

# ================================================================================
# ⚙️ Pondération des lettres
# ================================================================================
FRENCH_LETTER_WEIGHTS = {
    "A": 9, "B": 3, "C": 5, "D": 4, "E": 12, "F": 2, "G": 2, "H": 2, "I": 7,
    "J": 1, "K": 0.3, "L": 6, "M": 5, "N": 7, "O": 5, "P": 4, "Q": 0.5,
    "R": 7, "S": 6, "T": 7, "U": 6, "V": 2, "W": 0.3, "X": 0.4, "Y": 0.5, "Z": 0.3
}

def weighted_random_letter() -> str:
    letters = list(FRENCH_LETTER_WEIGHTS.keys())
    weights = list(FRENCH_LETTER_WEIGHTS.values())
    return random.choices(letters, weights=weights, k=1)[0]

def is_valid_word(word: str) -> bool:
    """Vérification instantanée O(1) dans le set."""
    return word.lower() in VALID_WORDS_SET

# ================================================================================
# 🎛️ Modal de saisie du mot
# ================================================================================
class MotModal(Modal):
    def __init__(self, parent_view):
        super().__init__(title="📝 Propose un mot")
        self.parent_view = parent_view
        self.word_input = TextInput(
            label="Mot",
            placeholder="Entre ton mot ici",
            required=True
        )
        self.add_item(self.word_input)

    async def on_submit(self, interaction: discord.Interaction):
        await self.parent_view.check_word(interaction, self.word_input.value.strip())

# ================================================================================
# 🚀 Vue d'attente / Lancement Multi ou Solo
# ================================================================================
class StartView(View):
    """Vue initiale permettant de rejoindre la partie et de la lancer."""

    def __init__(self, host: discord.User | discord.Member, is_multi: bool):
        super().__init__(timeout=30.0)
        self.host = host
        self.is_multi = is_multi
        self.players: List[discord.User | discord.Member] = [host]
        self.started = False

        if not self.is_multi:
            # En solo, on masque le bouton "Rejoindre"
            for child in list(self.children):
                if getattr(child, "custom_id", None) == "join_btn":
                    self.remove_item(child)

    @discord.ui.button(
        label="➕ Rejoindre la partie",
        style=discord.ButtonStyle.primary,
        custom_id="join_btn"
    )
    async def join_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id in [p.id for p in self.players]:
            await interaction.response.send_message(
                "❌ Tu es déjà inscrit !", ephemeral=True
            )
            return

        self.players.append(interaction.user)
        await interaction.response.send_message(
            "✅ Tu as rejoint la partie !", ephemeral=True
        )

    @discord.ui.button(
        label="🎮 Lancer la partie", style=discord.ButtonStyle.green
    )
    async def start_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id != self.host.id:
            await interaction.response.send_message(
                "❌ Seul l'hôte de la commande peut lancer !", ephemeral=True
            )
            return

        self.started = True
        for child in self.children:
            child.disabled = True
        button.label = "Partie lancée !"
        button.style = discord.ButtonStyle.secondary
        await interaction.response.edit_message(view=self)
        self.stop()

# ================================================================================
# 🎮 Vue principale du jeu
# ================================================================================
class MotContraintView(View):
    def __init__(
        self,
        start_letter: str,
        end_letter: str,
        players: List[discord.User | discord.Member],
        is_multi: bool
    ):
        super().__init__(timeout=90)
        self.start_letter = start_letter
        self.end_letter = end_letter
        self.players = players
        self.is_multi = is_multi
        self.scores: Dict[int, int] = {p.id: 0 for p in players}
        self.used_words: Set[str] = set()
        self.rounds = 1
        self.max_rounds = 5
        self.message: discord.Message = None

        self.add_item(ProposerButton(self))

    def _get_leaderboard_text(self) -> str:
        if not self.is_multi:
            return f"⭐ Score : **{list(self.scores.values())[0]}**"

        sorted_scores = sorted(self.scores.items(), key=lambda x: x[1], reverse=True)
        lines = []
        for uid, sc in sorted_scores:
            user = next((p for p in self.players if p.id == uid), None)
            name = user.display_name if user else "Joueur"
            lines.append(f"• **{name}** : {sc} pt(s)")
        return "\n".join(lines)

    def build_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="🎯 Mot Contraint",
            description=(
                f"**Manche {self.rounds}/{self.max_rounds}**\n\n"
                f"➡️ Donne un mot qui **commence par** `{self.start_letter}` "
                f"et **se termine par** `{self.end_letter}`.\n\n"
                f"📊 **Tableau des scores :**\n{self._get_leaderboard_text()}"
            ),
            color=discord.Color.orange()
        )
        embed.set_footer(text="⏳ Tu as 90 secondes pour répondre.")
        return embed

    async def check_word(self, interaction: discord.Interaction, word: str):
        allowed_ids = [p.id for p in self.players]
        if interaction.user.id not in allowed_ids:
            return await interaction.response.send_message(
                "❌ Tu ne participes pas à cette partie.", ephemeral=True
            )

        word_clean = word.lower()

        if word_clean in self.used_words:
            return await safe_respond(interaction, f"❌ Le mot `{word}` a déjà été utilisé pendant cette partie.", ephemeral=True)
        if not word_clean.startswith(self.start_letter.lower()):
            return await safe_respond(interaction, f"❌ Le mot ne commence pas par `{self.start_letter}`.", ephemeral=True)
        if not word_clean.endswith(self.end_letter.lower()):
            return await safe_respond(interaction, f"❌ Le mot ne se termine pas par `{self.end_letter}`.", ephemeral=True)
        if not is_valid_word(word_clean):
            return await safe_respond(interaction, f"❌ `{word}` n’est pas reconnu comme un mot français valide.", ephemeral=True)

        self.used_words.add(word_clean)
        self.scores[interaction.user.id] += 1
        self.rounds += 1

        if self.rounds > self.max_rounds:
            for child in self.children:
                child.disabled = True
            
            embed = discord.Embed(
                title="🎯 Mot Contraint",
                description=(
                    f"🏁 **Fin du jeu !**\n\n"
                    f"📊 **Scores finaux :**\n{self._get_leaderboard_text()}"
                ),
                color=discord.Color.green()
            )
            return await safe_edit(self.message, embed=embed, view=self)

        # Nouveau tour
        self.start_letter = weighted_random_letter()
        self.end_letter = weighted_random_letter()
        await safe_edit(self.message, embed=self.build_embed(), view=self)
        await safe_respond(
            interaction,
            f"✅ Bien joué **{interaction.user.display_name}** (`{word}`) ! Manche suivante 🔄",
            ephemeral=False
        )

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        embed = discord.Embed(
            title="🎯 Mot Contraint",
            description=(
                f"⌛ **Temps écoulé !**\n\n"
                f"La partie s'arrête ici.\n\n"
                f"📊 **Scores finaux :**\n{self._get_leaderboard_text()}"
            ),
            color=discord.Color.red()
        )
        await safe_edit(self.message, embed=embed, view=self)

# ================================================================================
# 🎛️ Bouton de proposition
# ================================================================================
class ProposerButton(Button):
    def __init__(self, parent_view: MotContraintView):
        super().__init__(label="Proposer un mot", style=discord.ButtonStyle.primary)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        allowed_ids = [p.id for p in self.parent_view.players]
        if interaction.user.id not in allowed_ids:
            return await interaction.response.send_message(
                "❌ Tu ne participes pas à cette partie.", ephemeral=True
            )
        await interaction.response.send_modal(MotModal(self.parent_view))

# ================================================================================
# 🧠 Cog principal
# ================================================================================
class MotContraint(commands.Cog):
    """
    Commande /mot_contraint et !mot_contraint — Mode Solo ou Multijoueur
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _start_game(
        self,
        channel: discord.abc.Messageable,
        author: discord.User | discord.Member,
        is_multi: bool = False
    ):
        start_view = StartView(author, is_multi)

        mode_str = "Multijoueur" if is_multi else "Solo"
        join_info = "\nLes autres joueurs peuvent cliquer sur **Rejoindre** !" if is_multi else ""

        intro_embed = discord.Embed(
            title="🎯 Mot Contraint",
            description=(
                f"Mode : **{mode_str}**\n"
                f"Hôte : **{author.display_name}**\n\n"
                f"Objectif : Trouve des mots qui commencent et se terminent par les lettres données en 5 manches !{join_info}\n\n"
                f"Clique sur **Lancer la partie** pour démarrer !"
            ),
            color=discord.Color.blurple(),
        )

        msg = await safe_send(channel, embed=intro_embed, view=start_view)
        if msg is None:
            return

        await start_view.wait()

        if not start_view.started:
            timeout_embed = discord.Embed(
                title="🎯 Mot Contraint",
                description="⌛ Temps écoulé. Partie annulée.",
                color=discord.Color.red(),
            )
            for child in start_view.children:
                child.disabled = True
            await safe_edit(msg, embed=timeout_embed, view=start_view)
            return

        # Décompte de 3 secondes
        for count in range(3, 0, -1):
            countdown_embed = discord.Embed(
                title="🎯 Mot Contraint",
                description=f"⏱️ Lancement dans **{count}**...",
                color=discord.Color.blurple(),
            )
            await safe_edit(msg, embed=countdown_embed, view=start_view)
            await asyncio.sleep(1)

        start_letter = weighted_random_letter()
        end_letter = weighted_random_letter()
        
        game_view = MotContraintView(
            start_letter, end_letter, start_view.players, is_multi
        )
        game_view.message = msg

        await safe_edit(msg, embed=game_view.build_embed(), view=game_view)

    # ============================================================================
    # 🔹 Commande SLASH
    # ============================================================================
    @app_commands.command(
        name="mot_contraint",
        description="Jeu : trouve un mot qui commence et finit par les lettres données."
    )
    @app_commands.describe(mode="Choisis le mode de jeu")
    @app_commands.choices(
        mode=[
            app_commands.Choice(name="Solo", value="solo"),
            app_commands.Choice(name="Multijoueur", value="multi"),
        ]
    )
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_mot_contraint(
        self,
        interaction: discord.Interaction,
        mode: app_commands.Choice[str] = None
    ):
        await interaction.response.defer()
        is_multi = (mode.value == "multi") if mode else False
        await self._start_game(interaction.channel, interaction.user, is_multi)
        await interaction.delete_original_response()

    # ============================================================================
    # 🔹 Commandes PREFIX
    # ============================================================================
    @commands.command(name="mot_contraint", aliases=["mc"], help="Jeu en solo")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_mot_contraint(self, ctx: commands.Context):
        await self._start_game(ctx.channel, ctx.author, is_multi=False)

    @commands.command(name="mot_contraint_multi", aliases=["mcm"], help="Jeu en multijoueur")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_mot_contraint_multi(self, ctx: commands.Context):
        await self._start_game(ctx.channel, ctx.author, is_multi=True)

# ================================================================================
# 🔌 Setup du Cog
# ================================================================================
async def setup(bot: commands.Bot):
    cog = MotContraint(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Jeux"
    await bot.add_cog(cog)
