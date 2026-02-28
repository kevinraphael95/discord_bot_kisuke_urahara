# ────────────────────────────────────────────────────────────────────────────────
# 📌 scientific_calculator.py — Calculatrice scientifique interactive
# Objectif : Calculatrice scientifique interactive avec mini-clavier et fonctions avancées
# Catégorie : Fun&Random
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button
import math
import logging
import re

from utils.discord_utils import safe_send, safe_edit, safe_respond

log = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────────────────────────
# 🧮 Moteur de calcul sécurisé
# ────────────────────────────────────────────────────────────────────────────────

_SAFE_TOKEN_RE = re.compile(
    r"""
    \d+\.?\d*           |   # nombres (entiers ou décimaux)
    [+\-*/^().]         |   # opérateurs et parenthèses
    pi | e              |   # constantes
    sqrt|log10|log|ln   |   # fonctions root/log
    sin|cos|tan         |   # fonctions trigo
    factorial           |   # factorielle
    \s+                     # espaces (ignorés)
    """,
    re.VERBOSE,
)

_SAFE_MATH = {
    "sqrt":      math.sqrt,
    "log10":     math.log10,
    "log":       math.log10,
    "ln":        math.log,
    "sin":       lambda x: math.sin(math.radians(x)),
    "cos":       lambda x: math.cos(math.radians(x)),
    "tan":       lambda x: math.tan(math.radians(x)),
    "factorial": math.factorial,
    "pi":        math.pi,
    "e":         math.e,
    "__builtins__": {},
}

def safe_eval(expression: str) -> float | str:
    """
    Évalue une expression mathématique de façon sécurisée.
    Retourne le résultat (float/int) ou la chaîne "Erreur".
    """
    if len(expression) > 200:
        return "Erreur"

    tokens = _SAFE_TOKEN_RE.findall(expression)
    reconstructed = "".join(tokens)
    if reconstructed.replace(" ", "") != expression.replace(" ", ""):
        return "Erreur"

    try:
        expr = (
            expression
            .replace("^", "**")
            .replace("π", "pi")
        )
        expr = re.sub(r"(\d+)!", r"factorial(\1)", expr)

        open_count  = expr.count("(")
        close_count = expr.count(")")
        if open_count < close_count:
            return "Erreur"
        expr += ")" * (open_count - close_count)

        result = eval(expr, {"__builtins__": {}}, _SAFE_MATH)  # noqa: S307

        if isinstance(result, float):
            rounded = round(result, 10)
            if rounded == int(rounded):
                return int(rounded)
            return rounded

        return result

    except Exception:
        return "Erreur"


# ────────────────────────────────────────────────────────────────────────────────
# 🖥️ Affichage
# ────────────────────────────────────────────────────────────────────────────────

MAX_EXPR_LEN = 24

def build_display(expression: str, result) -> str:
    expr_line   = expression[-MAX_EXPR_LEN:] if len(expression) > MAX_EXPR_LEN else expression
    result_line = str(result) if result is not None else ""
    result_line = result_line[:MAX_EXPR_LEN]

    return (
        "```\n"
        "╔══════════════════════════╗\n"
        f"║ {expr_line:<{MAX_EXPR_LEN}} ║\n"
        f"║ = {result_line:<{MAX_EXPR_LEN - 2}} ║\n"
        "╚══════════════════════════╝\n"
        "```"
    )


# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ UI — Mini-clavier interactif (25 boutons max — limite Discord)
# ────────────────────────────────────────────────────────────────────────────────

class CalculatorView(View):
    def __init__(self):
        super().__init__(timeout=180)
        self.expression: str    = ""
        self.result:     object = None
        self._add_buttons()

    def _add_buttons(self):
        # 5 rangées × 5 colonnes = 25 boutons exactement
        rows = [
            ["sin", "cos", "tan", "sqrt", "^"],
            ["7",   "8",   "9",   "/",    "ln"],
            ["4",   "5",   "6",   "*",    "π"],
            ["1",   "2",   "3",   "-",    "⌫"],
            ["C",   "0",   ".",   "+",    "="],
        ]
        styles = {
            "=": discord.ButtonStyle.success,
            "C": discord.ButtonStyle.danger,
            "⌫": discord.ButtonStyle.danger,
        }
        for row in rows:
            for label in row:
                style = styles.get(label, discord.ButtonStyle.secondary)
                self.add_item(CalcButton(label, self, style))


class CalcButton(Button):
    _FUNCTIONS = {"sin", "cos", "tan", "sqrt", "log", "ln"}
    _OPERATORS  = {"+", "-", "*", "/", "^"}

    def __init__(self, label: str, parent_view: CalculatorView, style):
        super().__init__(label=label, style=style)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        view  = self.parent_view
        label = self.label

        if label == "C":
            view.expression = ""
            view.result = None

        elif label == "⌫":
            if view.result is not None:
                view.result = None
                view.expression = ""
            elif view.expression:
                view.expression = re.sub(r"(sin|cos|tan|sqrt|log|ln|\()$|.$", "", view.expression)

        elif label == "=":
            if view.expression:
                view.result = safe_eval(view.expression)

        elif label in self._OPERATORS:
            if view.result not in (None, "Erreur"):
                view.expression = str(view.result) + label
                view.result = None
            elif view.result != "Erreur":
                view.expression += label

        else:
            if view.result not in (None, "Erreur"):
                view.expression = ""
                view.result = None

            if label in self._FUNCTIONS:
                view.expression += label + "("
            elif label == "π":
                view.expression += "pi"
            else:
                view.expression += label

        display = build_display(view.expression, view.result)
        try:
            await safe_edit(interaction.message, content=display, view=view)
        except Exception as exc:
            log.exception("Erreur affichage calculatrice : %s", exc)


# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────

class ScientificCalculator(commands.Cog):
    """Commandes /calc et !calc — Calculatrice scientifique interactive."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _send_calculator(self, channel: discord.abc.Messageable) -> discord.Message:
        view    = CalculatorView()
        display = build_display("", None)
        message = await safe_send(channel, display, view=view)
        view.message = message
        return message

    @app_commands.command(name="calc", description="Calculatrice scientifique interactive")
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_calc(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)
            await self._send_calculator(interaction.channel)
            await interaction.delete_original_response()
        except Exception as exc:
            log.exception("[/calc] Erreur inattendue : %s", exc)
            await safe_respond(interaction, "❌ Une erreur est survenue.", ephemeral=True)

    @slash_calc.error
    async def slash_calc_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            await safe_respond(interaction, f"⏳ Attends encore {error.retry_after:.1f}s.", ephemeral=True)
        else:
            log.exception("[/calc] Erreur non gérée : %s", error)
            await safe_respond(interaction, "❌ Une erreur est survenue.", ephemeral=True)

    @commands.command(name="calc", help="Calculatrice scientifique interactive")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_calc(self, ctx: commands.Context):
        try:
            await self._send_calculator(ctx.channel)
        except Exception as exc:
            log.exception("[!calc] Erreur inattendue : %s", exc)
            await safe_send(ctx.channel, "❌ Une erreur est survenue.")

    @prefix_calc.error
    async def prefix_calc_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.CommandOnCooldown):
            await safe_send(ctx.channel, f"⏳ Attends encore {error.retry_after:.1f}s.")
        else:
            log.exception("[!calc] Erreur non gérée : %s", error)
            await safe_send(ctx.channel, "❌ Une erreur est survenue.")


# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────

async def setup(bot: commands.Bot):
    cog = ScientificCalculator(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Fun&Random"
    await bot.add_cog(cog)
