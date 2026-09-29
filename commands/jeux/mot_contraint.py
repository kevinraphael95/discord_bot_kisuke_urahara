# ────────────────────────────────────────────────────────────────────────────────
# 📌 mot_contraint.py — Commande interactive /mot_contraint et !mot_contraint
# Objectif : Trouver un mot commençant et se terminant par les lettres imposées (Multi)
# Catégorie : Jeux
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import random
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Modal, TextInput, Button
from spellchecker import SpellChecker
from utils.discord_utils import safe_send, safe_edit

# ────────────────────────────────────────────────────────────────────────────────
# 🌐 Initialisation du SpellChecker français
# ────────────────────────────────────────────────────────────────────────────────
spell = SpellChecker(language='fr')

DICTIONARY_WORDS = [w for w in spell.word_frequency.dictionary.keys() if len(w) >= 2 and w.isalpha()]

def get_random_letter_pair() -> tuple[str, str]:
    """Tire un mot aléatoire existant et extrait sa première et dernière lettre."""
    word = random.choice(DICTIONARY_WORDS)
    return word[0].upper(), word[-1].upper()

def is_valid_word(word: str) -> bool:
    """Vérifie si le mot existe en français"""
    return word.lower() in spell.word_frequency

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ Modal de saisie pour le joueur qui a buzzé
# ────────────────────────────────────────────────────────────────────────────────
class MotModal(Modal):
    def __init__(self, parent_view):
        super().__init__(title="🔔 Proposer un mot")
        self.parent_view = parent_view
        self.word_input = TextInput(
            label="Mot",
            placeholder="Entre ton mot ici...",
            required=True
        )
        self.add_item(self.word_input)

    async def on_submit(self, interaction: discord.Interaction):
        await self.parent_view.check_word(interaction, self.word_input.value.strip())

# ────────────────────────────────────────────────────────────────────────────────
# 🎮 Vue principale Multijoueur + Buzzer
# ────────────────────────────────────────────────────────────────────────────────
class MotContraintMultiView(View):
    def __init__(self, start_letter: str, end_letter: str):
        super().__init__(timeout=120)
        self.start_letter = start_letter
        self.end_letter = end_letter
        self.scores = {}  # {user_id: points}
        self.user_names = {}  # {user_id: display_name}
        self.rounds = 1
        self.max_rounds = 10
        self.attempts_history = []  # Logs des essais de la manche en cours
        self.message = None

    def build_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="🎯 Mots Contraints - Mode Multijoueur",
            description=(
                f"### **Manche {self.rounds} / {self.max_rounds}**\n\n"
                f"# ➡️ `{self.start_letter}` _ _ _ `{self.end_letter}`\n\n"
                f"Trouvez un mot commençant par **`{self.start_letter}`** et se terminant par **`{self.end_letter}`** !"
            ),
            color=discord.Color.blue()
        )

        # Historique des récents essais
        if self.attempts_history:
            history_text = "\n".join(self.attempts_history[-4:])
            embed.add_field(name=f"Essais Récents (Manche {self.rounds}) :", value=history_text, inline=False)
        else:
            embed.add_field(name=f"Essais Récents (Manche {self.rounds}) :", value="_Aucune tentative pour l'instant_", inline=False)

        # Classement des joueurs
        if self.scores:
            sorted_scores = sorted(self.scores.items(), key=lambda x: x[1], reverse=True)
            leaderboard = "\n".join([f"- **{self.user_names[uid]}** : {pts} pt(s)" for uid, pts in sorted_scores])
            embed.add_field(name="🏆 Classement Actuel (Points) :", value=leaderboard, inline=False)
        else:
            embed.add_field(name="🏆 Classement Actuel (Points) :", value="_Aucun point marqué_", inline=False)

        return embed

    @discord.ui.button(label="🔔 BUZZER !", style=discord.ButtonStyle.success)
    async def buzzer_button(self, interaction: discord.Interaction, button: Button):
        # Enregistre le nom d'affichage du joueur
        self.user_names[interaction.user.id] = interaction.user.display_name
        if interaction.user.id not in self.scores:
            self.scores[interaction.user.id] = 0

        # Ouvre la modal uniquement pour la personne qui a buzzé
        await interaction.response.send_modal(MotModal(self))

    async def check_word(self, interaction: discord.Interaction, word: str):
        await interaction.response.defer()

        user_id = interaction.user.id
        user_name = interaction.user.display_name
        word_clean = word.lower()

        # Validation des conditions
        if not word_clean.startswith(self.start_letter.lower()):
            self.attempts_history.append(f"• **{user_name}** a proposé `{word.upper()}` (❌ Incorrect : ne commence pas par `{self.start_letter}`)")
        elif not word_clean.endswith(self.end_letter.lower()):
            self.attempts_history.append(f"• **{user_name}** a proposé `{word.upper()}` (❌ Incorrect : ne se termine pas par `{self.end_letter}`)")
        elif not is_valid_word(word_clean):
            self.attempts_history.append(f"• **{user_name}** a proposé `{word.upper()}` (❌ Non reconnu dans le dictionnaire)")
        else:
            # ✅ Mot valide -> Gain de point et passage à la manche suivante
            self.scores[user_id] += 1
            self.attempts_history.append(f"• **{user_name}** a proposé `{word.upper()}` (✅ Correct ! +1 pt)")

            self.rounds += 1
            if self.rounds > self.max_rounds:
                return await self.end_game()

            # Réinitialisation pour la manche suivante
            self.start_letter, self.end_letter = get_random_letter_pair()
            self.attempts_history.clear()

        await safe_edit(self.message, embed=self.build_embed(), view=self)

    async def end_game(self):
        for child in self.children:
            child.disabled = True

        embed = discord.Embed(
            title="🏁 Fin de la Partie Multijoueur !",
            color=discord.Color.gold()
        )

        if self.scores:
            sorted_scores = sorted(self.scores.items(), key=lambda x: x[1], reverse=True)
            winner_id, top_score = sorted_scores[0]
            winner_name = self.user_names[winner_id]

            embed.description = f"🎉 Victoire de **{winner_name}** avec **{top_score} point(s)** !\n\n"
            leaderboard = "\n".join([f"**{i+1}. {self.user_names[uid]}** — {pts} pt(s)" for i, (uid, pts) in enumerate(sorted_scores)])
            embed.add_field(name="📊 Classement Final :", value=leaderboard, inline=False)
        else:
            embed.description = "La partie est terminée sans aucun point marqué."

        await safe_edit(self.message, embed=embed, view=self)

    async def on_timeout(self):
        if self.message:
            await self.end_game()

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class MotContraint(commands.Cog):
    """
    Commande /mot_contraint et !mot_contraint — Jeu multijoueur avec buzzer
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _start_game(self, channel):
        start, end = get_random_letter_pair()
        view = MotContraintMultiView(start, end)
        embed = view.build_embed()
        view.message = await safe_send(channel, embed=embed, view=view)

    @app_commands.command(name="mot_contraint", description="Jeu multijoueur : buzz et trouve un mot avec les contraintes imposées.")
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_mot_contraint(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self._start_game(interaction.channel)
        await interaction.delete_original_response()

    @commands.command(name="mot_contraint", aliases=["mc"], help="Jeu multijoueur : buzz et trouve un mot avec les contraintes imposées.")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_mot_contraint(self, ctx: commands.Context):
        await self._start_game(ctx.channel)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = MotContraint(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Jeux"
    await bot.add_cog(cog)
