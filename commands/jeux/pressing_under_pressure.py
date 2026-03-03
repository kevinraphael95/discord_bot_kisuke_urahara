# ────────────────────────────────────────────────────────────────────────────────
# 📌 pressing_under_pressure.py
# Objectif : Mini-jeu troll inspiré de The Impossible Quiz. Énigmes aléatoires
#            avec timer live, vies, streaks, combo, troll events, classement.
#            Toute la partie se joue dans UN SEUL message édité en continu.
# Catégorie : Jeux
# Accès : Tous
# Cooldown : 1 utilisation / 10 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
import json
import random
import asyncio
import os
import logging

from utils.discord_utils import safe_send, safe_edit, safe_respond

log = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────────────────────────
# 🎨 Constantes
# ────────────────────────────────────────────────────────────────────────────────
DATA_JSON_PATH   = os.path.join("data", "pressing_puzzles.json")
SCORES_JSON_PATH = os.path.join("data", "pressing_scores.json")

MAX_LIVES        = 3
TOTAL_TIME_BASE  = 12    # secondes de base par énigme
COMBO_THRESHOLD  = 3     # succès consécutifs pour accélérer le timer
MAX_PUZZLES      = 10
TROLL_EVENT_PROB = 0.30  # probabilité d'un troll event (fenêtre 3–8s restantes)

TROLL_SUFFIXES = [
    " *(tu crois être prêt ?)*",
    " *(j'espère que tu lis bien…)*",
    " *(ne rate pas ça.)*",
    " *(facile… ou pas.)*",
    " *(je te surveille 👀)*",
    " *(réfléchis bien avant d'agir.)*",
    " *(ou alors… fais le contraire ?)*",
    " *(ha. bonne chance.)*",
    " *(la réponse est évidente. Enfin… presque.)*",
    " *(lis jusqu'au bout avant d'agir.)*",
    " *(ou peut-être que non.)*",
]

TROLL_EVENTS = [
    {"msg": "⚠️ **FAUSSE ALERTE.** Il ne se passe rien. Continue.",            "effect": None},
    {"msg": "🔀 **LES RÈGLES ONT CHANGÉ.** Fais exactement le contraire.",     "effect": "invert"},
    {"msg": "😴 **Rien à voir ici.** Passe ton chemin… ou pas.",               "effect": None},
    {"msg": "💥 **DOUBLE OU RIEN.** Le nombre de pressions requis a doublé.",  "effect": "double"},
    {"msg": "🎲 **CHANCE !** La réponse est maintenant complètement aléatoire.","effect": "random"},
    {"msg": "⏩ **SPEED RUN !** Tu n'as plus que 4 secondes.",                  "effect": "halve_time"},
    {"msg": "🔁 **RESET !** Ton compteur de pressions vient d'être remis à zéro.", "effect": "reset_presses"},
    {"msg": "🙈 **DISTRACTION.** Ne lis pas ceci. Concentre-toi.",             "effect": None},
    {"msg": "📉 **MALUS.** Tu perdras 2 vies si tu te trompes maintenant.",    "effect": "double_penalty"},
]

# Couleurs par phase (centralisées)
PHASE_COLORS = {
    "playing":  discord.Color.orange(),
    "success":  discord.Color.green(),
    "fail":     discord.Color.red(),
    "end_win":  discord.Color.gold(),
    "end_lose": discord.Color.dark_red(),
    "intro":    discord.Color.blurple(),
}

# ────────────────────────────────────────────────────────────────────────────────
# 💾 Scores persistants
# ────────────────────────────────────────────────────────────────────────────────
def load_scores() -> dict:
    try:
        with open(SCORES_JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_scores(data: dict) -> None:
    os.makedirs(os.path.dirname(SCORES_JSON_PATH), exist_ok=True)
    with open(SCORES_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def update_score(user_id: int, username: str, puzzles_done: int, won: bool) -> None:
    scores = load_scores()
    uid    = str(user_id)
    entry  = scores.get(uid, {
        "username": username, "games": 0, "wins": 0, "best": 0, "total_puzzles": 0,
    })
    entry["username"]       = username
    entry["games"]         += 1
    if won:
        entry["wins"]      += 1
    entry["total_puzzles"] += puzzles_done
    if puzzles_done > entry.get("best", 0):
        entry["best"]       = puzzles_done
    scores[uid] = entry
    save_scores(scores)

# ────────────────────────────────────────────────────────────────────────────────
# 📂 Chargement des énigmes
# ────────────────────────────────────────────────────────────────────────────────
def load_puzzles() -> list:
    try:
        with open(DATA_JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        log.warning("[PUP] Fichier %s introuvable.", DATA_JSON_PATH)
        return []
    except json.JSONDecodeError as e:
        log.error("[PUP] JSON invalide : %s", e)
        return []

# ────────────────────────────────────────────────────────────────────────────────
# 🧩 PuzzleState — état d'une énigme en cours
# ────────────────────────────────────────────────────────────────────────────────
class PuzzleState:
    """Encapsule toute la logique mutable d'une énigme."""

    def __init__(self, puzzle: dict, total_time: int):
        self.puzzle         = puzzle
        self.press_count    = 0
        self.total_time     = total_time
        self.remaining      = total_time
        self.effect: str | None = None
        self.double_penalty = False
        self.troll_fired    = False
        self.troll_msg: str | None = None

    def apply_troll(self, troll: dict) -> None:
        """Applique un troll event sur l'état courant."""
        self.troll_msg   = troll["msg"]
        self.troll_fired = True
        effect           = troll.get("effect")

        match effect:
            case "halve_time":    self.remaining = min(self.remaining, 4)
            case "double":        self.effect = "double"
            case "invert":        self.effect = "invert"
            case "random":
                self.effect = "random"
                self.puzzle = {**self.puzzle, "type": "random"}
            case "reset_presses": self.effect = "reset_presses"
            case "double_penalty": self.double_penalty = True
            case _:               pass   # fausse alerte / distraction

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ Vue — bouton unique, recyclé pour toute la partie
# ────────────────────────────────────────────────────────────────────────────────
class PressView(discord.ui.View):
    """Vue réutilisée pour toute la partie. On rebind l'état à chaque énigme."""

    def __init__(self, user: discord.User | discord.Member):
        super().__init__(timeout=None)
        self.user  = user
        self.state: PuzzleState | None = None

    def bind(self, state: PuzzleState) -> None:
        self.state = state
        self._set_disabled(False)

    def lock(self) -> None:
        self._set_disabled(True)

    def _set_disabled(self, value: bool) -> None:
        for child in self.children:
            child.disabled = value  # type: ignore

    @discord.ui.button(label="Appuie ici !", style=discord.ButtonStyle.green, emoji="👆")
    async def press(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("❌ Ce n'est pas ta partie !", ephemeral=True)
            return

        s = self.state
        if s is None:
            await interaction.response.defer()
            return

        # reset_presses : consomme l'effet au premier clic
        if s.effect == "reset_presses":
            s.press_count = 0
            s.effect      = None

        s.press_count += 1
        await interaction.response.defer()

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class PressingUnderPressure(commands.Cog):
    """Commande /pressing et !pressing — Jeu troll Pressing Under Pressure."""

    def __init__(self, bot: commands.Bot):
        self.bot      = bot
        self.sessions: set[int] = set()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔧 Helpers visuels
    # ────────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _timer_bar(total: int, remaining: int) -> str:
        return "🟩" * max(0, remaining) + "⬜" * max(0, total - remaining)

    @staticmethod
    def _lives_bar(lives: int) -> str:
        return "❤️" * max(0, lives) + "🖤" * max(0, MAX_LIVES - lives)

    @staticmethod
    def _difficulty_stars(difficulty: int) -> str:
        d = max(1, min(5, difficulty))
        return "⭐" * d + "☆" * (5 - d)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔧 Logique énigme
    # ────────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _prepare_puzzle(base: dict) -> dict:
        """Copie le puzzle et varie légèrement la valeur de clics."""
        p = base.copy()
        if p.get("type") in ("multi_click", "click_once") and p.get("value", 1) > 0:
            p["value"] = max(1, p["value"] + random.choice([-1, 0, 0, 0, 1]))
        p["question"] = p["question"] + random.choice(TROLL_SUFFIXES)
        return p

    @staticmethod
    def _evaluate(state: PuzzleState) -> bool:
        """Évalue si le joueur a réussi l'énigme selon son type et les effets actifs."""
        ptype   = state.puzzle.get("type", "")
        presses = state.press_count
        req     = state.puzzle.get("value", 0)
        effect  = state.effect

        # — Effets troll globaux —
        if effect == "invert":
            if ptype in ("multi_click", "click_once", "wait_then_click", "click_any"):
                return presses == 0
            if ptype in ("no_click", "no_click_time"):
                return presses >= 1
        if effect == "double" and ptype in ("multi_click", "click_once", "wait_then_click"):
            req *= 2

        # — Types standards —
        match ptype:
            case "multi_click" | "click_once":
                return presses == req
            case "wait_then_click":
                return presses == 1
            case "no_click" | "no_click_time":
                return presses == 0
            case "click_any":
                return presses >= 1
            case "click_if_true":
                return (presses >= 1) == bool(state.puzzle.get("value", True))
            case "click_if_confused" | "random" | "logic_troll":
                return random.choice([True, False])   # 🎲 troll pur
            case "logic_invert":
                return presses == 0
            case "timed_click":
                return presses == 1
            case _:
                return True   # fallback

    @staticmethod
    def _instruction(puzzle: dict) -> str:
        """Génère la ligne d'instruction visible sous la question."""
        ptype = puzzle.get("type", "")
        req   = puzzle.get("value", 0)

        match ptype:
            case "multi_click":      return f"👉 Appuie exactement **{req}** fois."
            case "click_once":       return "👉 Appuie **une seule** fois."
            case "wait_then_click":  return f"⏳ Attends **{req} seconde(s)** puis appuie **une fois**."
            case "no_click" | "no_click_time": return "🚫 **N'appuie pas** sur le bouton."
            case "click_any":        return "✅ Appuie **au moins une fois**."
            case "click_if_true":    return "🤔 Appuie **si la phrase est vraie** — sinon ne fais rien."
            case "click_if_confused":return "😵 Appuie si tu es **confus**… ou pas. Va savoir."
            case "logic_invert":     return "🔄 Fais le **contraire** de ce que tu ferais normalement."
            case "logic_troll":      return "🎭 La logique ne s'applique pas ici. Bonne chance."
            case "timed_click":
                target = puzzle.get("time_target", "?")
                return f"⏱️ Appuie quand il reste exactement **{target}** bloc(s) verts."
            case "random":           return "🎲 La réponse est **aléatoire**. Tout peut marcher… ou pas."
            case _:                  return "❓ Fais ce qui te semble logique."

    # ────────────────────────────────────────────────────────────────────────────
    # 🖼️ Construction de l'embed
    # ────────────────────────────────────────────────────────────────────────────
    def _build_embed(
        self,
        state:         PuzzleState,
        lives:         int,
        combo:         int,
        puzzle_num:    int,
        total_puzzles: int,
        phase:         str = "playing",
        result_msg:    str = "",
    ) -> discord.Embed:
        p          = state.puzzle
        diff       = p.get("difficulty", 1)
        combo_str  = f"  🔥 Combo ×{combo}!" if combo >= COMBO_THRESHOLD else ""
        troll_str  = f"\n\n⚡ **EVENT :** {state.troll_msg}" if state.troll_msg else ""
        penalty_str = "\n⚠️ *MALUS actif — erreur = -2 vies !*" if state.double_penalty else ""

        if phase in ("playing", "success", "fail"):
            desc = (
                f"**Énigme {puzzle_num}/{total_puzzles}** {self._difficulty_stars(diff)}\n\n"
                f"📝 {p.get('question', '')}\n\n"
                f"{self._instruction(p)}"
                f"{troll_str}{penalty_str}\n\n"
                f"👆 Pressions : **{state.press_count}**\n"
                f"⏳ {self._timer_bar(state.total_time, state.remaining if phase == 'playing' else 0)}\n"
                f"Vies : {self._lives_bar(lives)}{combo_str}"
            )
            if phase != "playing":
                status = "✅" if phase == "success" else "❌"
                desc  += f"\n\n{status} **{result_msg}**"
        else:
            desc = result_msg

        embed = discord.Embed(
            title="🧠 Pressing Under Pressure",
            description=desc,
            color=PHASE_COLORS.get(phase, discord.Color.blurple()),
        )
        embed.set_footer(text="Pressing Under Pressure • Inspiré de Donitz / itch.io")
        return embed

    # ────────────────────────────────────────────────────────────────────────────
    # 🎯 Boucle d'une énigme — édite le message existant
    # ────────────────────────────────────────────────────────────────────────────
    async def _run_puzzle(
        self,
        msg:           discord.Message,
        view:          PressView,
        base_puzzle:   dict,
        lives:         int,
        combo:         int,
        puzzle_num:    int,
        total_puzzles: int,
    ) -> tuple[int, int]:
        """Joue une énigme en éditant msg. Retourne (lives, combo) mis à jour."""

        puzzle     = self._prepare_puzzle(base_puzzle)
        total_time = max(5, TOTAL_TIME_BASE - (combo // COMBO_THRESHOLD))
        state      = PuzzleState(puzzle, total_time)

        view.bind(state)

        async def refresh(phase: str = "playing", result_msg: str = "") -> None:
            embed = self._build_embed(state, lives, combo, puzzle_num, total_puzzles, phase, result_msg)
            try:
                await msg.edit(embed=embed, view=view)
            except (discord.NotFound, discord.HTTPException):
                pass

        await refresh()

        # — Timer live —
        while state.remaining > 0:
            await asyncio.sleep(1)
            state.remaining -= 1

            # Troll event (une seule fois par énigme, fenêtre 3–8s restantes)
            if (
                not state.troll_fired
                and 3 <= state.remaining <= 8
                and random.random() < TROLL_EVENT_PROB
            ):
                state.apply_troll(random.choice(TROLL_EVENTS))

            await refresh()

        # — Évaluation —
        view.lock()
        success = self._evaluate(state)

        if success:
            combo     += 1
            result_msg = f"Réussi ! ({state.press_count} pression(s))"
            phase      = "success"
        else:
            penalty    = 2 if state.double_penalty else 1
            lives     -= penalty
            combo      = 0
            req        = state.puzzle.get("value", "?")
            result_msg = f"Raté… ({state.press_count} pression(s), attendu : {req})"
            if state.double_penalty:
                result_msg += " — **MALUS ×2 !**"
            phase = "fail"

        await refresh(phase, result_msg)
        await asyncio.sleep(2)
        return lives, combo

    # ────────────────────────────────────────────────────────────────────────────
    # 🏁 Partie complète — UN seul message édité du début à la fin
    # ────────────────────────────────────────────────────────────────────────────
    async def _run_full_game(
        self,
        channel: discord.abc.Messageable,
        user:    discord.User | discord.Member,
    ) -> None:
        if user.id in self.sessions:
            await safe_send(channel, "⏳ Tu as déjà une partie en cours !", delete_after=5)
            return

        puzzles_all = load_puzzles()
        if not puzzles_all:
            await safe_send(channel, "❌ Aucune énigme trouvée dans le fichier JSON.")
            return

        self.sessions.add(user.id)

        try:
            puzzles       = sorted(
                random.sample(puzzles_all, min(MAX_PUZZLES, len(puzzles_all))),
                key=lambda p: p.get("difficulty", 1),
            )
            lives         = MAX_LIVES
            combo         = 0
            total_puzzles = len(puzzles)

            # — Message unique : intro —
            view = PressView(user)
            view.lock()

            intro_embed = discord.Embed(
                title="🕹️ Pressing Under Pressure — DÉPART !",
                description=(
                    f"Bienvenue **{user.display_name}** !\n\n"
                    f"Tu vas affronter **{total_puzzles} énigmes** triées par difficulté.\n"
                    f"Lis bien les consignes… ou pas.\n\n"
                    f"❤️ Vies : {self._lives_bar(lives)}  "
                    f"🧩 Énigmes : **{total_puzzles}**\n\n"
                    f"*{COMBO_THRESHOLD} succès consécutifs = timer raccourci 🔥*\n"
                    f"*Des events troll peuvent surgir à tout moment ⚡*\n\n"
                    f"**Début dans 3 secondes…**"
                ),
                color=PHASE_COLORS["intro"],
            )
            intro_embed.set_footer(text="Pressing Under Pressure • Inspiré de Donitz / itch.io")

            msg = await safe_send(channel, embed=intro_embed, view=view)
            if msg is None:
                return

            await asyncio.sleep(3)

            # — Boucle énigmes —
            puzzles_done = 0
            for i, puzzle in enumerate(puzzles, start=1):
                lives, combo = await self._run_puzzle(
                    msg, view, puzzle, lives, combo, i, total_puzzles
                )
                puzzles_done += 1
                if lives <= 0:
                    break

            # — Écran de fin —
            won = lives > 0 and puzzles_done == total_puzzles
            update_score(user.id, user.display_name, puzzles_done, won)
            view.lock()

            if won:
                phase, end_desc = "end_win", (
                    f"🏆 **VICTOIRE !**\n\n"
                    f"**{user.display_name}** a survécu à toutes les énigmes !\n\n"
                    f"🧩 Énigmes : **{puzzles_done}/{total_puzzles}**\n"
                    f"Vies restantes : {self._lives_bar(lives)}\n\n"
                    f"*Utilise `/pressing top` pour voir le classement.*"
                )
            else:
                phase, end_desc = "end_lose", (
                    f"💀 **GAME OVER**\n\n"
                    f"**{user.display_name}** s'est effondré à l'énigme **{puzzles_done}**.\n\n"
                    f"🧩 Énigmes réussies : **{max(0, puzzles_done - 1)}/{total_puzzles}**\n"
                    f"Vies restantes : {self._lives_bar(0)}\n\n"
                    f"*Utilise `/pressing top` pour voir le classement.*"
                )

            dummy     = PuzzleState({}, 0)
            end_embed = self._build_embed(
                dummy, max(0, lives), combo, puzzles_done, total_puzzles,
                phase=phase, result_msg=end_desc,
            )
            try:
                await msg.edit(embed=end_embed, view=view)
            except Exception:
                pass

        except Exception as e:
            log.error("[PUP] Erreur inattendue : %s", e, exc_info=True)
            try:
                await safe_send(channel, "❌ Une erreur inattendue a interrompu la partie.")
            except Exception:
                pass
        finally:
            self.sessions.discard(user.id)

    # ────────────────────────────────────────────────────────────────────────────
    # 🏅 Classement
    # ────────────────────────────────────────────────────────────────────────────
    async def _send_leaderboard(self, channel: discord.abc.Messageable) -> None:
        scores = load_scores()
        if not scores:
            await safe_send(channel, "📭 Aucun score enregistré pour le moment.")
            return

        ranked = sorted(
            scores.values(),
            key=lambda x: (x.get("wins", 0), x.get("best", 0)),
            reverse=True,
        )[:10]

        medals = ["🥇", "🥈", "🥉"] + ["🔹"] * 7
        lines  = [
            f"{medals[i]} **{e['username']}** — "
            f"{e.get('wins', 0)}V / {e.get('games', 0)} parties | "
            f"Record : {e.get('best', 0)} énigmes"
            for i, e in enumerate(ranked)
        ]

        embed = discord.Embed(
            title="🏆 Classement — Pressing Under Pressure",
            description="\n".join(lines),
            color=discord.Color.gold(),
        )
        embed.set_footer(text="Pressing Under Pressure • Inspiré de Donitz / itch.io")
        await safe_send(channel, embed=embed)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(name="pressing", description="Lance le jeu Pressing Under Pressure !")
    @app_commands.describe(action="Lancer une partie ou voir le classement")
    @app_commands.choices(action=[
        app_commands.Choice(name="Jouer",      value="play"),
        app_commands.Choice(name="Classement", value="top"),
    ])
    @app_commands.checks.cooldown(1, 10.0, key=lambda i: i.user.id)
    async def slash_pressing(
        self,
        interaction: discord.Interaction,
        action: app_commands.Choice[str] = None,
    ):
        await interaction.response.defer()
        if action and action.value == "top":
            await self._send_leaderboard(interaction.channel)
        else:
            await self._run_full_game(interaction.channel, interaction.user)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="pressing", aliases=["pup"], help="Lance le jeu Pressing Under Pressure !")
    @commands.cooldown(1, 10.0, commands.BucketType.user)
    async def prefix_pressing(self, ctx: commands.Context):
        await self._run_full_game(ctx.channel, ctx.author)

    @commands.command(name="pressingtop", aliases=["puptop", "puppodium"])
    @commands.cooldown(1, 10.0, commands.BucketType.user)
    async def prefix_pressing_top(self, ctx: commands.Context):
        await self._send_leaderboard(ctx.channel)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = PressingUnderPressure(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Jeux"
    await bot.add_cog(cog)
