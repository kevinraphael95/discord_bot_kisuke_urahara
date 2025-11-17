# ────────────────────────────────────────────────────────────────────────────────
# 📌 anagramme.py — Commande interactive /anagramme et !anagramme
# Objectif : Jeu de l'anagramme avec embed, solo et multi, fin auto au bout de 3 minutes
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
import random, asyncio, unicodedata, aiohttp
from spellchecker import SpellChecker
from utils.discord_utils import safe_send, safe_edit

# ────────────────────────────────────────────────────────────────────────────────
# 🌐 Spellchecker français
# ────────────────────────────────────────────────────────────────────────────────
spell = SpellChecker(language='fr')

# ────────────────────────────────────────────────────────────────────────────────
# 🌐 Récupération d’un mot français aléatoire
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

def is_valid_word(word: str) -> bool:
    return word.lower() in spell.word_frequency

# ────────────────────────────────────────────────────────────────────────────────
# 🎮 Vue principale du jeu
# ────────────────────────────────────────────────────────────────────────────────
class AnagrammeView:
    """Classe représentant une partie d'Anagramme"""

    def __init__(self, target_word: str, author_id: int | None = None, multi: bool = False):
        self.target_word = target_word.upper()
        self.display_word = ''.join(random.sample(self.target_word, len(self.target_word)))
        self.author_id = author_id
        self.multi = multi
        self.attempts: list[str] = []
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
            "💡 **Comment jouer :**\n"
            "1️⃣ Propose un mot avec `.` ou `*` suivi de ton essai.\n"
            "2️⃣ La partie se termine après 3 minutes ou si le mot est trouvé.\n"
            "3️⃣ Mode solo : seul le lanceur peut jouer.\n"
            "4️⃣ Mode multi : tout le monde peut jouer."
        )
        embed.add_field(name="📝 Instructions", value=instructions, inline=False)
        return embed

    async def process_guess(self, channel: discord.abc.Messageable, guess: str, author_id: int):
        if self.finished or (not self.multi and author_id != self.author_id):
            return
        filtered = guess.strip(".* ").upper()
        if self.remove_accents(filtered) == self.remove_accents(self.target_word):
            self.finished = True
            if self.message:
                embed = self.build_embed()
                embed.color = discord.Color.green()
                embed.set_footer(text=f"🎉 Bravo ! Le mot était {self.target_word}")
                await safe_edit(self.message, embed=embed)
            return
        self.attempts.append(filtered)
        if self.message:
            await safe_edit(self.message, embed=self.build_embed())

    async def check_timeout(self):
        while not self.finished:
            await asyncio.sleep(5)
            if asyncio.get_event_loop().time() - self.start_time >= 180:
                self.finished = True
                if self.message:
                    embed = self.build_embed()
                    embed.color = discord.Color.red()
                    embed.set_footer(text=f"💀 Temps écoulé ! Le mot était {self.target_word}")
                    await safe_edit(self.message, embed=embed)

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class Anagramme(commands.Cog):
    """Commande /anagramme et !anagramme — Jeu de l'anagramme"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active_games: dict[int, AnagrammeView] = {}

    async def _start_game(self, channel: discord.abc.Messageable, user_id: int, multi: bool = False):
        if channel.id in self.active_games and not self.active_games[channel.id].finished:
            return await safe_send(channel, "⚠️ Une partie est déjà en cours dans ce salon.")
        word = await get_random_french_word(random.randint(5, 8))
        view = AnagrammeView(word, author_id=None if multi else user_id, multi=multi)
        view.message = await safe_send(channel, embed=view.build_embed())
        self.active_games[channel.id] = view
        asyncio.create_task(view.check_timeout())

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(name="anagramme", description="Joue à l'Anagramme (ajoute 'm' ou 'multi' pour le mode multi)")
    async def slash_anagramme(self, interaction: discord.Interaction, mode: str = None):
        multi = mode and mode.lower() in ("m", "multi")
        await interaction.response.defer()
        await self._start_game(interaction.channel, user_id=interaction.user.id, multi=multi)
        await interaction.delete_original_response()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="anagramme")
    async def prefix_anagramme(self, ctx: commands.Context, mode: str = None):
        multi = mode and mode.lower() in ("m", "multi")
        await self._start_game(ctx.channel, user_id=ctx.author.id, multi=multi)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Anagramme(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Jeux"
    await bot.add_cog(cog)
