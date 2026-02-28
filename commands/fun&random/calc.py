# ────────────────────────────────────────────────────────────────────────────────
# 📌 scientific_calculator.py — Calculatrice scientifique interactive
# Objectif : Calculatrice scientifique interactive avec mini-clavier et fonctions avancées
# Catégorie : Fun&Random
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
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

# Tokens autorisés : chiffres, opérateurs, fonctions math, constantes
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
    "log":       math.log10,   # alias pour "log" bouton
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
    # Vérification de la longueur pour éviter les abus
    if len(expression) > 200:
        return "Erreur"

    # Reconstruction tokenisée : on rejette tout token non reconnu
    tokens = _SAFE_TOKEN_RE.findall(expression)
    reconstructed = "".join(tokens)
    if reconstructed.replace(" ", "") != expression.replace(" ", ""):
        return "Erreur"

    try:
        # Conversions syntaxiques
        expr = (
            expression
            .replace("^", "**")
            .replace("π", "pi")
            # Factorielle : transformer "5!" → "factorial(5)" via regex
        )

        # Gérer la notation postfixe "N!" → "factorial(N)"
        expr = re.sub(r"(\d+)!", r"factorial(\1)", expr)

        # Équilibrer les parenthèses manquantes (côté droit uniquement)
        open_count  = expr.count("(")
        close_count = expr.count(")")
        if open_count < close_count:
            return "Erreur"  # parenthèse fermante sans ouvrante → expression invalide
        expr += ")" * (open_count - close_count)

        result = eval(expr, {"__builtins__": {}}, _SAFE_MATH)  # noqa: S307

        # Arrondi propre pour éviter les 0.9999999999
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

MAX_EXPR_LEN = 24  # largeur de l'écran ASCII

def build_display(expression: str, result) -> str:
    """Construit l'écran ASCII de la calculatrice."""
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
# 🎛️ UI — Mini-clavier interactif
# ────────────────────────────────────────────────────────────────────────────────

class CalculatorView(View):
    def __init__(self):
        super().__init__(timeout=180)
        self.expression: str       = ""
        self.result:     object    = None
        self._add_buttons()

    def _add_buttons(self):
        # Disposition du clavier
        rows = [
            ["7",   "8",   "9",   "/",   "sqrt"],
            ["4",   "5",   "6",   "*",   "^"],
            ["1",   "2",   "3",   "-",   "ln"],
            ["0",   ".",   "C",   "+",   "log"],
            ["(",   ")",   "⌫",   "!",   "="],
            ["sin", "cos", "tan", "π",   ""],
        ]
        styles = {
            "=":   discord.ButtonStyle.success,
            "C":   discord.ButtonStyle.danger,
            "⌫":   discord.ButtonStyle.danger,
        }
        for row in rows:
            for label in row:
                if label == "":
                    continue  # case vide → pas de bouton
                style = styles.get(label, discord.ButtonStyle.secondary)
                self.add_item(CalcButton(label, self, style))


class CalcButton(Button):
    # Fonctions qui nécessitent une parenthèse ouvrante
    _FUNCTIONS = {"sin", "cos", "tan", "sqrt", "log", "ln"}
    # Opérateurs binaires
    _OPERATORS = {"+", "-", "*", "/", "^"}

    def __init__(self, label: str, parent_view: CalculatorView, style):
        super().__init__(label=label, style=style)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        view  = self.parent_view
        label = self.label

        if label == "C":
            # Réinitialisation complète
            view.expression = ""
            view.result = None

        elif label == "⌫":
            # Suppression du dernier caractère (ou token de fonction)
            if view.result is not None:
                # Backspace après un résultat → efface le résultat
                view.result = None
                view.expression = ""
            elif view.expression:
                # Retirer le dernier token (fonction multi-char ou caractère)
                view.expression = re.sub(r"(sin|cos|tan|sqrt|log|ln|\()$|.$", "", view.expression)

        elif label == "=":
            if view.expression:
                view.result = safe_eval(view.expression)

        elif label in self._OPERATORS:
            # Opérateur : on continue depuis le résultat précédent si disponible
            if view.result not in (None, "Erreur"):
                view.expression = str(view.result) + label
                view.result = None
            elif view.result == "Erreur":
                pass  # on ignore, l'utilisateur doit faire C d'abord
            else:
                view.expression += label

        else:
            # Chiffre, fonction, constante, parenthèse, "!"
            if view.result not in (None, "Erreur"):
                # Nouveau calcul : on repart de zéro
                view.expression = ""
                view.result = None

            if label in self._FUNCTIONS:
                view.expression += label + "("
            elif label == "π":
                view.expression += "pi"
            elif label == "!":
                # Factorielle postfixe : on l'ajoute directement
                view.expression += "!"
            else:
                view.expression += label

        display = build_display(view.expression, view.result)
        try:
            await safe_edit(interaction.message, content=display, view=view)
        except Exception as exc:
            log.exception("Erreur lors de la mise à jour de l'affichage : %s", exc)


# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────

class ScientificCalculator(commands.Cog):
    """
    Commandes /calc et !calc — Calculatrice scientifique interactive avec mini-clavier.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── Méthode partagée ────────────────────────────────────────────────────────
    async def _send_calculator(self, channel: discord.abc.Messageable) -> discord.Message:
        view    = CalculatorView()
        display = build_display("", None)
        message = await safe_send(channel, display, view=view)
        view.message = message
        return message

    # ── Commande SLASH ──────────────────────────────────────────────────────────
    @app_commands.command(
        name="calc",
        description="Calculatrice scientifique interactive",
    )
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
            await safe_respond(
                interaction,
                f"⏳ Attends encore {error.retry_after:.1f}s.",
                ephemeral=True,
            )
        else:
            log.exception("[/calc] Erreur non gérée : %s", error)
            await safe_respond(interaction, "❌ Une erreur est survenue.", ephemeral=True)

    # ── Commande PREFIX ─────────────────────────────────────────────────────────
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
