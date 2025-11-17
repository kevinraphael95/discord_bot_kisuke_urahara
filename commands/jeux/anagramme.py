# ────────────────────────────────────────────────────────────────────────────────
# 📌 anagramme.py — Commande interactive /anagramme et !anagramme
# Objectif : Jeu de l’anagramme avec embed, tentatives et gestion du temps
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
import random, aiohttp, unicodedata, asyncio
from spellchecker import SpellChecker
from utils.discord_utils import safe_send, safe_edit

# ────────────────────────────────────────────────────────────────────────────────
# 🌐 Initialisation du SpellChecker français
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
# 🔤 Vérification d’un mot via SpellChecker
# ────────────────────────────────────────────────────────────────────────────────
def is_valid_word(word: str) -> bool:
    return word.lower() in spell.word_frequency

# ────────────────────────────────────────────────────────────────────────────────
# 🎮 Vue principale du jeu
# ────────────────────────────────────────────────────────────────────────────────
class AnagrammeView:
    """Classe représentant une partie d'Anagramme."""

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

    # ────────────────────────────────────────────────────────────────────────────
    # 🔤 Normalisation des accents
    # ────────────────────────────────────────────────────────────────────────────
    def remove_accents(self, text: str) -> str:
        return ''.join(
            c for c in unicodedata.normalize('NFD', text)
            if unicodedata.category(c) != 'Mn'
        ).upper()

    # ────────────────────────────────────────────────────────────────────────────
    # 🧱 Construction de l'embed
    # ────────────────────────────────────────────────────────────────────────────
    def build_embed(self) -> discord.Embed:
        mode_text = "Solo 🧍‍♂️" if not self.multi else "Multi 🌍"

        embed = discord.Embed(
            title=f"🔀 Anagramme - {mode_text}",
            description=f"Mot mélangé : **{' '.join(self.display_word)}**",
            color=discord.Color.orange()
        )

        # ─ Instructions du jeu ─
        if self.multi:
            instructions = (
                "💡 **Mode Multi :**\n"
                "• Tout le monde peut participer.\n"
                "• Proposez un mot avec `.mot` ou `*mot`.\n"
                f"• Le mot doit faire **{self.display_length} lettres**.\n"
                "• Tentatives illimitées.\n"
                "• Durée maximale : 3 minutes."
            )
        else:
            instructions = (
                "💡 **Mode Solo :**\n"
                "• Proposez un mot avec `.mot` ou `*mot`.\n"
                f"• Le mot doit faire **{self.display_length} lettres**.\n"
                f"• Vous avez **{self.max_attempts} essais**.\n"
                "• Durée maximale : 3 minutes."
            )
        embed.add_field(name="📝 Instructions", value=instructions, inline=False)

        # ─ Historique des essais ─
        if self.attempts:
            tries_text = "\n".join(f"{entry['author']}: {entry['word']}" for entry in self.attempts)
            field_name = (
                f"Essais ({len(self.attempts)})" if self.multi
                else f"Essais ({len(self.attempts)}/{self.max_attempts})"
            )
            embed.add_field(name=field_name, value=tries_text, inline=False)
        else:
            embed.add_field(name="Essais", value="*(Aucun essai pour l’instant)*", inline=False)

        # ─ Footer : temps ou résultat ─
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

    # ────────────────────────────────────────────────────────────────────────────
    # 🧠 Traitement d'une tentative
    # ────────────────────────────────────────────────────────────────────────────
    async def process_guess(self, channel, guess: str, author_name: str, author_id: int):
        if self.finished:
            return

        if not self.multi and author_id != self.author_id:
            return

        filtered = guess.strip(".* ").upper()

        if len(filtered) != self.display_length:
            return

        if not is_valid_word(filtered):
            return

        self.attempts.append({"word": filtered, "author": author_name})

        if self.remove_accents(filtered) == self.remove_accents(self.target_word):
            self.finished = True
        elif not self.multi and len(self.attempts) >= self.max_attempts:
            self.finished = True

        if self.message:
            await safe_edit(self.message, embed=self.build_embed())

    # ────────────────────────────────────────────────────────────────────────────
    # ⏳ Timeout automatique
    # ────────────────────────────────────────────────────────────────────────────
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
    """Commande /anagramme et !anagramme — Jeu de l’anagramme interactif."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active_games: dict[int, AnagrammeView] = {}

    # ────────────────────────────────────────────────────────────────────────────
    # 🟦 Lancement d’une partie
    # ────────────────────────────────────────────────────────────────────────────
    async def _start_game(self, channel: discord.abc.Messageable, author_id: int, mode: str = "solo"):
        if channel.id in self.active_games:
            return

        length = random.choice(range(5, 9))
        target = await get_random_french_word(length=length)
        multi = mode.lower() in ("multi", "m")

        view = AnagrammeView(target, author_id=None if multi else author_id, multi=multi)
        view.message = await safe_send(channel, embed=view.build_embed())

        self.active_games[channel.id] = view
        asyncio.create_task(view.check_timeout())

    # ────────────────────────────────────────────────────────────────────────────
    # 📨 Gestion des messages (tentatives)
    # ────────────────────────────────────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if message.channel.id not in self.active_games:
            return

        if not message.content.strip().startswith((".", "*")):
            return

        view = self.active_games[message.channel.id]
        await view.process_guess(message.channel, message.content, message.author.display_name, message.author.id)

        try:
            await message.delete()  # suppression automatique pour éviter le spam
        except:
            pass

        if view.finished:
            del self.active_games[message.channel.id]

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(name="anagramme", description="Lance une partie d'Anagramme.")
    @app_commands.describe(mode="Choisir : solo / multi")
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_anagramme(self, interaction: discord.Interaction, mode: str = "solo"):
        await self._start_game(interaction.channel, author_id=interaction.user.id, mode=mode)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="anagramme", help="Lance une partie d'Anagramme.")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
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
