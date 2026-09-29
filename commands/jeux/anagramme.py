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
from collections import Counter

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
        self.target_word       = normalized.upper()
        self.display_word      = ''.join(random.sample(self.target_word, len(self.target_word)))
        self.display_length    = len([c for c in self.target_word if c.isalpha()])
        self.author_id         = author_id
        self.multi             = multi
        self.max_attempts      = None if multi else max(self.display_length, 5)
        self.attempts: list[dict] = []
        self.message           = None
        self.finished          = False
        self.winner: str | None = None
        self.start_time        = asyncio.get_event_loop().time()

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
            if self.winner:
                embed.title = f"🔀 Anagramme - Gagné !"
                embed.color = discord.Color.green()
                embed.description = f"Mot mélangé : **{' '.join(self.display_word)}**\n\n🏆 **{self.winner}** a trouvé ! C'était bien **{self.target_word}**."
                embed.set_footer(text="Partie terminée")
            else:
                embed.title = f"🔀 Anagramme - Terminé"
                embed.color = discord.Color.red()
                embed.description = f"Mot mélangé : **{' '.join(self.display_word)}**\n\n❌ Personne n'a trouvé. Le mot était **{self.target_word}**."
                embed.set_footer(text="Partie terminée")
        else:
            elapsed   = int(asyncio.get_event_loop().time() - self.start_time)
            remaining = max(0, 180 - elapsed)
            embed.set_footer(text=f"⏳ Temps restant : {remaining} secondes")

        return embed

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

        game  = AnagrammeView(target_word, author_id=author_id, multi=multi)
        state = {"finished": False}

        embed = game.build_embed()

        # ── Callback de validation ──
        async def on_submit(interaction, answer):
            if state["finished"]:
                await safe_respond(interaction, "❌ La partie est terminée.", ephemeral=True)
                return

            if not game.multi and interaction.user.id != game.author_id:
                await safe_respond(interaction, "❌ Ce n'est pas ton jeu.", ephemeral=True)
                return

            guess = answer.strip().upper()

            if len(guess) != game.display_length:
                await safe_respond(
                    interaction,
                    f"❌ Le mot doit faire {game.display_length} lettres.",
                    ephemeral=True
                )
                return

            if Counter(guess) != Counter(game.target_word):
                await safe_respond(
                    interaction,
                    "❌ Ce mot n'utilise pas exactement les lettres proposées.",
                    ephemeral=True
                )
                return

            if not is_valid_word(guess):
                await safe_respond(
                    interaction,
                    f"❌ `{guess}` n'est pas un mot valide.",
                    ephemeral=True
                )
                return

            game.attempts.append({'word': guess, 'author': interaction.user.display_name})

            # ✅ Bonne réponse
            if normalize_text(guess) == normalize_text(game.target_word):
                state["finished"] = True
                game.finished = True
                game.winner = interaction.user.mention
                self.active_games.pop(channel.id, None)

                await safe_respond(interaction, "✅ Bonne réponse !", ephemeral=True)

                final_embed = game.build_embed()
                await view.mark_finished(embed=final_embed)

            # ❌ Mauvaise réponse
            else:
                await safe_respond(interaction, "❌ Ce n'est pas le bon mot !", ephemeral=True)

                # Vérification de la limite d'essais en Solo
                if not game.multi and len(game.attempts) >= game.max_attempts:
                    state["finished"] = True
                    game.finished = True
                    self.active_games.pop(channel.id, None)

                    final_embed = game.build_embed()
                    await view.mark_finished(embed=final_embed)
                else:
                    if game.message:
                        await safe_edit(game.message, embed=game.build_embed())

        # ── Création de la view ──
        if multi:
            async def on_buzz(user: discord.User | discord.Member):
                if view.message:
                    # 1. Griser les boutons de la view lors du buzz
                    for child in view.children:
                        if isinstance(child, discord.ui.Button):
                            child.disabled = True

                    # 2. Mise à jour du message avec la main prise dans le footer
                    current_embed = game.build_embed()
                    current_embed.set_footer(text=f"🎯 Main prise par {user.display_name}")

                    await safe_edit(view.message, embed=current_embed, view=view)

            view = BuzzerView(
                modal_title="✍️ Propose ton mot",
                modal_label="Mot",
                modal_placeholder=f"Mot de {game.display_length} lettres",
                modal_max_length=game.display_length,
                on_submit=on_submit,
                on_buzz=on_buzz,
                buzz_timeout=30,
                view_timeout=300,
            )
        else:
            view = ReplyView(
                user_id=author_id,
                modal_title="✍️ Propose ton mot",
                modal_label="Mot",
                modal_placeholder=f"Mot de {game.display_length} lettres",
                modal_max_length=game.display_length,
                on_submit=on_submit,
                timeout=300,
            )

        view.message = await safe_send(channel, embed=embed, view=view)
        if view.message is None:
            return
        game.message = view.message

        self.active_games[channel.id] = game

        # ── Attente (3 minutes) ──
        try:
            await asyncio.sleep(180)
        except asyncio.CancelledError:
            self.active_games.pop(channel.id, None)
            return

        if state["finished"]:
            return

        # ── Fin du temps ──
        game.finished = True
        self.active_games.pop(channel.id, None)
        final_embed = game.build_embed()
        await view.mark_finished(embed=final_embed)

    # ============================================================================
    # 🔹 Commande SLASH
    # ============================================================================
    @app_commands.command(name="anagramme", description="Lance une partie d'Anagramme (multi = tout le monde peut jouer)")
    @app_commands.describe(mode="Mode de jeu : solo ou multi")
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_anagramme(self, interaction: discord.Interaction, mode: str = "solo"):
        await interaction.response.defer()
        await self._start_game(interaction.channel, author_id=interaction.user.id, mode=mode)
        await interaction.delete_original_response()

    # ============================================================================
    # 🔹 Commande PREFIX
    # ============================================================================
    @commands.command(name="anagramme", help="Lance une partie d'Anagramme. anagramme multi ou m pour jouer en multi.")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
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
