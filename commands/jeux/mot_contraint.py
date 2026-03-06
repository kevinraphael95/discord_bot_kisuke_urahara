# ────────────────────────────────────────────────────────────────────────────────
# 📌 mot_contraint.py — Commande interactive /mot_contraint et !mot_contraint
# Objectif : Trouver un mot qui commence et se termine par les lettres données
# Catégorie : Jeux
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord, random
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Modal, TextInput, Button
from spellchecker import SpellChecker
from utils.discord_utils import safe_send, safe_respond, safe_edit

# ────────────────────────────────────────────────────────────────────────────────
# 🌐 Initialisation du SpellChecker français
# ────────────────────────────────────────────────────────────────────────────────
spell = SpellChecker(language='fr')

# ────────────────────────────────────────────────────────────────────────────────
# ⚙️ Pondération des lettres (moins de chances pour les rares)
# ────────────────────────────────────────────────────────────────────────────────
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
    """Vérifie si le mot existe en français"""
    return word.lower() in spell.word_frequency

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ Modal de saisie du mot
# ────────────────────────────────────────────────────────────────────────────────
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

# ────────────────────────────────────────────────────────────────────────────────
# 🎮 Vue principale du jeu
# ────────────────────────────────────────────────────────────────────────────────
class MotContraintView(View):
    def __init__(self, start_letter: str, end_letter: str, author_id: int):
        super().__init__(timeout=90)
        self.start_letter = start_letter
        self.end_letter = end_letter
        self.author_id = author_id
        self.score = 0
        self.rounds = 1
        self.max_rounds = 5
        self.message = None

        self.add_item(ProposerButton(self))

    def build_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=f"🎯 Mot Contraint — Manche {self.rounds}/{self.max_rounds}",
            description=(
                f"➡️ Donne un mot qui **commence par** `{self.start_letter}` "
                f"et **se termine par** `{self.end_letter}`."
            ),
            color=discord.Color.orange()
        )
        embed.add_field(name="Score actuel", value=f"⭐ {self.score}", inline=False)
        embed.set_footer(text="⏳ Tu as 90 secondes pour répondre.")
        return embed

    async def check_word(self, interaction: discord.Interaction, word: str):
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message("❌ Tu ne participes pas à cette partie.", ephemeral=True)

        word_clean = word.lower()
        if not word_clean.startswith(self.start_letter.lower()):
            return await safe_respond(interaction, f"❌ Le mot ne commence pas par `{self.start_letter}`.", ephemeral=True)
        if not word_clean.endswith(self.end_letter.lower()):
            return await safe_respond(interaction, f"❌ Le mot ne se termine pas par `{self.end_letter}`.", ephemeral=True)
        if not is_valid_word(word_clean):
            return await safe_respond(interaction, f"❌ `{word}` n’est pas reconnu comme un mot français valide.", ephemeral=True)

        self.score += 1
        self.rounds += 1

        if self.rounds > self.max_rounds:
            for child in self.children:
                child.disabled = True
            embed = discord.Embed(
                title="🏁 Fin du jeu !",
                description=f"✅ Score final : **{self.score}/{self.max_rounds}**",
                color=discord.Color.green()
            )
            return await safe_edit(self.message, embed=embed, view=self)

        # Nouveau tour
        self.start_letter = weighted_random_letter()
        self.end_letter = weighted_random_letter()
        await safe_edit(self.message, embed=self.build_embed(), view=self)
        await safe_respond(interaction, "✅ Bien joué ! Nouvelle manche 🔄", ephemeral=True)

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        embed = discord.Embed(
            title="⌛ Temps écoulé !",
            description=f"Le jeu est terminé. Score final : **{self.score}/{self.max_rounds}**",
            color=discord.Color.red()
        )
        await safe_edit(self.message, embed=embed, view=self)

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ Bouton de proposition
# ────────────────────────────────────────────────────────────────────────────────
class ProposerButton(Button):
    def __init__(self, parent_view):
        super().__init__(label="Proposer un mot", style=discord.ButtonStyle.primary)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.parent_view.author_id:
            return await interaction.response.send_message("❌ Tu ne participes pas à cette partie.", ephemeral=True)
        await interaction.response.send_modal(MotModal(self.parent_view))

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class MotContraint(commands.Cog):
    """
    Commande /mot_contraint et !mot_contraint — Trouver un mot qui commence et finit par les lettres données
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _start_game(self, channel, author_id):
        start = weighted_random_letter()
        end = weighted_random_letter()
        view = MotContraintView(start, end, author_id)
        embed = view.build_embed()
        view.message = await safe_send(channel, embed=embed, view=view)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(name="mot_contraint",description="Jeu : trouve un mot qui commence et finit par les lettres données.")
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_mot_contraint(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self._start_game(interaction.channel, interaction.user.id)
        await interaction.delete_original_response()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="mot_contraint", aliases=["mc"], help="Jeu : trouve un mot qui commence et finit par des lettres données.")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_mot_contraint(self, ctx: commands.Context):
        await self._start_game(ctx.channel, ctx.author.id)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = MotContraint(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Jeux"
    await bot.add_cog(cog)
