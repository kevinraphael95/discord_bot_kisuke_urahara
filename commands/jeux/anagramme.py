# ────────────────────────────────────────────────────────────────────────────────
# 📌 anagramme.py — Jeu de l'anagramme basé sur GameView
# Objectif : Jeu interactif solo/multi avec embed, tentatives, timeout et messages ./*
# Catégorie : Jeux
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord, random, unicodedata, asyncio, aiohttp
from discord import app_commands
from discord.ext import commands
from spellchecker import SpellChecker
from utils.discord_utils import safe_send, safe_edit
from utils.game_view import GameView

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
                    if isinstance(data, list) and data:
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
# 🎮 Vue Anagramme basée sur GameView
# ────────────────────────────────────────────────────────────────────────────────
class AnagrammeView(GameView):
    TIMEOUT = 180  # 3 minutes

    def __init__(self, target_word: str, author_id: int | None = None, multi: bool = False, channel: discord.TextChannel | None = None):
        super().__init__(author_id=author_id, multi=multi, channel=channel, timeout=self.TIMEOUT)
        normalized = target_word.replace("Œ", "OE").replace("œ", "oe")
        self.target_word = normalized.upper()
        self.display_word = ''.join(random.sample(self.target_word, len(self.target_word)))
        self.display_length = len([c for c in self.target_word if c.isalpha()])
        self.max_attempts = None if multi else max(self.display_length, 5)

    def remove_accents(self, text: str) -> str:
        return ''.join(c for c in unicodedata.normalize('NFD', text)
                       if unicodedata.category(c) != 'Mn').upper()

    def build_embed(self) -> discord.Embed:
        """Embed dynamique avec instructions et tentatives"""
        mode_text = "Multi 🌍" if self.multi else "Solo 🧍‍♂️"
        embed = discord.Embed(
            title=f"🔀 Anagramme - {mode_text}",
            description=f"Mot mélangé : **{' '.join(self.display_word)}**",
            color=discord.Color.orange()
        )

        # Instructions
        if self.multi:
            instructions = (
                "💡 **Mode Multi :** Tout le monde peut participer.\n"
                "Envoyez un mot avec `.` ou `*`.\n"
                f"Le mot doit faire {self.display_length} lettres.\n"
                "Tentatives illimitées.\n"
                "Durée max : 3 minutes ou quand le mot est trouvé."
            )
        else:
            instructions = (
                "💡 **Mode Solo :**\n"
                f"Envoyez un mot avec `.` ou `*`.\n"
                f"Le mot doit faire {self.display_length} lettres.\n"
                f"Vous avez {self.max_attempts} essais maximum.\n"
                "Partie terminée si mot trouvé ou après 3 minutes."
            )
        embed.add_field(name="📝 Instructions", value=instructions, inline=False)

        # Essais
        if self.attempts:
            tries_text = "\n".join(f"{entry['user']}: {entry['value']}" for entry in self.attempts)
            field_name = f"Essais ({len(self.attempts)})" if self.multi else f"Essais ({len(self.attempts)}/{self.max_attempts})"
            embed.add_field(name=field_name, value=tries_text, inline=False)
        else:
            embed.add_field(name="Essais", value="*(Aucun essai pour l’instant)*", inline=False)

        # Footer
        if self.finished:
            last_word = self.attempts[-1]['value'] if self.attempts else ""
            if self.remove_accents(last_word) == self.remove_accents(self.target_word):
                embed.color = discord.Color.green()
                embed.set_footer(text="🎉 Bravo ! Le mot a été trouvé.")
            else:
                embed.color = discord.Color.red()
                embed.set_footer(text=f"💀 Partie terminée. Le mot était {self.target_word}.")
        else:
            elapsed = int(asyncio.get_event_loop().time() - self.start_time)
            remaining = max(0, self.timeout - elapsed)
            embed.set_footer(text=f"⏳ Temps restant : {remaining} secondes")

        return embed

    async def process_guess(self, user: discord.User, guess: str) -> tuple[bool, str]:
        """Traite une tentative"""
        if self.finished:
            return False, "⚠️ La partie est terminée."
        if not self.can_play(user.id):
            return False, "❌ Vous ne pouvez pas jouer en solo."

        filtered = guess.strip(".* ").upper()
        if len(filtered) != self.display_length:
            return False, f"⚠️ Le mot doit faire {self.display_length} lettres."
        if not is_valid_word(filtered):
            return False, f"❌ `{filtered}` n’est pas reconnu comme un mot valide."

        self.add_attempt(user, filtered)

        if self.remove_accents(filtered) == self.remove_accents(self.target_word):
            self.finished = True
        elif not self.multi and len(self.attempts) >= self.max_attempts:
            self.finished = True

        if self.message:
            await safe_edit(self.message, embed=self.build_embed())

        return True, f"{user} a joué `{filtered}`"

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class Anagramme(commands.Cog):
    """Commande /anagramme et !anagramme — jeu interactif"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active_games: dict[int, AnagrammeView] = {}  # channel.id -> vue de jeu

    async def _start_game(self, channel: discord.abc.Messageable, author_id: int, mode: str = "solo"):
        if channel.id in self.active_games and not self.active_games[channel.id].finished:
            return  # silence si jeu déjà actif
        length = random.choice(range(5, 9))
        target_word = await get_random_french_word(length=length)
        multi = mode.lower() in ("multi", "m")
        author_filter = None if multi else author_id
        view = AnagrammeView(target_word, author_id=author_filter, multi=multi, channel=channel)
        await view.send_message(embed=view.build_embed())
        self.active_games[channel.id] = view
        asyncio.create_task(view.start_timer(remove_callback=lambda: self.active_games.pop(channel.id, None)))

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if message.channel.id not in self.active_games:
            return
        content = message.content.strip()
        if content.startswith((".", "*")):
            view = self.active_games[message.channel.id]
            await view.process_guess(message.author, content)
            try:
                await message.delete()
            except:
                pass

    @app_commands.command(name="anagramme", description="Lance une partie d'Anagramme (multi = tout le monde peut jouer)")
    @app_commands.describe(mode="Mode de jeu : solo ou multi")
    async def slash_anagramme(self, interaction: discord.Interaction, mode: str = "solo"):
        await interaction.response.defer()
        await self._start_game(interaction.channel, interaction.user.id, mode=mode)
        try:
            await interaction.delete_original_response()
        except:
            pass

    @commands.command(name="anagramme", help="Lance une partie d'Anagramme. anagramme multi ou m pour jouer en multi.")
    async def prefix_anagramme(self, ctx: commands.Context, mode: str = "solo"):
        await self._start_game(ctx.channel, ctx.author.id, mode=mode)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Anagramme(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Jeux"
    await bot.add_cog(cog)
