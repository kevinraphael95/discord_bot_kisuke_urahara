# ================================================================================
# 📌 pressing_under_pressure.py
# Objectif : Mini-jeu troll style "The Impossible Quiz" - Rendu ultra-épuré
# Catégorie : Jeux
# Accès : Tous
# Cooldown : 1 utilisation / 10 secondes / utilisateur
# ================================================================================

# ================================================================================
# 📦 Imports nécessaires
# ================================================================================
import asyncio
import json
import logging
import os
import random
from typing import Any, Dict, List, Optional, Set, Tuple

import discord
from discord import app_commands
from discord.ext import commands

from utils.discord_utils import safe_edit, safe_respond, safe_send

log = logging.getLogger(__name__)

# ================================================================================
# 🎨 Constantes
# ================================================================================
DATA_JSON_PATH = os.path.join("data", "pressing_puzzles.json")
SCORES_JSON_PATH = os.path.join("data", "pressing_scores.json")

MAX_LIVES = 3
TOTAL_TIME_BASE = 12
COMBO_THRESHOLD = 3
MAX_PUZZLES = 10
TROLL_EVENT_PROB = 0.30

TROLL_EVENTS = [
    {"msg": "⚡ Fausse alerte ! Continue.", "effect": None},
    {"msg": "⚡ RÈGLES INVERSÉES : Fais l'opposé !", "effect": "invert"},
    {"msg": "⚡ DOUBLE COMPTEUR : Nombre de clics doublé !", "effect": "double"},
    {"msg": "⚡ SPEED RUN : Plus que 4 secondes !", "effect": "halve_time"},
    {"msg": "⚡ RESET : Remis à zéro !", "effect": "reset_presses"},
    {"msg": "⚡ MALUS : Erreur = -2 vies !", "effect": "double_penalty"},
]

PHASE_COLORS = {
    "playing": discord.Color.blurple(),
    "success": discord.Color.green(),
    "fail": discord.Color.red(),
    "end_win": discord.Color.gold(),
    "end_lose": discord.Color.dark_red(),
    "intro": discord.Color.blurple(),
}


# ================================================================================
# 💾 Données & Scores
# ================================================================================
def load_scores() -> Dict[str, Any]:
    try:
        if os.path.exists(SCORES_JSON_PATH):
            with open(SCORES_JSON_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        log.error("[PUP] Erreur lecture scores : %s", e)
    return {}


def save_scores(data: Dict[str, Any]) -> None:
    try:
        os.makedirs(os.path.dirname(SCORES_JSON_PATH), exist_ok=True)
        with open(SCORES_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log.error("[PUP] Erreur sauvegarde scores : %s", e)


def update_score(user_id: int, username: str, puzzles_done: int, won: bool) -> None:
    scores = load_scores()
    uid = str(user_id)
    entry = scores.get(
        uid,
        {"username": username, "games": 0, "wins": 0, "best": 0, "total_puzzles": 0},
    )

    entry["username"] = username
    entry["games"] += 1
    if won:
        entry["wins"] += 1
    entry["total_puzzles"] += puzzles_done
    if puzzles_done > entry.get("best", 0):
        entry["best"] = puzzles_done

    scores[uid] = entry
    save_scores(scores)


def load_puzzles() -> List[Dict[str, Any]]:
    try:
        if os.path.exists(DATA_JSON_PATH):
            with open(DATA_JSON_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        log.error("[PUP] Erreur chargement énigmes : %s", e)
    return []


# ================================================================================
# 🧩 State & View
# ================================================================================
class PuzzleState:
    def __init__(self, puzzle: Dict[str, Any], total_time: int):
        self.puzzle = puzzle
        self.press_count = 0
        self.total_time = total_time
        self.remaining = total_time
        self.effect: Optional[str] = None
        self.double_penalty = False
        self.troll_fired = False
        self.troll_msg: Optional[str] = None

    def apply_troll(self, troll: Dict[str, Any]) -> None:
        self.troll_msg = troll["msg"]
        self.troll_fired = True
        effect = troll.get("effect")

        if effect == "halve_time":
            self.remaining = min(self.remaining, 4)
        elif effect == "double":
            self.effect = "double"
        elif effect == "invert":
            self.effect = "invert"
        elif effect == "reset_presses":
            self.effect = "reset_presses"
            self.press_count = 0
        elif effect == "double_penalty":
            self.double_penalty = True


class PressView(discord.ui.View):
    def __init__(self, user: discord.User | discord.Member):
        super().__init__(timeout=None)
        self.user = user
        self.state: Optional[PuzzleState] = None

    def bind(self, state: PuzzleState) -> None:
        self.state = state
        self._set_disabled(False)

    def lock(self) -> None:
        self._set_disabled(True)

    def _set_disabled(self, disabled: bool) -> None:
        for child in self.children:
            child.disabled = disabled  # type: ignore

    @discord.ui.button(label="CLIC !", style=discord.ButtonStyle.primary)
    async def press(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "❌ Pas ta partie !", ephemeral=True
            )
            return

        if self.state is None:
            await interaction.response.defer()
            return

        if self.state.effect == "reset_presses":
            self.state.press_count = 0
            self.state.effect = None

        self.state.press_count += 1
        await interaction.response.defer()


# ================================================================================
# 🧠 Cog Principal
# ================================================================================
class PressingUnderPressure(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.sessions: Set[int] = set()

    @staticmethod
    def _timer_bar(total: int, remaining: int) -> str:
        return "🟩" * max(0, remaining) + "⬛" * max(0, total - remaining)

    @staticmethod
    def _lives_bar(lives: int) -> str:
        return "❤️" * max(0, lives) + "🖤" * max(0, MAX_LIVES - lives)

    @staticmethod
    def _evaluate(state: PuzzleState) -> bool:
        ptype = state.puzzle.get("type", "")
        presses = state.press_count
        req = state.puzzle.get("value", 0)
        effect = state.effect

        if effect == "invert":
            if ptype in ("multi_click", "click_once", "wait_then_click", "click_any"):
                return presses == 0
            if ptype in ("no_click", "no_click_time"):
                return presses >= 1

        if effect == "double" and ptype in ("multi_click", "click_once", "wait_then_click"):
            req *= 2

        match ptype:
            case "multi_click" | "click_once":
                return presses == req
            case "wait_then_click" | "timed_click":
                return presses == 1
            case "no_click" | "no_click_time":
                return presses == 0
            case "click_any":
                return presses >= 1
            case "click_if_true":
                return (presses >= 1) == bool(state.puzzle.get("value", True))
            case "logic_invert":
                return presses == 0
            case _:
                return random.choice([True, False])

    @staticmethod
    def _instruction(puzzle: Dict[str, Any]) -> str:
        ptype = puzzle.get("type", "")
        req = puzzle.get("value", 0)

        match ptype:
            case "multi_click":
                return f"Appuie **{req}** fois."
            case "click_once":
                return "Appuie **1** seule fois."
            case "wait_then_click":
                return f"Attends **{req}s** puis appuie **1** fois."
            case "no_click" | "no_click_time":
                return "🎯 **NE TOUCHE À RIEN !**"
            case "click_any":
                return "Appuie au moins **1** fois."
            case "click_if_true":
                return "Appuie **uniquement si la phrase est vraie**."
            case "logic_invert":
                return "Fais le **contraire** de ce qui est demandé."
            case "timed_click":
                target = puzzle.get("time_target", "?")
                return f"Appuie à exactement **{target}** blocs verts."
            case _:
                return "Fais un choix."

    def _build_embed(
        self,
        state: PuzzleState,
        lives: int,
        combo: int,
        puzzle_num: int,
        total_puzzles: int,
        phase: str = "playing",
        result_msg: str = "",
    ) -> discord.Embed:
        p = state.puzzle

        if phase in ("playing", "success", "fail"):
            troll_line = f"\n\n{state.troll_msg}" if state.troll_msg else ""
            combo_str = f" | 🔥 x{combo}" if combo >= COMBO_THRESHOLD else ""

            desc = (
                f"**{p.get('question', '')}**\n"
                f"👉 {self._instruction(p)}{troll_line}\n\n"
                f"⏳ {self._timer_bar(state.total_time, state.remaining if phase == 'playing' else 0)}\n"
                f"📊 Énigme **{puzzle_num}/{total_puzzles}** | Clics: **{state.press_count}** | {self._lives_bar(lives)}{combo_str}"
            )

            if phase != "playing":
                desc += f"\n\n{'✅' if phase == 'success' else '❌'} **{result_msg}**"
        else:
            desc = result_msg

        return discord.Embed(
            description=desc,
            color=PHASE_COLORS.get(phase, discord.Color.blurple()),
        )

    # --- Énigme unique ---
    async def _run_puzzle(
        self,
        msg: discord.Message,
        view: PressView,
        base_puzzle: Dict[str, Any],
        lives: int,
        combo: int,
        puzzle_num: int,
        total_puzzles: int,
    ) -> Tuple[int, int]:
        total_time = max(5, TOTAL_TIME_BASE - (combo // COMBO_THRESHOLD))
        state = PuzzleState(base_puzzle, total_time)
        view.bind(state)

        async def refresh(phase: str = "playing", result_msg: str = "") -> None:
            embed = self._build_embed(
                state, lives, combo, puzzle_num, total_puzzles, phase, result_msg
            )
            await safe_edit(msg, embed=embed, view=view)

        await refresh()

        while state.remaining > 0:
            await asyncio.sleep(1)
            state.remaining -= 1

            if (
                not state.troll_fired
                and 3 <= state.remaining <= 8
                and random.random() < TROLL_EVENT_PROB
            ):
                state.apply_troll(random.choice(TROLL_EVENTS))

            await refresh()

        view.lock()
        success = self._evaluate(state)

        if success:
            combo += 1
            result_msg = f"Validé ({state.press_count} clics)"
            phase = "success"
        else:
            penalty = 2 if state.double_penalty else 1
            lives -= penalty
            combo = 0
            phase = "fail"
            result_msg = f"Raté ({state.press_count} clics)"

        await refresh(phase, result_msg)
        await asyncio.sleep(1.5)
        return lives, combo

    # --- Partie complète ---
    async def _run_full_game(
        self,
        channel: discord.abc.Messageable,
        user: discord.User | discord.Member,
    ) -> None:
        if user.id in self.sessions:
            await safe_send(channel, "⏳ Partie déjà en cours !", delete_after=3)
            return

        puzzles_all = load_puzzles()
        if not puzzles_all:
            await safe_send(channel, "❌ Énigmes introuvables.")
            return

        self.sessions.add(user.id)

        try:
            puzzles = random.sample(puzzles_all, min(MAX_PUZZLES, len(puzzles_all)))
            lives = MAX_LIVES
            combo = 0
            total_puzzles = len(puzzles)

            view = PressView(user)
            view.lock()

            intro_embed = discord.Embed(
                description=(
                    f"🎮 **Pressing Under Pressure**\n\n"
                    f"Joueur: **{user.display_name}**\n"
                    f"Objectif: **{total_puzzles} énigmes**\n\n"
                    f"⏱️ Lancement dans **3 secondes**..."
                ),
                color=PHASE_COLORS["intro"],
            )

            msg = await safe_send(channel, embed=intro_embed, view=view)
            if msg is None:
                return

            await asyncio.sleep(3)

            puzzles_done = 0
            for i, puzzle in enumerate(puzzles, start=1):
                lives, combo = await self._run_puzzle(
                    msg, view, puzzle, lives, combo, i, total_puzzles
                )
                puzzles_done += 1
                if lives <= 0:
                    break

            won = lives > 0 and puzzles_done == total_puzzles
            update_score(user.id, user.display_name, puzzles_done, won)
            view.lock()

            if won:
                end_desc = (
                    f"🏆 **VICTOIRE !**\n\n"
                    f"**{user.display_name}** a réussi les **{total_puzzles}** énigmes !\n"
                    f"Vies restantes : {self._lives_bar(lives)}"
                )
                phase = "end_win"
            else:
                end_desc = (
                    f"💀 **GAME OVER**\n\n"
                    f"Échec à l'énigme **{puzzles_done}/{total_puzzles}**.\n"
                    f"Score final : **{max(0, puzzles_done - 1)}** réussie(s)."
                )
                phase = "end_lose"

            dummy = PuzzleState({}, 0)
            end_embed = self._build_embed(
                dummy,
                max(0, lives),
                combo,
                puzzles_done,
                total_puzzles,
                phase=phase,
                result_msg=end_desc,
            )
            await safe_edit(msg, embed=end_embed, view=view)

        except Exception as e:
            log.error("[PUP] Erreur : %s", e, exc_info=True)
            await safe_send(channel, "❌ Erreur durant la partie.")
        finally:
            self.sessions.discard(user.id)

    # --- Leaderboard ---
    async def _send_leaderboard(
        self, channel: discord.abc.Messageable
    ) -> None:
        scores = load_scores()
        if not scores:
            await safe_send(channel, "📭 Aucun score.")
            return

        ranked = sorted(
            scores.values(),
            key=lambda x: (x.get("wins", 0), x.get("best", 0)),
            reverse=True,
        )[:10]

        medals = ["🥇", "🥈", "🥉"] + ["🔹"] * 7
        lines = [
            f"{medals[i]} **{e['username']}** — {e.get('wins', 0)} Wins (Max: {e.get('best', 0)})"
            for i, e in enumerate(ranked)
        ]

        embed = discord.Embed(
            title="🏆 Classement",
            description="\n".join(lines),
            color=discord.Color.gold(),
        )
        await safe_send(channel, embed=embed)

    # --- Commandes ---
    @app_commands.command(
        name="pressing", description="Jeu Pressing Under Pressure"
    )
    @app_commands.describe(action="Jouer ou Voir le classement")
    @app_commands.choices(
        action=[
            app_commands.Choice(name="Jouer", value="play"),
            app_commands.Choice(name="Classement", value="top"),
        ]
    )
    @app_commands.checks.cooldown(1, 10.0, key=lambda i: i.user.id)
    async def slash_pressing(
        self,
        interaction: discord.Interaction,
        action: Optional[app_commands.Choice[str]] = None,
    ):
        await interaction.response.defer()
        if action and action.value == "top":
            await self._send_leaderboard(interaction.channel)
        else:
            await self._run_full_game(interaction.channel, interaction.user)

    @commands.command(name="pressing", aliases=["pup"])
    @commands.cooldown(1, 10.0, commands.BucketType.user)
    async def prefix_pressing(self, ctx: commands.Context):
        await self._run_full_game(ctx.channel, ctx.author)

    @commands.command(name="pressingtop", aliases=["puptop"])
    @commands.cooldown(1, 10.0, commands.BucketType.user)
    async def prefix_pressing_top(self, ctx: commands.Context):
        await self._send_leaderboard(ctx.channel)


# ================================================================================
# 🔌 Setup
# ================================================================================
async def setup(bot: commands.Bot):
    cog = PressingUnderPressure(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Jeux"
    await bot.add_cog(cog)
