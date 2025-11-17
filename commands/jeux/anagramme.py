# ────────────────────────────────────────────────────────────────────────────────
# 📌 anagramme.py — Commande interactive /anagramme et !anagramme
# Objectif : Jeu de l'anagramme avec embed, tentatives limitées et feedback
# Catégorie : Jeux
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
import random, aiohttp, unicodedata
from spellchecker import SpellChecker
from utils.discord_utils import safe_send, safe_edit, safe_respond

# ────────────────────────────────────────────────────────────────────────────────
# 🌐 Initialisation du spellchecker français
# ────────────────────────────────────────────────────────────────────────────────
spell = SpellChecker(language='fr')

# ────────────────────────────────────────────────────────────────────────────────
# 🌐 Fonction pour récupérer un mot français aléatoire
# ────────────────────────────────────────────────────────────────────────────────
async def get_random_french_word(length: int | None = None) -> str:
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
        print(f"[ERREUR API Anagramme] {e}")
    return "PYTHON"

# ────────────────────────────────────────────────────────────────────────────────
# 🌐 Vérification d’un mot via SpellChecker
# ────────────────────────────────────────────────────────────────────────────────
def is_valid_word(word: str) -> bool:
    return word.lower() in spell.word_frequency

# ────────────────────────────────────────────────────────────────────────────────
# 🎮 Vue principale du jeu
# ────────────────────────────────────────────────────────────────────────────────
class AnagrammeView:
    def __init__(self, target_word: str, max_attempts: int | None = None, author_id: int | None = None):
        normalized = target_word.replace("Œ", "OE").replace("œ", "oe")
        self.target_word = normalized.upper()
        self.display_word = ''.join(random.sample(self.target_word, len(self.target_word)))
        self.display_length = len([c for c in self.target_word if c.isalpha()])
        base_attempts = max(self.display_length, 5)
        self.max_attempts = max_attempts if max_attempts else base_attempts
        self.attempts: list[dict] = []
        self.message = None
        self.finished = False
        self.author_id = author_id
        self.hinted_indices: set[int] = set()

    def remove_accents(self, text: str) -> str:
        return ''.join(
            c for c in unicodedata.normalize('NFD', text)
            if unicodedata.category(c) != 'Mn'
        ).upper()

    def create_feedback_line(self, entry: dict) -> str:
        word = entry['word']
        letters = " ".join(
            c if i >= len(self.target_word) or self.remove_accents(c) != self.remove_accents(self.target_word[i])
            else c
            for i, c in enumerate(word)
        )
        return letters

    def build_embed(self) -> discord.Embed:
        mode_text = "Solo 🧍‍♂️" if self.author_id else "Multi 🌍"
        embed = discord.Embed(
            title=f"🔀 Anagramme - {mode_text}",
            description=f"Mot mélangé : **{' '.join(self.display_word)}**",
            color=discord.Color.orange()
        )
        if self.attempts:
            tries_text = "\n".join(entry['word'] for entry in self.attempts)
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
        else:
            embed.set_footer(text=f"⏳ Temps restant : 180 secondes")
        return embed

    async def process_guess(self, channel: discord.abc.Messageable, guess: str):
        if self.finished:
            return await safe_send(channel, "⚠️ La partie est terminée.")
        filtered_guess = guess.strip(".* ").upper()
        if len(filtered_guess) != self.display_length:
            return await safe_send(channel, f"⚠️ Le mot doit faire {self.display_length} lettres.")
        if not is_valid_word(filtered_guess):
            return await safe_send(channel, f"❌ `{filtered_guess}` n’est pas reconnu comme un mot valide.")
        self.attempts.append({'word': filtered_guess})
        if self.remove_accents(filtered_guess) == self.remove_accents(self.target_word) or len(self.attempts) >= self.max_attempts:
            self.finished = True
        if self.message:
            await safe_edit(self.message, embed=self.build_embed())

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class Anagramme(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active_games: dict[int, AnagrammeView] = {}  # channel_id -> view

    async def _start_game(self, channel: discord.abc.Messageable, author_id: int, mode: str = "solo"):
        length = random.choice(range(5, 9))
        target_word = await get_random_french_word(length=length)
        author_filter = None if mode.lower() in ("multi", "m") else author_id
        view = AnagrammeView(target_word, author_id=author_filter)
        embed = view.build_embed()
        view.message = await safe_send(channel, embed=embed)
        self.active_games[channel.id] = view

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if message.channel.id not in self.active_games:
            return
        content = message.content.strip()
        if content.startswith((".", "*")):
            view = self.active_games[message.channel.id]
            await view.process_guess(message.channel, content)

    @app_commands.command(name="anagramme", description="Lance une partie d'Anagramme (multi = tout le monde peut jouer)")
    @app_commands.describe(mode="Mode de jeu : solo ou multi")
    async def slash_anagramme(self, interaction: discord.Interaction, mode: str = "solo"):
        await interaction.response.defer()
        await self._start_game(interaction.channel, author_id=interaction.user.id, mode=mode)
        await interaction.delete_original_response()

    @commands.command(name="anagramme", help="Lance une partie d'Anagramme. anagramme multi ou m pour jouer en multi.")
    async def prefix_anagramme(self, ctx: commands.Context, mode: str = "solo"):
        await self._start_game(ctx.channel, author_id=ctx.author.id, mode=mode)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Anagramme(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Jeux"
    await bot.add_cog(cog)
