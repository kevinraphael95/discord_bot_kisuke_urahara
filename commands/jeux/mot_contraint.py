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
import random
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Modal, TextInput, Button
from spellchecker import SpellChecker
from utils.discord_utils import safe_send, safe_respond, safe_edit

# ────────────────────────────────────────────────────────────────────────────────
# 🌐 Initialisation du SpellChecker français
# ────────────────────────────────────────────────────────────────────────────────
spell = SpellChecker(language='fr')

# Extraction des mots du dictionnaire ayant au moins 2 lettres
DICTIONARY_WORDS = [w for w in spell.word_frequency.dictionary.keys() if len(w) >= 2 and w.isalpha()]

def get_random_letter_pair() -> tuple[str, str]:
    """Tire un mot aléatoire existant et extrait sa première et dernière lettre."""
    word = random.choice(DICTIONARY_WORDS)
    return word[0].upper(), word[-1].upper()

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
# 🔘 Vue initiale avec le bouton de lancement
# ────────────────────────────────────────────────────────────────────────────────
class StartGameView(View):
    def __init__(self, author_id: int):
        super().__init__(timeout=60)
        self.author_id = author_id

    @discord.ui.button(label="🎮 Lancer la partie", style=discord.ButtonStyle.success)
    async def start_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.author_id:
            return await safe_respond(interaction, "❌ Tu ne peux pas démarrer la partie d'un autre joueur.", ephemeral=True)

        start, end = get_random_letter_pair()
        game_view = MotContraintView(start, end, self.author_id)
        embed = game_view.build_embed()

        # Remplacement du message initial par le jeu actif
        await interaction.response.edit_message(embed=embed, view=game_view)
        game_view.message = interaction.message

# ────────────────────────────────────────────────────────────────────────────────
# 🎮 Vue principale du jeu actif
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
        return embed

    async def check_word(self, interaction: discord.Interaction, word: str):
        if interaction.user.id != self.author_id:
            return await safe_respond(interaction, "❌ Tu ne participes pas à cette partie.", ephemeral=True)

        # ✅ On acquitte l'interaction immédiatement pour éviter le spam de messages
        # L'embed sera mis à jour via safe_edit ensuite.
        await interaction.response.defer()

        word_clean = word.lower()
        if not word_clean.startswith(self.start_letter.lower()):
            # Comme on a defer(), on doit utiliser followup ou safe_send si on veut alerter l'utilisateur,
            # mais ici on va simplement safe_edit l'embed pour remettre l'ancien tour si échec,
            # OU mieux, on ne fait rien et on attend la prochaine modal pour ne pas casser le flow.
            # Pour simplifier et éviter le spam de DM/Messages, on va safe_edit le même embed pour "refresh"
            return await safe_edit(self.message, embed=self.build_embed(), view=self)

        if not word_clean.endswith(self.end_letter.lower()):
            return await safe_edit(self.message, embed=self.build_embed(), view=self)

        if not is_valid_word(word_clean):
            return await safe_edit(self.message, embed=self.build_embed(), view=self)

        # 🔥 Le mot est valide : On incrémente
        self.score += 1
        self.rounds += 1

        # Vérification fin de partie
        if self.rounds > self.max_rounds:
            for child in self.children:
                child.disabled = True
            embed = discord.Embed(
                title="🏁 Fin du jeu !",
                description=f"✅ Score final : **{self.score}/{self.max_rounds}**",
                color=discord.Color.green()
            )
            return await safe_edit(self.message, embed=embed, view=self)

        # Nouveau tour : On met à jour l'embed existant SANS message de confirmation
        self.start_letter, self.end_letter = get_random_letter_pair()
        await safe_edit(self.message, embed=self.build_embed(), view=self)

    async def on_timeout(self):
        # En cas de timeout, Discord n'envoie pas d'interaction, on doit safe_edit le message stocké
        if not self.message:
            return

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
            return await safe_respond(interaction, "❌ Tu ne participes pas à cette partie.", ephemeral=True)
        # Discord gère l'acquittement de la modal automatiquement
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
        embed = discord.Embed(
            title="🎯 Mot Contraint",
            description="Appuie sur le bouton ci-dessous pour démarrer la partie (5 manches).",
            color=discord.Color.blurple()
        )
        view = StartGameView(author_id)
        # safe_send retourne le message envoyé, utile pour le timeout plus tard
        await safe_send(channel, embed=embed, view=view)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(name="mot_contraint", description="Jeu : trouve un mot qui commence et finit par les lettres données.")
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_mot_contraint(self, interaction: discord.Interaction):
        # On defer pour avoir le temps de safe_send
        await interaction.response.defer()
        await self._start_game(interaction.channel, interaction.user.id)
        # safe_send a déjà envoyé le message de Start, on supprime le "Le bot réfléchit"
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
