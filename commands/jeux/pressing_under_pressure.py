# ────────────────────────────────────────────────────────────────────────────────
# 📌 pressing_under_pressure.py — Jeu Pressing Under Pressure (slash + préfixe)
# Objectif : Mini-jeu troll inspiré de The Impossible Quiz, énigmes aléatoires
#            avec timer live, vies, streaks, combo, troll events, classement.
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
import time
import os
import logging

from utils.discord_utils import safe_send, safe_respond

log = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────────────────────────
# 🎨 Constantes
# ────────────────────────────────────────────────────────────────────────────────
DATA_JSON_PATH   = os.path.join("data", "pressing_puzzles.json")
SCORES_JSON_PATH = os.path.join("data", "pressing_scores.json")

MAX_LIVES        = 3          # ❤️ Vies de départ
TOTAL_TIME_BASE  = 10         # ⏱ Secondes de base par énigme
COMBO_THRESHOLD  = 3          # 🔥 Nombre de succès consécutifs pour le combo
MAX_PUZZLES      = 10         # 🧩 Nombre max d'énigmes par partie

# Variations de texte troll ajoutées à la question
TROLL_SUFFIXES = [
    " (tu crois être prêt ?)",
    " (j'espère que tu lis bien…)",
    " (ne rate pas ça.)",
    " (facile… ou pas.)",
    " (je te surveille 👀)",
    " (réfléchis bien avant d'agir.)",
    " (ou alors… fais le contraire ?)",
    " (ha. bonne chance.)",
    " (la réponse est évidente. Enfin… presque.)",
]

# Events troll aléatoires (déclenchés aléatoirement en cours d'énigme)
TROLL_EVENTS = [
    {"msg": "⚠️ **FAUSSE ALERTE** : Il ne se passe rien. Continue.", "effect": None},
    {"msg": "🔀 **LES RÈGLES ONT CHANGÉ.** Fais exactement le contraire de ce qui est demandé.", "effect": "invert"},
    {"msg": "😴 **Rien à voir ici.** Passe ton tour… ou pas.", "effect": None},
    {"msg": "💥 **DOUBLE OU RIEN.** Le nombre de pressions requis vient de doubler.", "effect": "double"},
    {"msg": "🎲 **CHANCE !** La réponse est maintenant aléatoire.", "effect": "random"},
    {"msg": "⏩ **SPEED RUN !** Tu n'as plus que 5 secondes.", "effect": "halve_time"},
    {"msg": "🔁 **RESET !** Le compteur de pressions vient d'être remis à zéro.", "effect": "reset_presses"},
]

# ────────────────────────────────────────────────────────────────────────────────
# 💾 Gestion du score persistant
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
    uid = str(user_id)
    entry = scores.get(uid, {"username": username, "games": 0, "wins": 0, "best": 0, "total_puzzles": 0})
    entry["username"]      = username
    entry["games"]        += 1
    if won:
        entry["wins"]     += 1
    entry["total_puzzles"] += puzzles_done
    if puzzles_done > entry.get("best", 0):
        entry["best"]      = puzzles_done
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
        log.warning(f"[PUP] Fichier {DATA_JSON_PATH} introuvable.")
        return []
    except json.JSONDecodeError as e:
        log.error(f"[PUP] JSON invalide : {e}")
        return []

# ────────────────────────────────────────────────────────────────────────────────
# 🧩 Classe PuzzleState — état d'une énigme en cours
# ────────────────────────────────────────────────────────────────────────────────
class PuzzleState:
    def __init__(self, puzzle: dict, total_time: int):
        self.puzzle         = puzzle
        self.press_count    = 0
        self.total_time     = total_time
        self.remaining      = total_time
        self.effect         = None          # Effet troll actif
        self.troll_fired    = False         # Un seul troll par énigme
        self.finished       = asyncio.Event()

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ Vue du bouton
# ────────────────────────────────────────────────────────────────────────────────
class PressView(discord.ui.View):
    """Vue avec un unique bouton « Appuie ici ! » lié à un PuzzleState."""

    def __init__(self, state: PuzzleState, user: discord.User | discord.Member):
        super().__init__(timeout=None)   # Le timeout est géré manuellement
        self.state = state
        self.user  = user

    @discord.ui.button(label="Appuie ici !", style=discord.ButtonStyle.green, emoji="👆")
    async def press(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "❌ Ce n'est pas ta partie !", ephemeral=True
            )
            return

        s = self.state

        # Effet reset_presses
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
        self.sessions: set[int] = set()   # user_id des parties en cours

    # ────────────────────────────────────────────────────────────────────────────
    # 🔧 Utilitaires
    # ────────────────────────────────────────────────────────────────────────────
    def _generate_timer(self, total: int, remaining: int) -> str:
        green = "🟩" * max(0, remaining)
        white = "⬜" * max(0, total - remaining)
        return green + white

    def _lives_display(self, lives: int) -> str:
        return "❤️" * lives + "🖤" * (MAX_LIVES - lives)

    def _randomize_puzzle(self, puzzle: dict) -> dict:
        p = puzzle.copy()
        if p["type"] in ("click_once", "multi_click"):
            p["value"] = max(1, p.get("value", 1) + random.choice([-1, 0, 0, 1]))
        p["question"] = p["question"] + random.choice(TROLL_SUFFIXES)
        return p

    def _evaluate_success(self, state: PuzzleState) -> bool:
        ptype   = state.puzzle.get("type", "")
        presses = state.press_count
        req     = state.puzzle.get("value", 0)
        effect  = state.effect

        # Effet invert : inverser la logique click / no_click
        if effect == "invert":
            if ptype in ("multi_click", "click_once"):
                return presses == 0
            if ptype in ("no_click", "no_click_time"):
                return presses >= 1
        # Effet double
        if effect == "double":
            if ptype in ("multi_click", "click_once"):
                req = req * 2

        if ptype in ("multi_click", "click_once"):
            return presses == req
        if ptype in ("no_click", "no_click_time"):
            return presses == 0
        if ptype == "click_any":
            return True
        if ptype == "click_if_true":
            return bool(state.puzzle.get("value", True))
        if ptype == "click_if_confused":
            return random.choice([True, False])   # 🎲 troll pur
        if ptype == "random":
            return random.choice([True, False])
        return True

    def _build_embed(
        self,
        state: PuzzleState,
        lives: int,
        combo: int,
        puzzle_num: int,
        total_puzzles: int,
        troll_msg: str | None = None,
    ) -> discord.Embed:
        p       = state.puzzle
        ptype   = p.get("type", "")
        req     = p.get("value", 0)

        # Indice de ce qu'il faut faire
        if ptype in ("multi_click", "click_once"):
            instruction = f"👉 Appuie exactement **{req}** fois."
        elif ptype in ("no_click", "no_click_time"):
            instruction = "🚫 N'appuie **surtout pas** sur le bouton !"
        elif ptype == "click_any":
            instruction = "✅ Appuie **au moins une fois**."
        elif ptype == "click_if_true":
            instruction = "🤔 Appuie **si la phrase est vraie**, sinon ne fais rien."
        elif ptype == "click_if_confused":
            instruction = "😵 Appuie si tu es **confus**… ou pas. Va savoir."
        elif ptype == "random":
            instruction = "🎲 La réponse est **complètement aléatoire**. Bonne chance."
        else:
            instruction = "❓ Fais ce qui te semble logique."

        combo_display = f"🔥 Combo ×{combo} !" if combo >= COMBO_THRESHOLD else ""
        troll_display = f"\n\n⚡ **EVENT :** {troll_msg}" if troll_msg else ""

        embed = discord.Embed(
            title="🧠 Pressing Under Pressure !",
            description=(
                f"**Énigme {puzzle_num}/{total_puzzles}** — `{p.get('id', '?')}`\n\n"
                f"📝 {p['question']}\n\n"
                f"{instruction}{troll_display}\n\n"
                f"👆 Pressions : **{state.press_count}**\n"
                f"⏳ Temps : {self._generate_timer(state.total_time, state.remaining)}\n"
                f"Vies : {self._lives_display(lives)}  {combo_display}"
            ),
            color=discord.Color.orange(),
        )
        embed.set_footer(text="Pressing Under Pressure • Inspiré de Donitz/itch.io")
        return embed

    # ────────────────────────────────────────────────────────────────────────────
    # 🎯 Résolution d'une énigme
    # ────────────────────────────────────────────────────────────────────────────
    async def _run_puzzle(
        self,
        channel: discord.abc.Messageable,
        base_puzzle: dict,
        user: discord.User | discord.Member,
        lives: int,
        combo: int,
        puzzle_num: int,
        total_puzzles: int,
    ) -> tuple[bool, int, int]:
        """Lance une énigme. Retourne (success, lives, combo)."""

        puzzle      = self._randomize_puzzle(base_puzzle)
        total_time  = max(5, TOTAL_TIME_BASE - (combo // COMBO_THRESHOLD))   # accélère avec le combo
        state       = PuzzleState(puzzle, total_time)
        view        = PressView(state, user)
        troll_msg   = None

        embed = self._build_embed(state, lives, combo, puzzle_num, total_puzzles)
        try:
            msg = await safe_send(channel, embed=embed, view=view)
        except Exception as e:
            log.error(f"[PUP] Impossible d'envoyer l'embed : {e}")
            return False, lives, combo

        # ── Timer live ──────────────────────────────────────────────────────
        while state.remaining > 0:
            await asyncio.sleep(1)
            state.remaining -= 1

            # 🎲 Troll event aléatoire (une seule fois, entre 3s et 7s restantes)
            if (
                not state.troll_fired
                and 3 <= state.remaining <= 7
                and random.random() < 0.35          # 35 % de chance
            ):
                troll        = random.choice(TROLL_EVENTS)
                troll_msg    = troll["msg"]
                effect       = troll["effect"]
                state.troll_fired = True

                if effect == "halve_time":
                    state.remaining = min(state.remaining, 5)
                    state.total_time = state.remaining + (state.total_time - state.remaining)
                elif effect == "double":
                    state.effect = "double"
                elif effect == "invert":
                    state.effect = "invert"
                elif effect == "random":
                    state.effect = "random"
                    state.puzzle["type"] = "random"
                elif effect == "reset_presses":
                    state.effect = "reset_presses"

            embed = self._build_embed(state, lives, combo, puzzle_num, total_puzzles, troll_msg)
            try:
                await msg.edit(embed=embed, view=view)
            except discord.NotFound:
                return False, lives, combo
            except Exception:
                pass

        # ── Fin du timer — désactiver le bouton ─────────────────────────────
        for child in view.children:
            child.disabled = True  # type: ignore

        success = self._evaluate_success(state)

        # Résultat dans l'embed
        req_display = state.puzzle.get("value", 0)
        if success:
            embed.color = discord.Color.green()
            embed.add_field(
                name="🎉 Succès !",
                value=f"Pressions : **{state.press_count}**",
                inline=False,
            )
            combo += 1
        else:
            embed.color = discord.Color.red()
            embed.add_field(
                name="❌ Échec",
                value=f"Pressions : **{state.press_count}** | Attendu : **{req_display}**",
                inline=False,
            )
            lives -= 1
            combo  = 0

        try:
            await msg.edit(embed=embed, view=view)
        except Exception:
            pass

        await asyncio.sleep(1.5)   # Petite pause pour laisser le joueur lire
        return success, lives, combo

    # ────────────────────────────────────────────────────────────────────────────
    # 🏁 Partie complète
    # ────────────────────────────────────────────────────────────────────────────
    async def _run_full_game(
        self,
        channel: discord.abc.Messageable,
        user: discord.User | discord.Member,
    ) -> None:
        if user.id in self.sessions:
            await safe_send(channel, "⏳ Tu as déjà une partie en cours !")
            return

        PUZZLES = load_puzzles()
        if not PUZZLES:
            await safe_send(channel, "❌ Aucune énigme trouvée dans le JSON.")
            return

        self.sessions.add(user.id)

        try:
            puzzles        = random.sample(PUZZLES, min(MAX_PUZZLES, len(PUZZLES)))
            lives          = MAX_LIVES
            combo          = 0
            puzzles_done   = 0
            total_puzzles  = len(puzzles)

            # ── Intro ────────────────────────────────────────────────────────
            intro = discord.Embed(
                title="🕹️ Pressing Under Pressure — DÉPART !",
                description=(
                    f"Bienvenue **{user.display_name}** !\n\n"
                    f"Tu vas affronter **{total_puzzles} énigmes** de plus en plus retorses.\n"
                    f"Lis bien les consignes… ou pas.\n\n"
                    f"❤️ Vies : **{MAX_LIVES}** | 🧩 Énigmes : **{total_puzzles}**\n\n"
                    f"*(Chaque {COMBO_THRESHOLD} succès consécutifs = le timer s'accélère 🔥)*"
                ),
                color=discord.Color.blurple(),
            )
            intro.set_footer(text="Inspiré de Pressing Under Pressure • Donitz / itch.io")
            await safe_send(channel, embed=intro)
            await asyncio.sleep(3)

            # ── Boucle énigmes ───────────────────────────────────────────────
            for i, puzzle in enumerate(puzzles, start=1):
                _, lives, combo = await self._run_puzzle(
                    channel, puzzle, user, lives, combo, i, total_puzzles
                )
                puzzles_done += 1

                if lives <= 0:
                    break

            # ── Résultat final ───────────────────────────────────────────────
            won = (lives > 0 and puzzles_done == total_puzzles)
            update_score(user.id, user.display_name, puzzles_done, won)

            if won:
                result = discord.Embed(
                    title="🏆 VICTOIRE !",
                    description=(
                        f"**{user.display_name}** a survécu à toutes les énigmes !\n\n"
                        f"Énigmes réussies : **{puzzles_done}/{total_puzzles}**\n"
                        f"Vies restantes : {self._lives_display(lives)}"
                    ),
                    color=discord.Color.gold(),
                )
            else:
                result = discord.Embed(
                    title="💀 GAME OVER",
                    description=(
                        f"**{user.display_name}** s'est effondré à l'énigme **{puzzles_done}**.\n\n"
                        f"Énigmes réussies : **{puzzles_done - 1}/{total_puzzles}**\n"
                        f"Vies restantes : {self._lives_display(0)}"
                    ),
                    color=discord.Color.dark_red(),
                )
            result.set_footer(text="Utilise !pressing top pour voir le classement.")
            await safe_send(channel, embed=result)

        except Exception as e:
            log.error(f"[PUP] Erreur inattendue : {e}", exc_info=True)
            await safe_send(channel, "❌ Une erreur inattendue a interrompu la partie.")
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
        lines  = []
        for idx, entry in enumerate(ranked):
            lines.append(
                f"{medals[idx]} **{entry['username']}** — "
                f"{entry.get('wins', 0)}W / {entry.get('games', 0)} parties | "
                f"Best : {entry.get('best', 0)} énigmes"
            )

        embed = discord.Embed(
            title="🏆 Classement — Pressing Under Pressure",
            description="\n".join(lines),
            color=discord.Color.gold(),
        )
        await safe_send(channel, embed=embed)

    # ────────────────────────────────────────────────────────────────────────────
    # ⚡ Commande SLASH — jeu
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(name="pressing", description="Lance le jeu Pressing Under Pressure !")
    @app_commands.describe(action="Lancer une partie ou voir le classement")
    @app_commands.choices(action=[
        app_commands.Choice(name="Jouer", value="play"),
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
    # ⚡ Commande PREFIX — jeu
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
