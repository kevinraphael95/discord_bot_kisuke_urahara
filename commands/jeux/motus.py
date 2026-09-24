# ================================================================================
# 📌 motus.py — Commande interactive /motus et !motus
# Objectif : Jeu du Motus avec embed, tentatives limitées et feedback coloré
# Catégorie : Jeux
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ================================================================================

# ================================================================================
# 📦 Imports nécessaires
# ================================================================================
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Modal, TextInput, Button
import random
import aiohttp
import unicodedata
from spellchecker import SpellChecker
from utils.discord_utils import safe_send, safe_edit, safe_respond

# ================================================================================
# 🌐 Initialisation du spellchecker français
# ================================================================================
spell = SpellChecker(language='fr')

# ================================================================================
# 🌐 Fonction pour récupérer un mot français aléatoire
# ================================================================================
async def get_random_french_word(length: int | None = None) -> str:
    """Récupère un mot français aléatoire depuis l'API trouve-mot.fr"""
    url = "https://trouve-mot.fr/api/random"
    if length:
        url += f"?size={length}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if isinstance(data, list) and len(data) > 0:
                        return data[0]["name"].upper()
    except Exception as e:
        print(f"[ERREUR API Motus] {e}")
    return "PYTHON"

# ================================================================================
# 🌐 Fonction pour vérifier qu’un mot existe via SpellChecker
# ================================================================================
def is_valid_word(word: str) -> bool:
    """Retourne True si le mot est reconnu par SpellChecker"""
    return word.lower() in spell.word_frequency

# ================================================================================
# 🎛️ Modal pour proposer un mot
# ================================================================================
class MotusModal(Modal):
    def __init__(self, parent_view):
        super().__init__(title="Propose un mot")
        self.parent_view = parent_view
        self.word_input = TextInput(
            label="Mot",
            placeholder=f"Mot de {self.parent_view.display_length} lettres",
            required=True,
            max_length=self.parent_view.display_length,
            min_length=self.parent_view.display_length
        )
        self.add_item(self.word_input)

    async def on_submit(self, interaction: discord.Interaction):
        guess = self.word_input.value.strip().upper()
        await self.parent_view.process_guess(interaction, guess)

# ================================================================================
# 🎛️ Vue principale avec boutons (Proposer + Indice)
# ================================================================================
class MotusView(View):
    def __init__(self, target_word: str, max_attempts: int | None = None, author_id: int | None = None):
        super().__init__(timeout=180)

        # 🔤 Normalisation du mot (œ → oe) et retrait des tirets
        normalized = target_word.replace("Œ", "OE").replace("œ", "oe")
        self.target_word = normalized.upper()
        self.display_word = self.target_word  # Pour affichage avec tirets
        self.display_length = len([c for c in self.target_word if c.isalpha()])  # Longueur sans tirets

        # 🔢 Au moins 5 essais même pour les mots courts
        base_attempts = max(self.display_length, 5)
        self.max_attempts = max_attempts if max_attempts else base_attempts

        self.attempts: list[dict] = []  # {'word': str, 'hint': bool}
        self.message = None
        self.finished = False
        self.author_id = author_id
        self.hinted_indices: set[int] = set()

        # Boutons
        self.add_item(MotusButton(self))
        self.hint_button = HintButton(self)
        self.add_item(self.hint_button)

    # ============= Helper pour enlever accents =============
    def remove_accents(self, text: str) -> str:
        return ''.join(
            c for c in unicodedata.normalize('NFD', text)
            if unicodedata.category(c) != 'Mn'
        ).upper()

    # ============= Feedback visuel =============
    def create_feedback_line(self, entry: dict) -> str:
        word = entry['word']
        is_hint = entry.get('hint', False)

        def letter_to_flag(c: str) -> str:
            if c == "-":
                return "-"  # conserve les tirets sans les compter
            c_clean = self.remove_accents(c)
            if c_clean.isalpha() and len(c_clean) == 1:
                return chr(0x1F1E6 + (ord(c_clean) - ord('A')))
            return "🟦"

        letters = " ".join(letter_to_flag(c) for c in word)

        if is_hint:
            colors = ["🟦"] * len(word)
            for i, c in enumerate(word):
                if c != "_":
                    colors[i] = "🟩"
        else:
            colors = self.evaluate_guess(word)

        return f"{letters}\n{' '.join(colors)}"

    # ============= Vérifie un essai =============
    def evaluate_guess(self, word: str) -> list[str]:
        result = [None] * len(word)
        target_counts = {}

        for ch in self.target_word:
            if ch == "-":  # ignore les tirets
                continue
            c = self.remove_accents(ch)
            target_counts[c] = target_counts.get(c, 0) + 1

        for i, c in enumerate(word):
            if self.target_word[i] == "-":  # Skip tirets
                result[i] = "-"
                continue
            if self.remove_accents(c) == self.remove_accents(self.target_word[i]):
                result[i] = "🟩"
                target_counts[self.remove_accents(c)] -= 1

        for i, c in enumerate(word):
            if result[i] or self.target_word[i] == "-":
                continue
            c_clean = self.remove_accents(c)
            if target_counts.get(c_clean, 0) > 0:
                result[i] = "🟨"
                target_counts[c_clean] -= 1
            else:
                result[i] = "⬛"

        return result

    def build_embed(self) -> discord.Embed:
        mode_text = "Multi" if self.author_id is None else "Solo"
        embed = discord.Embed(
            title=f"🎯 M🟡TUS - mode {mode_text}",
            description=f"Mot de **{self.display_length}** lettres",
            color=discord.Color.orange()
        )
        if self.attempts:
            tries_text = "\n\n".join(self.create_feedback_line(entry) for entry in self.attempts)
            embed.add_field(name=f"Essais ({len(self.attempts)}/{self.max_attempts})", value=tries_text, inline=False)
        else:
            embed.add_field(name="Essais", value="*(Aucun essai pour l’instant)*", inline=False)

        if self.finished:
            last_word = self.attempts[-1]['word'] if self.attempts else ""
            if self.remove_accents(last_word) == self.remove_accents(self.target_word):
                embed.color = discord.Color.green()
                embed.set_footer(text="🎉 Bravo ! Tu as trouvé le mot.")
            else:
                embed.color = discord.Color.red()
                embed.set_footer(text=f"💀 Partie terminée. Le mot était {self.target_word}.")

        return embed

    async def process_guess(self, interaction: discord.Interaction, guess: str):
        if self.finished:
            return await safe_respond(interaction, "⚠️ La partie est terminée.", ephemeral=True)

        # Vérifie la longueur hors tirets
        filtered_guess = guess.replace("-", "")
        if len(filtered_guess) != self.display_length:
            return await safe_respond(interaction, f"⚠️ Le mot doit faire {self.display_length} lettres.", ephemeral=True)

        if not is_valid_word(filtered_guess):
            return await safe_respond(interaction, f"❌ `{guess}` n’est pas reconnu comme un mot valide.", ephemeral=True)

        self.attempts.append({'word': guess.upper(), 'hint': False})

        if self.remove_accents(filtered_guess) == self.remove_accents(self.target_word.replace("-", "")) \
                or len(self.attempts) >= self.max_attempts:
            self.finished = True
            for child in self.children:
                child.disabled = True

        await safe_edit(self.message, embed=self.build_embed(), view=self)
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)

    async def on_timeout(self):
        if self.finished:
            return
        self.finished = True
        for child in self.children:
            child.disabled = True
        embed = self.build_embed()
        embed.color = discord.Color.red()
        embed.set_footer(text=f"⏳ Temps écoulé ! Le mot était {self.target_word}.")
        await safe_edit(self.message, embed=embed, view=self)

# ================================================================================
# 🎛️ Bouton Proposer
# ================================================================================
class MotusButton(Button):
    def __init__(self, parent_view: MotusView):
        super().__init__(label="Proposer un mot", style=discord.ButtonStyle.primary)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        if self.parent_view.author_id and interaction.user.id != self.parent_view.author_id:
            return await interaction.response.send_message("❌ Seul le lanceur peut proposer un mot.", ephemeral=True)
        await interaction.response.send_modal(MotusModal(self.parent_view))

# ================================================================================
# 🎛️ Bouton Indice
# ================================================================================
class HintButton(Button):
    def __init__(self, parent_view: MotusView):
        super().__init__(label="Indice", style=discord.ButtonStyle.secondary)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        pv = self.parent_view
        if pv.author_id and interaction.user.id != pv.author_id:
            return await interaction.response.send_message("❌ Seul le lanceur peut utiliser l'indice.", ephemeral=True)
        if pv.finished:
            return await interaction.response.send_message("⚠️ La partie est déjà terminée.", ephemeral=True)

        available_indices = [i for i in range(len(pv.target_word)) if i not in pv.hinted_indices and pv.target_word[i] != "-"]
        if not available_indices:
            return await interaction.response.send_message("ℹ️ Aucune lettre restante à révéler.", ephemeral=True)

        idx = random.choice(available_indices)
        hint_word = ["_" for _ in range(len(pv.target_word))]
        hint_word[idx] = pv.target_word[idx]

        pv.attempts.append({'word': "".join(hint_word), 'hint': True})
        pv.hinted_indices.add(idx)
        self.disabled = True

        if len(pv.attempts) >= pv.max_attempts:
            pv.finished = True
            for child in pv.children:
                child.disabled = True

        await safe_edit(pv.message, embed=pv.build_embed(), view=pv)
        await interaction.response.send_message(f"🔎 Indice utilisé — lettre **{pv.target_word[idx]}** révélée.", ephemeral=True)

# ================================================================================
# 🧠 Cog principal
# ================================================================================
class Motus(commands.Cog):
    """Commande /motus et !motus — Lance une partie de Motus"""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _start_game(self, channel: discord.abc.Messageable, author_id: int, mode: str = "solo"):
        length = random.choice(range(5, 9))
        target_word = await get_random_french_word(length=length)
        author_filter = None if mode.lower() in ("multi", "m") else author_id
        view = MotusView(target_word, max_attempts=None, author_id=author_filter)
        embed = view.build_embed()
        view.message = await safe_send(channel, embed=embed, view=view)

    @app_commands.command(name="motus", description="Lance une partie de Motus (multi = tout le monde peut jouer)")
    @app_commands.describe(mode="Mode de jeu : solo ou multi")
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: (i.user.id))
    async def slash_motus(self, interaction: discord.Interaction, mode: str = "solo"):
        try:
            await interaction.response.defer()
            await self._start_game(interaction.channel, author_id=interaction.user.id, mode=mode)
            await interaction.delete_original_response()
        except app_commands.CommandOnCooldown as e:
            await safe_respond(interaction, f"⏳ Attends encore {e.retry_after:.1f}s.", ephemeral=True)
        except Exception as e:
            print(f"[ERREUR /motus] {e}")
            await safe_respond(interaction, "❌ Une erreur est survenue.", ephemeral=True)

    @commands.command(name="motus", help="Lance une partie de Motus. motus multi ou m pour jouer en multi.")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_motus(self, ctx: commands.Context, mode: str = "solo"):
        try:
            await self._start_game(ctx.channel, author_id=ctx.author.id, mode=mode)
        except commands.CommandOnCooldown as e:
            await safe_send(ctx.channel, f"⏳ Attends encore {e.retry_after:.1f}s.")
        except Exception as e:
            print(f"[ERREUR !motus] {e}")
            await safe_send(ctx.channel, "❌ Une erreur est survenue.")

# ================================================================================
# 🔌 Setup du Cog
# ================================================================================
async def setup(bot: commands.Bot):
    cog = Motus(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Jeux"
    await bot.add_cog(cog)
