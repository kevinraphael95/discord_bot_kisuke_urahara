# ================================================================================
# 📌 matrices.py — Commande /matrices et !matrices
# Objectif : Résoudre un calcul sur des matrices (déterminant, somme, produit...)
# Catégorie : Jeux
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# Modes : Facile (det 2x2) / Moyen (A+B, A-B, k×A) / Hard (A×B 2x2 ou det 3x3)
# ================================================================================

# ================================================================================
# 📦 Imports nécessaires
# ================================================================================
import asyncio
import logging
import random
import re
from typing import Literal

import discord
from discord import app_commands
from discord.ext import commands

from utils.discord_utils import safe_edit, safe_respond, safe_send
from utils.jeux_utils import BuzzerView, ReplyView, parse_mode

log = logging.getLogger(__name__)

# ================================================================================
# 🔧 Helpers — calcul matriciel
# ================================================================================
Matrix = list[list[int]]


def rand_matrix(rows: int, cols: int, lo: int, hi: int) -> Matrix:
    return [[random.randint(lo, hi) for _ in range(cols)] for _ in range(rows)]


def det2(m: Matrix) -> int:
    return m[0][0] * m[1][1] - m[0][1] * m[1][0]


def det3(m: Matrix) -> int:
    a, b, c = m[0]
    d, e, f = m[1]
    g, h, i = m[2]
    return a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)


def mat_add(a: Matrix, b: Matrix) -> Matrix:
    return [[x + y for x, y in zip(ra, rb)] for ra, rb in zip(a, b)]


def mat_sub(a: Matrix, b: Matrix) -> Matrix:
    return [[x - y for x, y in zip(ra, rb)] for ra, rb in zip(a, b)]


def mat_scal(k: int, a: Matrix) -> Matrix:
    return [[k * x for x in row] for row in a]


def mat_mul(a: Matrix, b: Matrix) -> Matrix:
    return [
        [sum(a[i][k] * b[k][j] for k in range(len(b))) for j in range(len(b[0]))]
        for i in range(len(a))
    ]


def flatten(m: Matrix) -> list[int]:
    return [x for row in m for x in row]


# ================================================================================
# 🔧 Helpers — affichage
# ================================================================================
def _render(m: Matrix, w: int) -> list[str]:
    return ["| " + "  ".join(str(x).rjust(w) for x in row) + " |" for row in m]


def render_expr(parts: list) -> str:
    """
    Affiche une expression côte à côte. `parts` = liste de matrices et d'opérateurs (str).
    Ex : [A, "+", B] ou ["det", A].
    """
    w = max(len(str(x)) for p in parts if isinstance(p, list) for row in p for x in row)
    blocks: list[list[str]] = []
    for p in parts:
        if isinstance(p, list):
            blocks.append(_render(p, w))
        else:
            blocks.append([p])  # opérateur, placé plus tard

    height = max(len(b) for p, b in zip(parts, blocks) if isinstance(p, list))
    lines = [""] * height
    mid = height // 2

    for p, block in zip(parts, blocks):
        if isinstance(p, list):
            width = len(block[0])
            for i in range(height):
                lines[i] += block[i] if i < len(block) else " " * width
        else:
            width = len(p) + 2
            for i in range(height):
                lines[i] += (" " + p + " ") if i == mid else " " * width
    return "\n".join(line.rstrip() for line in lines)


def fmt_answer_input(vals: list[int]) -> str:
    return " ".join(str(v) for v in vals)


def parse_answer(text: str) -> list[int] | None:
    """Extrait tous les entiers (accepte « − » et séparateurs variés)."""
    cleaned = text.replace("−", "-").replace("–", "-")
    nums = re.findall(r"-?\d+", cleaned)
    if not nums:
        return None
    return [int(x) for x in nums]


# ================================================================================
# 🎲 Génération de question
# ================================================================================
def pick_question(difficulty: str = "hard") -> dict:
    """
    Retourne un dict :
      display      → expression à afficher (bloc de code)
      instruction  → consigne
      expected     → liste d'entiers attendue (ligne par ligne pour une matrice)
      answer_text  → réponse formatée pour l'affichage final
      label        → label du modal
      placeholder  → placeholder du modal
    """
    if difficulty == "easy":
        a = rand_matrix(2, 2, -5, 9)
        res = det2(a)
        return {
            "display": render_expr(["det", a]),
            "instruction": "Calcule le déterminant (ad − bc).",
            "expected": [res],
            "answer_text": f"**`{res}`**",
            "label": "Le déterminant",
            "placeholder": "Ex : -7",
        }

    if difficulty == "medium":
        a = rand_matrix(2, 2, -5, 9)
        op = random.choice(["+", "-", "k"])
        if op == "k":
            k = random.randint(2, 4)
            res = mat_scal(k, a)
            display = render_expr([f"{k} ×", a])
            instr = f"Calcule {k}×A."
        else:
            b = rand_matrix(2, 2, -5, 9)
            res = mat_add(a, b) if op == "+" else mat_sub(a, b)
            display = render_expr([a, op, b])
            instr = "Calcule A + B." if op == "+" else "Calcule A − B."
        return _matrix_answer(display, instr, res)

    # hard
    if random.random() < 0.5:
        a = rand_matrix(2, 2, -4, 6)
        b = rand_matrix(2, 2, -4, 6)
        res = mat_mul(a, b)
        return _matrix_answer(render_expr([a, "×", b]), "Calcule le produit A × B.", res)

    a = rand_matrix(3, 3, -3, 5)
    res = det3(a)
    return {
        "display": render_expr(["det", a]),
        "instruction": "Calcule le déterminant 3×3.",
        "expected": [res],
        "answer_text": f"**`{res}`**",
        "label": "Le déterminant",
        "placeholder": "Ex : 42",
    }


def _matrix_answer(display: str, instruction: str, res: Matrix) -> dict:
    flat = flatten(res)
    rows, cols = len(res), len(res[0])
    return {
        "display": display,
        "instruction": f"{instruction} Réponds ligne par ligne ({rows}×{cols} = {rows * cols} nombres).",
        "expected": flat,
        "answer_text": "\n```\n" + render_expr([res]) + "\n```",
        "label": "Ligne par ligne (ex : 1 2 3 4)",
        "placeholder": "Ex : 1 2 3 4",
    }


# ================================================================================
# 🎛️ Menu de choix de difficulté (dans le même message)
# ================================================================================
class DifficultyButton(discord.ui.Button):
    def __init__(self, label: str, difficulty: str, cog, author_id: int, multi: bool):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.difficulty = difficulty
        self.cog = cog
        self.author_id = author_id
        self.multi = multi

    async def callback(self, interaction: discord.Interaction):
        if not self.multi and interaction.user.id != self.author_id:
            await safe_respond(interaction, "❌ Ce n'est pas ta partie.", ephemeral=True)
            return
        try:
            await interaction.response.defer()
        except Exception:
            pass
        await self.cog._start_game(
            interaction.channel,
            self.author_id,
            self.multi,
            difficulty=self.difficulty,
            edit_message=interaction.message,
        )


class DifficultyView(discord.ui.View):
    def __init__(self, cog, author_id: int, multi: bool, timeout: int = 60):
        super().__init__(timeout=timeout)
        self.add_item(DifficultyButton("🟢 Facile (det 2×2)", "easy", cog, author_id, multi))
        self.add_item(DifficultyButton("🟡 Moyen (+ − ×k)", "medium", cog, author_id, multi))
        self.add_item(DifficultyButton("🔴 Hard (produit / det 3×3)", "hard", cog, author_id, multi))


# ================================================================================
# 🧠 Cog principal
# ================================================================================
class Matrices(commands.Cog):
    """Commande /matrices et !matrices — Calcul matriciel."""

    DURATION = 150
    MAX_ATTEMPTS_SOLO = 3

    DIFF_LABELS = {
        "easy": "🟢 Facile",
        "medium": "🟡 Moyen",
        "hard": "🔴 Hard",
    }

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ============================================================================
    # 🎯 Menu de difficulté (envoie UN SEUL message)
    # ============================================================================
    async def _show_difficulty_menu(self, channel, author_id: int, multi: bool):
        embed = discord.Embed(
            title="🧮 Matrices",
            description=(
                "Choisis ton mode de jeu :\n\n"
                "🟢 **Facile** — déterminant d'une matrice **2×2**\n"
                "🟡 **Moyen** — **A + B**, **A − B** ou **k × A** (2×2)\n"
                "🔴 **Hard** — **produit 2×2** ou **déterminant 3×3**"
            ),
            color=discord.Color.orange(),
        )
        view = DifficultyView(self, author_id, multi)
        await safe_send(channel, embed=embed, view=view)

    # ============================================================================
    # 🎮 Logique de jeu
    # ============================================================================
    async def _start_game(
        self,
        channel: discord.abc.Messageable,
        author_id: int,
        multi: bool = False,
        difficulty: str = "hard",
        edit_message: discord.Message | None = None,
    ):
        q = pick_question(difficulty)
        expected: list[int] = q["expected"]

        attempts: list[dict] = []
        state = {"finished": False}
        start_time = asyncio.get_event_loop().time()

        diff_txt = self.DIFF_LABELS.get(difficulty, "🔴 Hard")

        def build_embed(
            winner: str | None = None,
            finished: bool = False,
            timed_out: bool = False,
        ) -> discord.Embed:
            mode_txt = "Multi 🌍" if multi else "Solo 🧍"
            title = f"🧮 Matrices — {diff_txt} — {mode_txt}"

            if finished:
                color = discord.Color.green() if winner else discord.Color.red()
            else:
                color = discord.Color.blurple()

            embed = discord.Embed(
                title=title,
                description=f"```\n{q['display']}\n```\n**{q['instruction']}**",
                color=color,
            )

            if not multi:
                embed.add_field(
                    name=f"Essais ({len(attempts)}/{self.MAX_ATTEMPTS_SOLO})",
                    value="\n".join(
                        f"{a['author']}: **{a['word']}** {'✅' if a['correct'] else '❌'}"
                        for a in attempts
                    ) or "_Aucun essai pour l'instant._",
                    inline=False,
                )
            elif attempts:
                embed.add_field(
                    name="Essais",
                    value="\n".join(
                        f"{a['author']}: **{a['word']}** {'✅' if a['correct'] else '❌'}"
                        for a in attempts
                    ),
                    inline=False,
                )

            if finished:
                if winner:
                    result_txt = f"🏆 **{winner}** a trouvé !\n✅ Réponse : {q['answer_text']}"
                else:
                    prefix = "⏰ Temps écoulé !" if timed_out else "❌ Personne n'a trouvé."
                    result_txt = f"{prefix}\n✅ Réponse : {q['answer_text']}"
                embed.add_field(name="🏁 Résultat", value=result_txt, inline=False)
                embed.set_footer(text="Partie terminée")
            else:
                elapsed = int(asyncio.get_event_loop().time() - start_time)
                remaining = max(0, self.DURATION - elapsed)
                embed.set_footer(text=f"⏱️ Temps restant : {remaining}s")

            return embed

        async def finish(winner: str | None, timed_out: bool = False):
            state["finished"] = True
            final_embed = build_embed(winner=winner, finished=True, timed_out=timed_out)
            await view.mark_finished(embed=final_embed)

        # ── Soumission de réponse ──
        async def on_submit(interaction: discord.Interaction, answer: str):
            if not interaction.response.is_done():
                await interaction.response.defer()
            if state["finished"]:
                return
            if not multi and interaction.user.id != author_id:
                return

            vals = parse_answer(answer)
            if vals is None or len(vals) != len(expected):
                # Format invalide : on ne consomme pas d'essai
                try:
                    await interaction.followup.send(
                        f"❌ Il faut exactement **{len(expected)}** nombre(s), séparés par des espaces.",
                        ephemeral=True,
                    )
                except Exception:
                    pass
                return

            guess_txt = fmt_answer_input(vals)

            if any(a["word"] == guess_txt for a in attempts):
                if view.message:
                    await safe_edit(view.message, embed=build_embed())
                return

            correct = vals == expected
            attempts.append({"author": interaction.user.display_name, "word": guess_txt, "correct": correct})

            if correct:
                await finish(interaction.user.mention)
            elif not multi and len(attempts) >= self.MAX_ATTEMPTS_SOLO:
                await finish(None)
            elif view.message:
                await safe_edit(view.message, embed=build_embed())

        # ── Buzz (multi) ──
        async def on_buzz(user: discord.User | discord.Member):
            if view.message:
                for child in view.children:
                    if isinstance(child, discord.ui.Button):
                        child.disabled = True
                elapsed = int(asyncio.get_event_loop().time() - start_time)
                remaining = max(0, self.DURATION - elapsed)
                emb = build_embed()
                emb.set_footer(text=f"🎯 Main prise par {user.display_name} | ⏱️ {remaining}s")
                await safe_edit(view.message, embed=emb, view=view)

        # ── Création de la view ──
        if multi:
            view = BuzzerView(
                modal_title="🧮 Ta réponse",
                modal_label=q["label"],
                modal_placeholder=q["placeholder"],
                modal_max_length=40,
                on_submit=on_submit,
                on_buzz=on_buzz,
                buzz_timeout=45,
                view_timeout=300,
            )
        else:
            view = ReplyView(
                user_id=author_id,
                modal_title="🧮 Ta réponse",
                modal_label=q["label"],
                modal_placeholder=q["placeholder"],
                modal_max_length=40,
                on_submit=on_submit,
                timeout=300,
            )

        # ✅ Si edit_message fourni : on édite le message existant (menu)
        if edit_message is not None:
            view.message = edit_message
            await safe_edit(edit_message, embed=build_embed(), view=view)
        else:
            view.message = await safe_send(channel, embed=build_embed(), view=view)
            if view.message is None:
                return

        try:
            await asyncio.sleep(self.DURATION)
        except asyncio.CancelledError:
            return

        if state["finished"]:
            return

        await finish(None, timed_out=True)

    # ============================================================================
    # 🔹 Commande SLASH
    # ============================================================================
    @app_commands.command(
        name="matrices",
        description="Résous un calcul sur des matrices (déterminant, somme, produit).",
    )
    @app_commands.describe(mode="solo ou multi (tout le monde peut jouer)")
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_matrices(
        self,
        interaction: discord.Interaction,
        mode: Literal["solo", "multi"] = "solo",
    ):
        await interaction.response.defer()
        await self._show_difficulty_menu(
            interaction.channel, author_id=interaction.user.id, multi=parse_mode(mode)
        )
        await interaction.delete_original_response()

    # ============================================================================
    # 🔹 Commande PREFIX
    # ============================================================================
    @commands.command(
        name="matrices",
        aliases=["mat", "matrice"],
        help="Résous un calcul sur des matrices. Ajoute 'm' ou 'multi' pour jouer en multi.",
    )
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_matrices(self, ctx: commands.Context, *, arg: str = None):
        tokens = (arg or "").lower().split()
        multi = any(parse_mode(t) for t in tokens)
        await self._show_difficulty_menu(ctx.channel, author_id=ctx.author.id, multi=multi)


# ================================================================================
# 🔌 Setup du Cog
# ================================================================================
async def setup(bot: commands.Bot):
    cog = Matrices(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Jeux"
    await bot.add_cog(cog)
