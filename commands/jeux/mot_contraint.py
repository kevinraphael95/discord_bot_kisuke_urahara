# ================================================================================
# 📌 mot_contraint.py — Commande interactive /mot_contraint et !mot_contraint
# Objectif : Jeu du mot contraint avec embed, tentatives limitées et feedback
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

import discord
from discord import app_commands
from discord.ext import commands
from spellchecker import SpellChecker

from utils.discord_utils import safe_edit, safe_send
from utils.jeux_utils import BuzzerView, ReplyView, normalize_text, parse_mode

log = logging.getLogger(__name__)

# ================================================================================
# 🌐 Initialisation du spellchecker français
# ================================================================================
spell = SpellChecker(language="fr")

DICTIONARY_WORDS = [
    w for w in spell.word_frequency.dictionary.keys()
    if len(w) >= 2 and w.isalpha()
]

def get_random_letter_pair() -> tuple[str, str]:
    """Tire un mot aléatoire existant et extrait sa première et dernière lettre."""
    word = random.choice(DICTIONARY_WORDS)
    return word[0].upper(), word[-1].upper()

def is_valid_word(word: str) -> bool:
    """Vérifie si le mot existe dans le dictionnaire français"""
    return word.lower() in spell.word_frequency

# ================================================================================
# 🎮 Vue principale du jeu
# ================================================================================
class MotContraintView:
    """Classe représentant une partie de Mot Contraint"""

    def __init__(self, start_letter: str, end_letter: str, author_id: int | None = None, multi: bool = False):
        self.start_letter      = start_letter
        self.end_letter        = end_letter
        self.author_id         = author_id
        self.multi             = multi
        self.rounds            = 1
        self.max_rounds        = 10 if multi else 1
        self.attempts: list[dict] = []
        self.scores: dict[str, int] = {}
        self.message           = None
        self.finished          = False
        self.winner: str | None = None
        self.last_error: str | None = None
        self.start_time        = asyncio.get_event_loop().time()

    def build_embed(self) -> discord.Embed:
        mode_text = "Solo 🧍‍♂️" if not self.multi else "Multi 🌍"
        embed = discord.Embed(
            title=f"🎯 Mots Contraints - {mode_text}",
            description=(
                f"# ➡️ `{self.start_letter}` _ _ _ `{self.end_letter}`\n\n"
                f"Trouvez un mot commençant par **`{self.start_letter}`** et se terminant par **`{self.end_letter}`** !"
            ),
            color=discord.Color.orange()
        )

        if self.multi:
            instructions = (
                "💡 **Comment jouer en mode Multi :**\n"
                "1️⃣ Clique sur **🔔 Buzzer** pour prendre la main.\n"
                "2️⃣ Le plus rapide ouvre une fenêtre pour proposer un mot.\n"
                f"3️⃣ Le mot doit commencer par `{self.start_letter}` et finir par `{self.end_letter}`.\n"
                f"4️⃣ Partie en **{self.max_rounds} manches**.\n"
                "5️⃣ La partie se termine après 3 minutes ou à la fin des manches."
            )
        else:
            instructions = (
                "💡 **Comment jouer en mode Solo :**\n"
                "1️⃣ Clique sur **✍️ Répondre** pour proposer ta réponse.\n"
                f"2️⃣ Le mot doit commencer par `{self.start_letter}` et finir par `{self.end_letter}`.\n"
                "3️⃣ La partie se termine dès que tu trouves un mot valide ou après 3 minutes."
            )

        embed.add_field(name="📝 Instructions", value=instructions, inline=False)

        if self.attempts:
            lines = []
            for entry in self.attempts[-5:]:
                status = "✅" if entry.get("correct") else "❌"
                lines.append(f"{entry['author']}: **{entry['word']}** {status}")
            tries_text = "\n".join(lines)
            field_name = f"Essais ({len(self.attempts)})"
            embed.add_field(name=field_name, value=tries_text, inline=False)
        else:
            embed.add_field(name="Essais", value="*(Aucun essai pour l'instant)*", inline=False)

        if self.scores and self.multi:
            sorted_scores = sorted(self.scores.items(), key=lambda x: x[1], reverse=True)
            leaderboard = "\n".join([f"- **{name}**: {pts}" for name, pts in sorted_scores])
            embed.add_field(name="🏆 Classement Actuel (Points)", value=leaderboard, inline=False)

        if self.last_error and not self.finished:
            embed.add_field(name="⚠️ Remarque", value=self.last_error, inline=False)

        if self.finished:
            if self.scores:
                sorted_scores = sorted(self.scores.items(), key=lambda x: x[1], reverse=True)
                top_name, top_score = sorted_scores[0]
                embed.title = "🎯 Mots Contraints - Gagné !"
                embed.color = discord.Color.green()
                embed.description = f"🎉 Victoire de **{top_name}** avec **{top_score} point(s)** !"
            else:
                embed.title = "🎯 Mots Contraints - Terminé"
                embed.color = discord.Color.red()
                embed.description = "❌ Fin de la partie, aucun point n'a été marqué."
            embed.set_footer(text="Partie terminée")
        else:
            elapsed   = int(asyncio.get_event_loop().time() - self.start_time)
            remaining = max(0, 180 - elapsed)
            embed.set_footer(text=f"⏳ Temps restant : {remaining} secondes")

        return embed

# ================================================================================
# 🧠 Cog principal
# ================================================================================
class MotContraint(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot          = bot
        self.active_games: dict[int, MotContraintView] = {}

    async def _start_game(self, channel: discord.abc.Messageable, author_id: int, mode: str = "solo"):
        start, end = get_random_letter_pair()
        multi      = parse_mode(mode)

        game  = MotContraintView(start, end, author_id=author_id, multi=multi)
        state = {"finished": False}

        embed = game.build_embed()

        # ── Callback de validation ──
        async def on_submit(interaction: discord.Interaction, answer: str):
            if not interaction.response.is_done():
                await interaction.response.defer()

            if state["finished"]:
                return

            if not game.multi and interaction.user.id != game.author_id:
                return

            guess = answer.strip().upper()
            word_clean = guess.lower()
            author_name = interaction.user.display_name
            game.last_error = None

            if not guess:
                return

            # Vérification si le mot a déjà été proposé
            if any(normalize_text(entry['word']) == normalize_text(guess) for entry in game.attempts):
                game.last_error = f"Le mot `{guess}` a déjà été proposé !"
                if game.message:
                    await safe_edit(game.message, embed=game.build_embed())
                return

            # Vérification des règles
            if not word_clean.startswith(game.start_letter.lower()):
                game.last_error = f"Le mot doit commencer par `{game.start_letter}`."
                game.attempts.append({'word': guess, 'author': author_name, 'correct': False})
            elif not word_clean.endswith(game.end_letter.lower()):
                game.last_error = f"Le mot doit se terminer par `{game.end_letter}`."
                game.attempts.append({'word': guess, 'author': author_name, 'correct': False})
            elif not is_valid_word(word_clean):
                game.last_error = f"`{guess}` n'est pas un mot reconnu du dictionnaire."
                game.attempts.append({'word': guess, 'author': author_name, 'correct': False})
            else:
                # ✅ Mot valide !
                game.attempts.append({'word': guess, 'author': author_name, 'correct': True})
                game.scores[author_name] = game.scores.get(author_name, 0) + 1

                game.rounds += 1
                if game.rounds > game.max_rounds:
                    state["finished"] = True
                    game.finished = True
                    self.active_games.pop(channel.id, None)

                    final_embed = game.build_embed()
                    await view.mark_finished(embed=final_embed)
                    return
                else:
                    # Manche suivante
                    game.start_letter, game.end_letter = get_random_letter_pair()
                    game.attempts.clear()

            if game.message:
                await safe_edit(game.message, embed=game.build_embed())

        # ── Création de la view ──
        if multi:
            async def on_buzz(user: discord.User | discord.Member):
                if view.message:
                    for child in view.children:
                        if isinstance(child, discord.ui.Button):
                            child.disabled = True

                    current_embed = game.build_embed()
                    current_embed.set_footer(text=f"🎯 Main prise par {user.display_name}")

                    await safe_edit(view.message, embed=current_embed, view=view)

            view = BuzzerView(
                modal_title="✍️ Propose ton mot",
                modal_label="Mot",
                modal_placeholder=f"Mot commençant par {game.start_letter} et finissant par {game.end_letter}",
                modal_max_length=30,
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
                modal_placeholder=f"Mot commençant par {game.start_letter} et finissant par {game.end_letter}",
                modal_max_length=30,
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
    @app_commands.command(name="mot_contraint", description="Trouve un mot commençant et finissant par les lettres données.")
    @app_commands.describe(mode="Mode de jeu : solo ou multi")
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_mot_contraint(self, interaction: discord.Interaction, mode: str = "solo"):
        await interaction.response.defer()
        await self._start_game(interaction.channel, author_id=interaction.user.id, mode=mode)
        await interaction.delete_original_response()

    # ============================================================================
    # 🔹 Commande PREFIX
    # ============================================================================
    @commands.command(name="mot_contraint", aliases=["mc"], help="Jeu du mot contraint. mot_contraint multi ou m pour jouer en multi.")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_mot_contraint(self, ctx: commands.Context, mode: str = "solo"):
        await self._start_game(ctx.channel, author_id=ctx.author.id, mode=mode)

# ================================================================================
# 🔌 Setup du Cog
# ================================================================================
async def setup(bot: commands.Bot):
    cog = MotContraint(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Jeux"
    await bot.add_cog(cog)
