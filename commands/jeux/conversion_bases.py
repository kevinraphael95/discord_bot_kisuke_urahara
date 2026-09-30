# ================================================================================
# 📌 conversion_bases.py — Commande /conversion_bases et !conversion_bases
# Objectif : Convertir un nombre d'une base (2-10) vers une autre (2-10)
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
from typing import Literal, NamedTuple

import discord
from discord import app_commands
from discord.ext import commands

from utils.discord_utils import safe_edit, safe_respond, safe_send
from utils.jeux_utils import BuzzerView, ReplyView, parse_mode

log = logging.getLogger(__name__)

# ================================================================================
# 🔧 Helpers
# ================================================================================
DIGITS = "0123456789"

def to_base(n: int, base: int) -> str:
    """Convertit un entier en chaîne dans la base donnée (2-10)."""
    if n == 0:
        return "0"
    out = []
    while n > 0:
        out.append(DIGITS[n % base])
        n //= base
    return "".join(reversed(out))


def from_base(s: str, base: int) -> int | None:
    """Convertit une chaîne (base 2-10) en entier. None si invalide."""
    s = s.strip().lower()
    if not s:
        return None
    for ch in s:
        if ch not in DIGITS[:base]:
            return None
    try:
        return int(s, base)
    except ValueError:
        return None


def pick_question(min_base: int = 2, max_base: int = 10) -> tuple[int, int, int, str, str]:
    """
    Tire un nombre et 2 bases différentes.
    Retourne (n, src_base, dst_base, src_str, dst_str).
    """
    src_base = random.randint(min_base, max_base)
    dst_base = random.choice([b for b in range(min_base, max_base + 1) if b != src_base])

    # Taille du nombre adaptée : plus la base est petite, plus on prend de chiffres
    length = random.randint(3, 5) if src_base <= 4 else random.randint(2, 4)
    max_val = src_base ** length - 1
    min_val = src_base ** (length - 1) if length > 1 else 0
    n = random.randint(min_val, max_val)

    return n, src_base, dst_base, to_base(n, src_base), to_base(n, dst_base)


# ================================================================================
# 🧠 Cog principal
# ================================================================================
class ConversionBases(commands.Cog):
    """Commande /conversion_bases et !conversion_bases — Convertir entre bases 2 à 10."""

    DURATION = 120  # secondes par question
    MAX_ATTEMPTS_SOLO = 3

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ============================================================================
    # 🎮 Logique de jeu
    # ============================================================================
    async def _start_game(self, channel: discord.abc.Messageable, author_id: int, multi: bool = False):
        n, src_base, dst_base, src_str, dst_str = pick_question()

        attempts: list[dict] = []
        state = {"finished": False}
        start_time = asyncio.get_event_loop().time()

        def build_embed(winner: str | None = None, finished: bool = False) -> discord.Embed:
            mode_txt = "Multi 🌍" if multi else "Solo 🧍"
            title = f"🔢 Conversion de bases — {mode_txt}"

            if finished:
                if winner:
                    embed = discord.Embed(
                        title=f"{title} — Gagné !",
                        description=(
                            f"🏆 **{winner}** a trouvé !\n"
                            f"✅ Réponse : **`{dst_str}`** (base {dst_base})\n"
                            f"🔎 `{src_str}` (base {src_base}) = `{n}` en décimal"
                        ),
                        color=discord.Color.green(),
                    )
                else:
                    embed = discord.Embed(
                        title=f"{title} — Perdu",
                        description=(
                            f"❌ Personne n'a trouvé.\n"
                            f"✅ Réponse : **`{dst_str}`** (base {dst_base})\n"
                            f"🔎 `{src_str}` (base {src_base}) = `{n}` en décimal"
                        ),
                        color=discord.Color.red(),
                    )
                embed.set_footer(text="Partie terminée")
                return embed

            embed = discord.Embed(
                title=title,
                description=(
                    f"Convertis le nombre suivant :\n\n"
                    f"**`{src_str}`** (base **{src_base}**)  →  base **{dst_base}**"
                ),
                color=discord.Color.blurple(),
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
            else:
                if attempts:
                    embed.add_field(
                        name="Essais",
                        value="\n".join(
                            f"{a['author']}: **{a['word']}** {'✅' if a['correct'] else '❌'}"
                            for a in attempts
                        ),
                        inline=False,
                    )

            elapsed = int(asyncio.get_event_loop().time() - start_time)
            remaining = max(0, self.DURATION - elapsed)
            embed.set_footer(text=f"⏱️ Temps restant : {remaining}s")
            return embed

        async def finish(winner: str | None):
            state["finished"] = True
            await view.mark_finished(embed=build_embed(winner=winner, finished=True))

        # ── Soumission de réponse (mode texte / modal) ──
        async def on_submit(interaction: discord.Interaction, answer: str):
            if not interaction.response.is_done():
                await interaction.response.defer()
            if state["finished"]:
                return
            if not multi and interaction.user.id != author_id:
                return

            guess = answer.strip()
            if not guess:
                return

            # Anti-doublon
            if any(a["word"] == guess for a in attempts):
                if view.message:
                    await safe_edit(view.message, embed=build_embed())
                return

            correct = guess == dst_str
            attempts.append({"author": interaction.user.display_name, "word": guess, "correct": correct})

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
                modal_title="🔢 Ta réponse",
                modal_label=f"En base {dst_base}",
                modal_placeholder=f"Ex : 1010",
                modal_max_length=20,
                on_submit=on_submit,
                on_buzz=on_buzz,
                buzz_timeout=45,
                view_timeout=300,
            )
        else:
            view = ReplyView(
                user_id=author_id,
                modal_title="🔢 Ta réponse",
                modal_label=f"En base {dst_base}",
                modal_placeholder=f"Ex : 1010",
                modal_max_length=20,
                on_submit=on_submit,
                timeout=300,
            )

        view.message = await safe_send(channel, embed=build_embed(), view=view)
        if view.message is None:
            return

        # ── Attente / timeout ──
        try:
            await asyncio.sleep(self.DURATION)
        except asyncio.CancelledError:
            return

        if state["finished"]:
            return

        # Temps écoulé
        final = build_embed(winner=None, finished=True)
        final.title = "⏰ Temps écoulé !"
        await view.mark_finished(embed=final)

    # ============================================================================
    # 🔹 Commande SLASH
    # ============================================================================
    @app_commands.command(
        name="conversion_bases",
        description="Convertis un nombre d'une base (2-10) vers une autre (2-10).",
    )
    @app_commands.describe(mode="solo ou multi (tout le monde peut jouer)")
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_conversion(
        self,
        interaction: discord.Interaction,
        mode: Literal["solo", "multi"] = "solo",
    ):
        await interaction.response.defer()
        await self._start_game(interaction.channel, author_id=interaction.user.id, multi=parse_mode(mode))
        await interaction.delete_original_response()

    # ============================================================================
    # 🔹 Commande PREFIX
    # ============================================================================
    @commands.command(
        name="conversion_bases",
        aliases=["cb", "base"],
        help="Convertis un nombre entre bases 2 et 10. Ajoute 'm' ou 'multi' pour jouer en multi.",
    )
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_conversion(self, ctx: commands.Context, *, arg: str = None):
        tokens = (arg or "").lower().split()
        multi = any(parse_mode(t) for t in tokens)
        await self._start_game(ctx.channel, author_id=ctx.author.id, multi=multi)


# ================================================================================
# 🔌 Setup du Cog
# ================================================================================
async def setup(bot: commands.Bot):
    cog = ConversionBases(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Jeux"
    await bot.add_cog(cog)
