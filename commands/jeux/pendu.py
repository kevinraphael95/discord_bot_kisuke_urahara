# ================================================================================
# 📌 pendu.py — Commande interactive /pendu et !pendu
# Objectif : Jeu du pendu interactif avec embed, tentatives limitées et feedback
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

from utils.discord_utils import safe_edit, safe_send
from utils.jeux_utils import BuzzerView, ReplyView, normalize_text, parse_mode

log = logging.getLogger(__name__)

# ================================================================================
# 🎨 Constantes et ASCII
# ================================================================================
PENDU_ASCII = [
    "`      \n      \n      \n      \n      \n=========`",
    "`      +---+\n     |   |\n         |\n         |\n         |\n=========`",
    "`      +---+\n     |   |\n     O   |\n         |\n         |\n=========`",
    "`      +---+\n     |   |\n     O   |\n     |   |\n         |\n=========`",
    "`      +---+\n     |   |\n     O   |\n    /|   |\n         |\n=========`",
    "`      +---+\n     |   |\n     O   |\n    /|\\  |\n         |\n=========`",
    "`      +---+\n     |   |\n     O   |\n    /    |\n=========`",
    "`      +---+\n     |   |\n     O   |\n    /|\\  |\n    / \\  |\n=========`",
]
MAX_ERREURS = 7

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
        log.exception("[pendu] Erreur API : %s", e)
    return "PYTHON"

# ================================================================================
# 🎮 Vue principale du jeu
# ================================================================================
class PenduView:
    """Classe représentant une partie du Pendu"""

    def __init__(self, target_word: str, author_id: int | None = None, multi: bool = False):
        normalized = target_word.replace("Œ", "OE").replace("œ", "oe")
        self.target_word       = normalized.upper()
        self.trouve            = set()
        self.rate              = set()
        self.author_id         = author_id
        self.multi             = multi
        self.max_erreurs       = MAX_ERREURS
        self.attempts: list[dict] = []
        self.message           = None
        self.finished          = False
        self.winner: str | None = None
        self.last_error: str | None = None
        self.start_time        = asyncio.get_event_loop().time()

    def get_display_word(self) -> str:
        return " ".join([l if l in self.trouve else "_" for l in self.target_word])

    def get_pendu_ascii(self) -> str:
        idx = min(len(self.rate), len(PENDU_ASCII) - 1)
        return PENDU_ASCII[idx]

    def get_lettres_tentees(self) -> str:
        lettres = sorted(self.trouve | self.rate)
        return ", ".join(lettres) if lettres else "Aucune"

    def build_embed(self) -> discord.Embed:
        mode_text = "Solo 🧍‍♂️" if not self.multi else "Multi 🌍"
        embed = discord.Embed(
            title=f"🕹️ Jeu du Pendu - {mode_text}",
            description=f"# ➡️ `{self.get_display_word()}`\n```\n{self.get_pendu_ascii()}\n```",
            color=discord.Color.orange()
        )

        if self.multi:
            instructions = (
                "💡 **Comment jouer en mode Multi :**\n"
                "1️⃣ Clique sur **🔔 Buzzer** pour prendre la main.\n"
                "2️⃣ Propose une **lettre** ou le **mot complet**.\n"
                f"3️⃣ Vous avez droit à **{self.max_erreurs} erreurs** au total.\n"
                "4️⃣ La partie se termine après 3 minutes ou quand le mot est trouvé."
            )
        else:
            instructions = (
                "💡 **Comment jouer en mode Solo :**\n"
                "1️⃣ Clique sur **✍️ Répondre** pour proposer ta réponse.\n"
                "2️⃣ Propose une **lettre** ou le **mot complet**.\n"
                f"3️⃣ Vous avez droit à **{self.max_erreurs} erreurs** au total.\n"
                "4️⃣ La partie se termine après 3 minutes ou quand le mot est trouvé."
            )

        embed.add_field(name="📝 Instructions", value=instructions, inline=False)
        embed.add_field(name="Erreurs", value=f"`{len(self.rate)} / {self.max_erreurs}`", inline=True)
        embed.add_field(name="Lettres tentées", value=f"`{self.get_lettres_tentees()}`", inline=True)

        if self.attempts:
            lines = []
            for entry in self.attempts[-5:]:
                status = "✅" if entry.get('correct') else "❌"
                lines.append(f"{entry['author']}: **{entry['word']}** {status}")
            tries_text = "\n".join(lines)
            embed.add_field(name="Essais", value=tries_text, inline=False)
        else:
            embed.add_field(name="Essais", value="*(Aucun essai pour l'instant)*", inline=False)

        if self.last_error and not self.finished:
            embed.add_field(name="⚠️ Remarque", value=self.last_error, inline=False)

        if self.finished:
            if self.winner:
                embed.title = "🕹️ Jeu du Pendu - Gagné !"
                embed.color = discord.Color.green()
                embed.description = f"# ➡️ `{self.target_word}`\n```\n{self.get_pendu_ascii()}\n```\n🏆 **{self.winner}** a trouvé !"
            else:
                embed.title = "🕹️ Jeu du Pendu - Perdu"
                embed.color = discord.Color.red()
                embed.description = f"# ➡️ `{self.target_word}`\n```\n{self.get_pendu_ascii()}\n```\n💀 Pendu !"
            embed.set_footer(text="Partie terminée")
        else:
            elapsed   = int(asyncio.get_event_loop().time() - self.start_time)
            remaining = max(0, 180 - elapsed)
            embed.set_footer(text=f"⏳ Temps restant : {remaining} secondes")

        return embed

# ================================================================================
# 🧠 Cog principal
# ================================================================================
class Pendu(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot          = bot
        self.active_games: dict[int, PenduView] = {}

    async def _start_game(self, channel: discord.abc.Messageable, author_id: int, mode: str = "solo"):
        length      = random.choice(range(5, 9))
        target_word = await get_random_french_word(length=length)
        multi       = parse_mode(mode)

        game  = PenduView(target_word, author_id=author_id, multi=multi)
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
            game.last_error = None

            if not guess:
                return

            # Proposition d'une seule lettre
            if len(guess) == 1:
                if guess in game.trouve or guess in game.rate:
                    game.last_error = f"La lettre `{guess}` a déjà été proposée !"
                    if game.message:
                        await safe_edit(game.message, embed=game.build_embed())
                    return

                if guess in game.target_word:
                    game.trouve.add(guess)
                    is_correct = True
                else:
                    game.rate.add(guess)
                    is_correct = False

                game.attempts.append({
                    'word': guess,
                    'author': interaction.user.display_name,
                    'correct': is_correct
                })

            # Proposition du mot entier
            else:
                is_correct = (normalize_text(guess) == normalize_text(game.target_word))
                game.attempts.append({
                    'word': guess,
                    'author': interaction.user.display_name,
                    'correct': is_correct
                })
                if is_correct:
                    for l in game.target_word:
                        game.trouve.add(l)
                else:
                    game.rate.add(f"MOT:{guess}")

            # Vérification victoire
            if all(l in game.trouve for l in set(game.target_word)):
                state["finished"] = True
                game.finished = True
                game.winner = interaction.user.mention
                self.active_games.pop(channel.id, None)

                final_embed = game.build_embed()
                await view.mark_finished(embed=final_embed)
                return

            # Vérification défaite (erreurs dépassées)
            if len(game.rate) >= game.max_erreurs:
                state["finished"] = True
                game.finished = True
                self.active_games.pop(channel.id, None)

                final_embed = game.build_embed()
                await view.mark_finished(embed=final_embed)
                return

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
                modal_title="✍️ Propose une lettre ou le mot",
                modal_label="Lettre ou Mot",
                modal_placeholder="Exemple: A ou PYTHON",
                modal_max_length=30,
                on_submit=on_submit,
                on_buzz=on_buzz,
                buzz_timeout=30,
                view_timeout=300,
            )
        else:
            view = ReplyView(
                user_id=author_id,
                modal_title="✍️ Propose une lettre ou le mot",
                modal_label="Lettre ou Mot",
                modal_placeholder="Exemple: A ou PYTHON",
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
    @app_commands.command(name="pendu", description="Lance une partie du Pendu (multi = tout le monde peut jouer)")
    @app_commands.describe(mode="Mode de jeu : solo ou multi")
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_pendu(self, interaction: discord.Interaction, mode: str = "solo"):
        await interaction.response.defer()
        await self._start_game(interaction.channel, author_id=interaction.user.id, mode=mode)
        await interaction.delete_original_response()

    # ============================================================================
    # 🔹 Commande PREFIX
    # ============================================================================
    @commands.command(name="pendu", help="Lance une partie du Pendu. pendu multi ou m pour jouer en multi.")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_pendu(self, ctx: commands.Context, mode: str = "solo"):
        await self._start_game(ctx.channel, author_id=ctx.author.id, mode=mode)

# ================================================================================
# 🔌 Setup du Cog
# ================================================================================
async def setup(bot: commands.Bot):
    cog = Pendu(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Jeux"
    await bot.add_cog(cog)
