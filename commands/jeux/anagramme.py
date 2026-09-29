# ================================================================================
# 📌 anagramme.py — Commande interactive /anagramme et !anagramme
# Objectif : Jeu de l'anagramme avec embed, tentatives limitées et feedback
# Catégorie : Jeux
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ================================================================================

# ================================================================================
# 📦 Imports nécessaires
# ================================================================================
import asyncio
import logging
import random

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from spellchecker import SpellChecker

from utils.discord_utils import safe_send, safe_edit, safe_respond
from utils.jeux_utils import normalize_text, parse_mode, ReplyView, BuzzerView

log = logging.getLogger(__name__)

# ================================================================================
# 🌐 Initialisation du spellchecker français
# ================================================================================
spell = SpellChecker(language='fr')

# ================================================================================
# 🌐 Récupération d'un mot français aléatoire
# ================================================================================
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
        log.exception("[anagramme] Erreur API : %s", e)
    return "PYTHON"

# ================================================================================
# 🌐 Vérification d'un mot via SpellChecker
# ================================================================================
def is_valid_word(word: str) -> bool:
    return word.lower() in spell.word_frequency

# ================================================================================
# 🎮 Vue principale du jeu
# ================================================================================
class AnagrammeView:
    """Classe représentant une partie d'Anagramme"""

    def __init__(self, target_word: str, author_id: int | None = None, multi: bool = False):
        normalized = target_word.replace("Œ", "OE").replace("œ", "oe")
        self.target_word    = normalized.upper()
        self.display_word   = ''.join(random.sample(self.target_word, len(self.target_word)))
        self.display_length = len([c for c in self.target_word if c.isalpha()])
        self.author_id      = author_id
        self.multi          = multi
        self.max_attempts   = None if multi else max(self.display_length, 5)
        self.attempts: list[dict] = []
        self.message        = None
        self.finished       = False
        self.start_time     = asyncio.get_event_loop().time()

    def build_embed(self) -> discord.Embed:
        mode_text = "Solo 🧍‍♂️" if not self.multi else "Multi 🌍"
        embed = discord.Embed(
            title=f"🔀 Anagramme - {mode_text}",
            description=f"Mot mélangé : **{' '.join(self.display_word)}**",
            color=discord.Color.orange()
        )

        if self.multi:
            instructions = (
                "💡 **Comment jouer en mode Multi :**\n"
                "1️⃣ Clique sur **🔔 Buzzer** pour prendre la main.\n"
                "2️⃣ Le plus rapide ouvre une fenêtre pour proposer un mot.\n"
                f"3️⃣ Le mot doit faire {self.display_length} lettres.\n"
                "4️⃣ Il n'y a **aucune limite d'essais**.\n"
                "5️⃣ La partie se termine après 3 minutes ou quand le mot est trouvé."
            )
        else:
            instructions = (
                "💡 **Comment jouer en mode Solo :**\n"
                "1️⃣ Clique sur **✍️ Répondre** pour proposer ta réponse.\n"
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
            embed.add_field(name="Essais", value="*(Aucun essai pour l'instant)*", inline=False)

        if self.finished:
            last_word = self.attempts[-1]['word'] if self.attempts else ""
            if normalize_text(last_word) == normalize_text(self.target_word):
                embed.color = discord.Color.green()
                embed.set_footer(text="🎉 Bravo ! Le mot a été trouvé.")
            else:
                embed.color = discord.Color.red()
                embed.set_footer(text=f"💀 Partie terminée. Le mot était {self.target_word}.")
        else:
            elapsed   = int(asyncio.get_event_loop().time() - self.start_time)
            remaining = max(0, 180 - elapsed)
            embed.set_footer(text=f"⏳ Temps restant : {remaining} secondes")

        return embed

    async def process_guess(self, channel, guess: str, author_name: str, author_id: int, silent: bool = False):
        """Vérifie la proposition."""
        if self.finished:
            if not silent:
                await safe_send(channel, "⚠️ La partie est terminée.")
            return False

        if not self.multi and author_id != self.author_id:
            return False

        filtered_guess = guess.strip(".* ").upper()

        if len(filtered_guess) != self.display_length:
            if not silent:
                await safe_send(channel, f"⚠️ Le mot doit faire {self.display_length} lettres.")
            return False
        if not is_valid_word(filtered_guess):
            if not silent:
                await safe_send(channel, f"❌ `{filtered_guess}` n'est pas reconnu comme un mot valide.")
            return False

        self.attempts.append({'word': filtered_guess, 'author': author_name})

        if normalize_text(filtered_guess) == normalize_text(self.target_word):
            self.finished = True
        elif not self.multi and len(self.attempts) >= self.max_attempts:
            self.finished = True

        if self.message:
            await safe_edit(self.message, embed=self.build_embed())

        return True

    async def check_timeout(self):
        """Arrête la partie après 3 minutes"""
        while not self.finished:
            await asyncio.sleep(5)
            elapsed = asyncio.get_event_loop().time() - self.start_time
            if elapsed >= 180:
                self.finished = True
                if self.message:
                    await safe_edit(self.message, embed=self.build_embed())
                break

# ================================================================================
# 🧠 Cog principal
# ================================================================================
class Anagramme(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot          = bot
        self.active_games: dict[int, AnagrammeView] = {}

    async def _start_game(self, channel: discord.abc.Messageable, author_id: int, mode: str = "solo"):
        length      = random.choice(range(5, 9))
        target_word = await get_random_french_word(length=length)
        multi       = parse_mode(mode)
        author_filter = None if multi else author_id

        view  = AnagrammeView(target_word, author_id=author_filter, multi=multi)
        embed = view.build_embed()

        # ── Mode Solo : bouton "✍️ Répondre" ──
        if not multi:
            async def on_submit(interaction, answer):
                await view.process_guess(
                    interaction.channel,
                    answer,
                    interaction.user.display_name,
                    interaction.user.id,
                    silent=True,
                )
                if not view.finished:
                    await safe_respond(interaction, "✅ Proposition envoyée !", ephemeral=True)
                else:
                    await safe_respond(interaction, "🎉 Bien joué !", ephemeral=True)

            reply_view = ReplyView(
                user_id=author_id,
                modal_title="✍️ Propose ton mot",
                modal_label="Mot",
                modal_placeholder=f"Mot de {view.display_length} lettres",
                modal_max_length=view.display_length,
                on_submit=on_submit,
                timeout=180,
            )
            msg = await safe_send(channel, embed=embed, view=reply_view)
            if msg is not None:
                reply_view.message = msg
                view.message       = msg

        # ── Mode Multi : buzzer ──
        else:
            buzz_ref = {"view": None}  # référence circulaire

            async def on_buzz(interaction):
                # Mention dans le salon
                await safe_send(
                    interaction.channel,
                    f"🎯 {interaction.user.mention} a buzzé ! À toi de proposer.",
                )

            async def on_submit(interaction, answer):
                ok = await view.process_guess(
                    interaction.channel,
                    answer,
                    interaction.user.display_name,
                    interaction.user.id,
                    silent=True,
                )
                if ok:
                    await safe_respond(interaction, "✅ Proposition envoyée !", ephemeral=True)
                else:
                    await safe_respond(interaction, "❌ Proposition invalide.", ephemeral=True)

            buzz_view = BuzzerView(
                modal_title="✍️ Propose ton mot",
                modal_label="Mot",
                modal_placeholder=f"Mot de {view.display_length} lettres",
                modal_max_length=view.display_length,
                on_submit=on_submit,
                on_buzz=on_buzz,
                buzz_timeout=30,
                view_timeout=180,
            )
            msg = await safe_send(channel, embed=embed, view=buzz_view)
            if msg is not None:
                buzz_view.message = msg
                view.message      = msg

        if view.message is None:
            return

        self.active_games[channel.id] = view
        asyncio.create_task(view.check_timeout())

    # ============================================================================
    # 🔹 Commande SLASH
    # ============================================================================
    @app_commands.command(name="anagramme", description="Lance une partie d'Anagramme (multi = tout le monde peut jouer)")
    @app_commands.describe(mode="Mode de jeu : solo ou multi")
    async def slash_anagramme(self, interaction: discord.Interaction, mode: str = "solo"):
        await interaction.response.defer()
        await self._start_game(interaction.channel, author_id=interaction.user.id, mode=mode)
        await interaction.delete_original_response()

    # ============================================================================
    # 🔹 Commande PREFIX
    # ============================================================================
    @commands.command(name="anagramme", help="Lance une partie d'Anagramme. anagramme multi ou m pour jouer en multi.")
    async def prefix_anagramme(self, ctx: commands.Context, mode: str = "solo"):
        await self._start_game(ctx.channel, author_id=ctx.author.id, mode=mode)

# ================================================================================
# 🔌 Setup du Cog
# ================================================================================
async def setup(bot: commands.Bot):
    cog = Anagramme(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Jeux"
    await bot.add_cog(cog)
