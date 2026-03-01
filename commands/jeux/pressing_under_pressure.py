# ────────────────────────────────────────────────────────────────────────────────
# 📌 pressing_under_pressure.py — Jeu Pressing Under Pressure (slash + préfixe)
# Objectif : Mini-jeu troll inspiré de The Impossible Quiz, énigmes aléatoires
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

from utils.discord_utils import safe_send, safe_respond

log = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────────────────────────
# 🎨 Constantes
# ────────────────────────────────────────────────────────────────────────────────
DATA_JSON_PATH   = os.path.join("data", "pressing_puzzles.json")
SCORES_JSON_PATH = os.path.join("data", "pressing_scores.json")

MAX_LIVES       = 3     # ❤️ Vies de départ
TOTAL_TIME_BASE = 12    # ⏱ Secondes de base par énigme
COMBO_THRESHOLD = 3     # 🔥 Succès consécutifs pour accélérer le timer
MAX_PUZZLES     = 10    # 🧩 Nombre d'énigmes par partie

# Suffixes troll ajoutés aléatoirement aux questions
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

# Events troll déclenchés aléatoirement en cours d'énigme
TROLL_EVENTS = [
    {"msg": "⚠️ **FAUSSE ALERTE.** Il ne se passe rien. Continue.", "effect": None},
    {"msg": "🔀 **LES RÈGLES ONT CHANGÉ.** Fais exactement le contraire.", "effect": "invert"},
    {"msg": "😴 **Rien à voir ici.** Passe ton chemin… ou pas.", "effect": None},
    {"msg": "💥 **DOUBLE OU RIEN.** Le nombre de pressions requis vient de doubler.", "effect": "double"},
    {"msg": "🎲 **CHANCE !** La réponse est maintenant complètement aléatoire.", "effect": "random"},
    {"msg": "⏩ **SPEED RUN !** Tu n'as plus que 4 secondes.", "effect": "halve_time"},
    {"msg": "🔁 **RESET !** Ton compteur de pressions vient d'être remis à zéro.", "effect": "reset_presses"},
    {"msg": "🙈 **DISTRACTION.** Ne lis pas ceci. Concentre-toi.", "effect": None},
    {"msg": "📉 **MALUS.** Tu perdras 2 vies si tu te trompes maintenant.", "effect": "double_penalty"},
]

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
        "username": username, "games": 0, "wins": 0,
        "best": 0, "total_puzzles": 0,
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
    def __init__(self, puzzle: dict, total_time: int):
        self.puzzle         = puzzle
        self.press_count    = 0
        self.total_time     = total_time
        self.remaining      = total_time
        self.effect         = None   # Effet troll actif
        self.double_penalty = False  # Perd 2 vies si échec
        self.troll_fired    = False  # Un seul troll event par énigme
        self.troll_msg      = None   # Message troll affiché dans l'embed

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ Vue — bouton unique, recyclé pour toute la partie
# ────────────────────────────────────────────────────────────────────────────────
class PressView(discord.ui.View):
    """
    Vue persistante réutilisée durant toute la partie.
    On met à jour state entre chaque énigme via bind().
    """

    def __init__(self, user: discord.User | discord.Member):
        super().__init__(timeout=None)
        self.user  = user
        self.state: PuzzleState | None = None

    def bind(self, state: PuzzleState) -> None:
        """Lie la vue à un nouveau PuzzleState pour l'énigme suivante."""
        self.state = state
        for child in self.children:
            child.disabled = False   # type: ignore

    def lock(self) -> None:
        """Désactive le bouton."""
        for child in self.children:
            child.disabled = True    # type: ignore

    @discord.ui.button(label="Appuie ici !", style=discord.ButtonStyle.green, emoji="👆")
    async def press(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "❌ Ce n'est pas ta partie !", ephemeral=True
            )
            return

        s = self.state
        if s is None:
            await interaction.response.defer()
            return

        # Effet reset_presses : remet le compteur à 0 au premier clic post-event
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
        self.sessions: set[int] = set()   # user_id en cours de partie

    # ────────────────────────────────────────────────────────────────────────────
    # 🔧 Helpers d'affichage
    # ────────────────────────────────────────────────────────────────────────────
    def _timer_bar(self, total: int, remaining: int) -> str:
        green = "🟩" * max(0, remaining)
        white = "⬜" * max(0, total - remaining)
        return green + white

    def _lives_bar(self, lives: int) -> str:
        return "❤️" * max(0, lives) + "🖤" * max(0, MAX_LIVES - lives)

    def _difficulty_stars(self, difficulty: int) -> str:
        d = max(1, min(5, difficulty))
        return "⭐" * d + "☆" * (5 - d)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔧 Logique énigme
    # ────────────────────────────────────────────────────────────────────────────
    def _prepare_puzzle(self, base: dict) -> dict:
        """Copie et randomise légèrement le puzzle."""
        p     = base.copy()
        ptype = p.get("type", "")

        # Légère variation du nombre de clics
        if ptype in ("multi_click", "click_once") and p.get("value", 1) > 0:
            p["value"] = max(1, p["value"] + random.choice([-1, 0, 0, 0, 1]))

        p["question"] = p["question"] + random.choice(TROLL_SUFFIXES)
        return p

    def _evaluate(self, state: PuzzleState) -> bool:
        """Évalue si le joueur a réussi l'énigme."""
        ptype   = state.puzzle.get("type", "")
        presses = state.press_count
        req     = state.puzzle.get("value", 0)
        effect  = state.effect

        # Effets troll qui modifient la logique
        if effect == "invert":
            if ptype in ("multi_click", "click_once", "wait_then_click", "click_any"):
                return presses == 0
            if ptype in ("no_click", "no_click_time"):
                return presses >= 1
        if effect == "double" and ptype in ("multi_click", "click_once", "wait_then_click"):
            req = req * 2

        # Types de base
        if ptype in ("multi_click", "click_once"):
            return presses == req

        if ptype == "wait_then_click":
            # Succès si le joueur a appuyé exactement 1 fois (le timing est honorifique)
            return presses == 1

        if ptype in ("no_click", "no_click_time"):
            return presses == 0

        if ptype == "click_any":
            return presses >= 1

        if ptype == "click_if_true":
            expected_click = bool(state.puzzle.get("value", True))
            return (presses >= 1) == expected_click

        if ptype == "click_if_confused":
            return random.choice([True, False])   # 🎲 troll pur

        if ptype == "logic_invert":
            # La question dit d'appuyer → ne pas appuyer pour réussir
            return presses == 0

        if ptype == "logic_troll":
            # Insoluble par design
            return random.choice([True, False])

        if ptype == "timed_click":
            # Succès si le joueur a appuyé exactement 1 fois
            return presses == 1

        if ptype == "random":
            return random.choice([True, False])

        return True   # Fallback : type inconnu → succès

    def _instruction(self, puzzle: dict) -> str:
        """Génère la ligne d'instruction visible sous la question."""
        ptype = puzzle.get("type", "")
        req   = puzzle.get("value", 0)

        if ptype == "multi_click":
            return f"👉 Appuie exactement **{req}** fois."
        if ptype == "click_once":
            return "👉 Appuie **une seule** fois."
        if ptype == "wait_then_click":
            return f"⏳ Attends **{req} seconde(s)** puis appuie **une fois**."
        if ptype in ("no_click", "no_click_time"):
            return "🚫 **N'appuie pas** sur le bouton."
        if ptype == "click_any":
            return "✅ Appuie **au moins une fois**."
        if ptype == "click_if_true":
            return "🤔 Appuie **si la phrase est vraie** — sinon ne fais rien."
        if ptype == "click_if_confused":
            return "😵 Appuie si tu es **confus**… ou pas. Va savoir."
        if ptype == "logic_invert":
            return "🔄 Fais le **contraire** de ce que tu ferais normalement."
        if ptype == "logic_troll":
            return "🎭 La logique ne s'applique pas ici. Bonne chance."
        if ptype == "timed_click":
            target = puzzle.get("time_target", "?")
            return f"⏱️ Appuie quand il reste exactement **{target}** bloc(s) verts."
        if ptype == "random":
            return "🎲 La réponse est **aléatoire**. Tout ce que tu fais peut marcher… ou pas."
        return "❓ Fais ce qui te semble logique."

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
        p     = state.puzzle
        diff  = p.get("difficulty", 1)

        combo_str  = f"  🔥 Combo ×{combo}!" if combo >= COMBO_THRESHOLD else ""
        troll_str  = f"\n\n⚡ **EVENT :** {state.troll_msg}" if state.troll_msg else ""
        penalty_str = "\n⚠️ *MALUS actif — erreur = -2 vies !*" if state.double_penalty else ""

        if phase == "playing":
            color = discord.Color.orange()
            desc  = (
                f"**Énigme {puzzle_num}/{total_puzzles}** {self._difficulty_stars(diff)}\n\n"
                f"📝 {p.get('question', '')}\n\n"
                f"{self._instruction(p)}"
                f"{troll_str}{penalty_str}\n\n"
                f"👆 Pressions : **{state.press_count}**\n"
                f"⏳ {self._timer_bar(state.total_time, state.remaining)}\n"
                f"Vies : {self._lives_bar(lives)}{combo_str}"
            )

        elif phase == "success":
            color = discord.Color.green()
            desc  = (
                f"**Énigme {puzzle_num}/{total_puzzles}** {self._difficulty_stars(diff)}\n\n"
                f"📝 {p.get('question', '')}\n\n"
                f"{self._instruction(p)}"
                f"{troll_str}\n\n"
                f"👆 Pressions : **{state.press_count}**\n"
                f"⏳ {self._timer_bar(state.total_time, 0)}\n"
                f"Vies : {self._lives_bar(lives)}{combo_str}\n\n"
                f"✅ **{result_msg}**"
            )

        elif phase == "fail":
            color = discord.Color.red()
            desc  = (
                f"**Énigme {puzzle_num}/{total_puzzles}** {self._difficulty_stars(diff)}\n\n"
                f"📝 {p.get('question', '')}\n\n"
                f"{self._instruction(p)}"
                f"{troll_str}\n\n"
                f"👆 Pressions : **{state.press_count}**\n"
                f"⏳ {self._timer_bar(state.total_time, 0)}\n"
                f"Vies : {self._lives_bar(lives)}{combo_str}\n\n"
                f"❌ **{result_msg}**"
            )

        else:
            # end_win / end_lose / intro
            color_map = {
                "end_win":  discord.Color.gold(),
                "end_lose": discord.Color.dark_red(),
                "intro":    discord.Color.blurple(),
            }
            color = color_map.get(phase, discord.Color.blurple())
            desc  = result_msg

        embed = discord.Embed(
            title="🧠 Pressing Under Pressure",
            description=desc,
            color=color,
        )
        embed.set_footer(text="Pressing Under Pressure • Inspiré de Donitz / itch.io")
        return embed

    # ────────────────────────────────────────────────────────────────────────────
    # 🎯 Une énigme — édite le message existant, ne crée rien de nouveau
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

        embed = self._build_embed(state, lives, combo, puzzle_num, total_puzzles)
        try:
            await msg.edit(embed=embed, view=view)
        except discord.NotFound:
            return lives, combo

        # ── Timer live ──────────────────────────────────────────────────────
        while state.remaining > 0:
            await asyncio.sleep(1)
            state.remaining -= 1

            # 🎲 Troll event (une seule fois par énigme, fenêtre 3–8s restantes)
            if (
                not state.troll_fired
                and 3 <= state.remaining <= 8
                and random.random() < 0.30
            ):
                troll             = random.choice(TROLL_EVENTS)
                state.troll_msg   = troll["msg"]
                state.troll_fired = True
                effect            = troll["effect"]

                if effect == "halve_time":
                    state.remaining = min(state.remaining, 4)
                elif effect == "double":
                    state.effect = "double"
                elif effect == "invert":
                    state.effect = "invert"
                elif effect == "random":
                    state.effect = "random"
                    state.puzzle  = {**state.puzzle, "type": "random"}
                elif effect == "reset_presses":
                    state.effect = "reset_presses"
                elif effect == "double_penalty":
                    state.double_penalty = True

            embed = self._build_embed(state, lives, combo, puzzle_num, total_puzzles)
            try:
                await msg.edit(embed=embed, view=view)
            except discord.NotFound:
                return lives, combo
            except Exception:
                pass

        # ── Fin timer — évaluation ──────────────────────────────────────────
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

        embed = self._build_embed(
            state, max(0, lives), combo, puzzle_num, total_puzzles,
            phase=phase, result_msg=result_msg,
        )
        try:
            await msg.edit(embed=embed, view=view)
        except Exception:
            pass

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

        PUZZLES = load_puzzles()
        if not PUZZLES:
            await safe_send(channel, "❌ Aucune énigme trouvée dans le fichier JSON.")
            return

        self.sessions.add(user.id)

        try:
            # Sélection et tri par difficulté croissante
            pool    = random.sample(PUZZLES, min(MAX_PUZZLES, len(PUZZLES)))
            puzzles = sorted(pool, key=lambda p: p.get("difficulty", 1))

            lives         = MAX_LIVES
            combo         = 0
            total_puzzles = len(puzzles)

            # ── Création du message unique (intro) ───────────────────────────
            view = PressView(user)
            view.lock()   # Bouton désactivé pendant l'intro

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
                color=discord.Color.blurple(),
            )
            intro_embed.set_footer(text="Pressing Under Pressure • Inspiré de Donitz / itch.io")

            # Ce message est le SEUL de toute la partie
            msg = await safe_send(channel, embed=intro_embed, view=view)
            if msg is None:
                return

            await asyncio.sleep(3)

            # ── Boucle énigmes ───────────────────────────────────────────────
            puzzles_done = 0
            for i, puzzle in enumerate(puzzles, start=1):
                lives, combo = await self._run_puzzle(
                    msg, view, puzzle, lives, combo, i, total_puzzles
                )
                puzzles_done += 1
                if lives <= 0:
                    break

            # ── Écran de fin — édite toujours le même message ────────────────
            won = lives > 0 and puzzles_done == total_puzzles
            update_score(user.id, user.display_name, puzzles_done, won)
            view.lock()

            if won:
                phase    = "end_win"
                end_desc = (
                    f"🏆 **VICTOIRE !**\n\n"
                    f"**{user.display_name}** a survécu à toutes les énigmes !\n\n"
                    f"🧩 Énigmes : **{puzzles_done}/{total_puzzles}**\n"
                    f"Vies restantes : {self._lives_bar(lives)}\n\n"
                    f"*Utilise `!pressing top` pour voir le classement.*"
                )
            else:
                phase    = "end_lose"
                end_desc = (
                    f"💀 **GAME OVER**\n\n"
                    f"**{user.display_name}** s'est effondré à l'énigme **{puzzles_done}**.\n\n"
                    f"🧩 Énigmes réussies : **{max(0, puzzles_done - 1)}/{total_puzzles}**\n"
                    f"Vies restantes : {self._lives_bar(0)}\n\n"
                    f"*Utilise `!pressing top` pour voir le classement.*"
                )

            dummy = PuzzleState({}, 0)
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
    # ⚡ Commande SLASH
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

    @slash_pressing.error
    async def slash_pressing_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                f"⏳ Cooldown ! Réessaie dans **{error.retry_after:.1f}s**.", ephemeral=True
            )

    # ────────────────────────────────────────────────────────────────────────────
    # ⚡ Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.group(name="pressing", aliases=["pup"], invoke_without_command=True)
    @commands.cooldown(1, 10.0, commands.BucketType.user)
    async def prefix_pressing(self, ctx: commands.Context):
        await self._run_full_game(ctx.channel, ctx.author)

    @prefix_pressing.command(name="top", aliases=["classement", "lb"])
    async def prefix_pressing_top(self, ctx: commands.Context):
        """Affiche le classement des meilleurs joueurs."""
        await self._send_leaderboard(ctx.channel)

    @prefix_pressing.error
    async def prefix_pressing_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.CommandOnCooldown):
            await safe_send(
                ctx.channel,
                f"⏳ Cooldown ! Réessaie dans **{error.retry_after:.1f}s**.",
            )

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = PressingUnderPressure(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Jeux"
    await bot.add_cog(cog)
