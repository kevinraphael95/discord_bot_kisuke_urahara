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
from discord.ext import commands, tasks
import random, unicodedata, asyncio
from spellchecker import SpellChecker
from utils.discord_utils import safe_send, safe_edit

# Nouveau module pour générer des mots français aléatoires
from random_words_generator.words import generate_random_words

# ────────────────────────────────────────────────────────────────────────────────
# 🌐 Initialisation du spellchecker français
# ────────────────────────────────────────────────────────────────────────────────
spell = SpellChecker(language='fr')

# ────────────────────────────────────────────────────────────────────────────────
# 🌐 Fonction pour récupérer un mot français aléatoire
# ────────────────────────────────────────────────────────────────────────────────
async def get_random_french_word(length: int | None = None) -> str:
    """
    Retourne un mot français aléatoire.
    Si length est spécifié, essaie de choisir un mot de cette longueur.
    """
    try:
        # Génère jusqu'à 20 mots aléatoires
        candidates = generate_random_words(20)
        # Filtrer par longueur si demandé
        if length:
            candidates = [w for w in candidates if len(w) == length]
        if candidates:
            return random.choice(candidates).upper()
    except Exception as e:
        print(f"[ERREUR random_words_generator] {e}")
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
    """Classe représentant une partie d'Anagramme"""
    def __init__(self, target_word: str, author_id: int | None = None, multi: bool = False):
        normalized = target_word.replace("Œ", "OE").replace("œ", "oe")
        self.target_word = normalized.upper()
        self.display_word = ''.join(random.sample(self.target_word, len(self.target_word)))
        self.display_length = len([c for c in self.target_word if c.isalpha()])
        self.author_id = author_id
        self.multi = multi
        self.max_attempts = None if multi else max(self.display_length, 5)
        self.attempts: list[dict] = []
        self.message = None
        self.finished = False
        self.start_time = asyncio.get_event_loop().time()

    def remove_accents(self, text: str) -> str:
        return ''.join(
            c for c in unicodedata.normalize('NFD', text)
            if unicodedata.category(c) != 'Mn'
        ).upper()

    def build_embed(self) -> discord.Embed:
        mode_text = "Solo 🧍‍♂️" if not self.multi else "Multi 🌍"
        embed = discord.Embed(
            title=f"🔀 Anagramme - {mode_text}",
            description=f"Mot mélangé : **{' '.join(self.display_word)}**",
            color=discord.Color.orange()
        )

        instructions = (
            "💡 **Comment jouer en mode Multi :**\n"
            "1️⃣ Tout le monde peut participer.\n"
            f"2️⃣ Proposez un mot avec `.` ou `*` suivi de votre essai.\n"
            f"3️⃣ Le mot doit faire {self.display_length} lettres.\n"
            "4️⃣ Il n’y a **aucune limite d’essais**.\n"
            "5️⃣ La partie se termine automatiquement après 3 minutes ou quand le mot est trouvé."
            if self.multi else
            "💡 **Comment jouer en mode Solo :**\n"
            f"1️⃣ Proposez un mot avec `.` ou `*` suivi de votre essai.\n"
            f"2️⃣ Le mot doit faire {self.display_length} lettres.\n"
            f"3️⃣ Vous avez {self.max_attempts} essais maximum.\n"
            "4️⃣ La partie se termine quand le mot est trouvé ou après 3 minutes."
        )
        embed.add_field(name="📝 Instructions", value=instructions, inline=False)

        if self.attempts:
            tries_text = "\n".join(f"{entry['author']}: {entry['word']}" for entry in self.attempts)
            field_name = f"Essais ({len(self.attempts)})" if self.multi else f"Essais ({len(self.attempts)}/{self.max_attempts})"
            embed.add_field(name=field_name, value=tries_text, inline=False)
        else:
            embed.add_field(name="Essais", value="*(Aucun essai pour l’instant)*", inline=False)

        if self.finished:
            last_word = self.attempts[-1]['word'] if self.attempts else ""
            if self.remove_accents(last_word) == self.remove_accents(self.target_word):
                embed.color = discord.Color.green()
                embed.set_footer(text="🎉 Bravo ! Le mot a été trouvé.")
            else:
                embed.color = discord.Color.red()
                embed.set_footer(text=f"💀 Partie terminée. Le mot était {self.target_word}.")
        else:
            elapsed = int(asyncio.get_event_loop().time() - self.start_time)
            remaining = max(0, 180 - elapsed)
            embed.set_footer(text=f"⏳ Temps restant : {remaining} secondes")

        return embed

    async def process_guess(self, channel: discord.abc.Messageable, guess: str, author_name: str, author_id: int):
        if self.finished: return await safe_send(channel, "⚠️ La partie est terminée.")
        if not self.multi and author_id != self.author_id: return

        filtered_guess = guess.strip(".* ").upper()

        if len(filtered_guess) != self.display_length:
            return await safe_send(channel, f"⚠️ Le mot doit faire {self.display_length} lettres.")
        if not is_valid_word(filtered_guess):
            return await safe_send(channel, f"❌ `{filtered_guess}` n’est pas reconnu comme un mot valide.")

        self.attempts.append({'word': filtered_guess, 'author': author_name})

        if self.remove_accents(filtered_guess) == self.remove_accents(self.target_word):
            self.finished = True
        elif not self.multi and len(self.attempts) >= self.max_attempts:
            self.finished = True

        if self.message:
            await safe_edit(self.message, embed=self.build_embed())

    async def check_timeout(self):
        while not self.finished:
            await asyncio.sleep(5)
            if asyncio.get_event_loop().time() - self.start_time >= 180:
                self.finished = True
                if self.message:
                    await safe_edit(self.message, embed=self.build_embed())
                break

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class Anagramme(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active_games: dict[int, AnagrammeView] = {}

    async def _start_game(self, channel: discord.abc.Messageable, author_id: int, mode: str = "solo"):
        length = random.choice(range(5, 9))
        target_word = await get_random_french_word(length=length)
        multi = mode.lower() in ("multi", "m")
        author_filter = None if multi else author_id
        view = AnagrammeView(target_word, author_id=author_filter, multi=multi)
        view.message = await safe_send(channel, embed=view.build_embed())
        self.active_games[channel.id] = view
        asyncio.create_task(view.check_timeout())

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot: return
        if message.channel.id not in self.active_games: return
        if message.content.strip().startswith((".", "*")):
            view = self.active_games[message.channel.id]
            await view.process_guess(message.channel, message.content, message.author.display_name, message.author.id)

    # ────────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────────
    @app_commands.command(name="anagramme", description="Lance une partie d'Anagramme (multi = tout le monde peut jouer)")
    @app_commands.describe(mode="Mode de jeu : solo ou multi")
    async def slash_anagramme(self, interaction: discord.Interaction, mode: str = "solo"):
        await interaction.response.defer()
        await self._start_game(interaction.channel, author_id=interaction.user.id, mode=mode)
        await interaction.delete_original_response()

    # ────────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────────
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
