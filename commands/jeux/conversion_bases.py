# ================================================================================
# 📌 conversion_bases.py — Commande /conversion_bases et !conversion_bases
# Objectif : Convertir un nombre d'une base (2-10) vers une autre (2-10)
# Catégorie : Jeux
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# Modes : Facile (→ base 10) / Hard (base 2-10 vers base 2-10)
# ================================================================================

# ================================================================================
# 📦 Imports nécessaires
# ================================================================================
import asyncio
import logging
import random
from typing import Literal

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


def pick_question(difficulty: str = "hard") -> tuple[int, int, int, str, str]:
    """
    Tire un nombre et 2 bases.
    - difficulté "easy" : source ∈ 2-9, cible = 10 (toujours)
    - difficulté "hard" : source ∈ 2-10, cible ∈ 2-10, différentes
    Retourne (n, src_base, dst_base, src_str, dst_str).
    """
    if difficulty == "easy":
        src_base = random.randint(2, 9)
        dst_base = 10
    else:  # hard
        src_base = random.randint(2, 10)
        dst_base = random.choice([b for b in range(2, 11) if b != src_base])

    length = random.randint(3, 5) if src_base <= 4 else random.randint(2, 4)
    max_val = src_base ** length - 1
    min_val = src_base ** (length - 1) if length > 1 else 0
    n = random.randint(min_val, max_val)

    return n, src_base, dst_base, to_base(n, src_base), to_base(n, dst_base)


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
        # ✅ On lance la partie DANS LE MÊME message (pas de nouveau message)
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
        self.add_item(DifficultyButton("🟢 Facile (→ base 10)", "easy", cog, author_id, multi))
        self.add_item(DifficultyButton("🔴 Hard (base → base)", "hard", cog, author_id, multi))


# ================================================================================
# 🧠 Cog principal
# ================================================================================
class ConversionBases(commands.Cog):
    """Commande /conversion_bases et !conversion_bases — Convertir entre bases 2 à 10."""

    DURATION = 120
    MAX_ATTEMPTS_SOLO = 3

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ============================================================================
    # 🎯 Menu de difficulté (envoie UN SEUL message)
    # ============================================================================
    async def _show_difficulty_menu(self, channel, author_id: int, multi: bool):
        embed = discord.Embed(
            title="🔢 Conversion de bases",
            description=(
                "Choisis ton mode de jeu :\n\n"
                "🟢 **Facile** — convertis un nombre (base 2-9) en **base 10**\n"
                "🔴 **Hard** — convertis un nombre entre **deux bases** (2-10)"
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
        n, src_base, dst_base, src_str, dst_str = pick_question(difficulty)

        attempts: list[dict] = []
        state = {"finished": False}
        start_time = asyncio.get_event_loop().time()

        diff_txt = "🟢 Facile" if difficulty == "easy" else "🔴 Hard"

        def build_embed(
            winner: str | None = None,
            finished: bool = False,
            timed_out: bool = False,
        ) -> discord.Embed:
            mode_txt = "Multi 🌍" if multi else "Solo 🧍"
            title = f"🔢 Conversion de bases — {diff_txt} — {mode_txt}"

            if finished:
                color = discord.Color.green() if winner else discord.Color.red()
            else:
                color = discord.Color.blurple()

            embed = discord.Embed(
                title=title,
                description=(
                    f"# `{src_str}` (base {src_base})  →  base {dst_base}\n"
                    f"**Convertis ce nombre dans la base demandée.**"
                ),
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
                    result_txt = (
                        f"🏆 **{winner}** a trouvé !\n"
                        f"✅ Réponse : **`{dst_str}`** (base {dst_base})"
                    )
                    if difficulty == "hard":
                        result_txt += f"\n🔎 `{src_str}` (base {src_base}) = `{n}` en décimal"
                else:
                    prefix = "⏰ Temps écoulé !" if timed_out else "❌ Personne n'a trouvé."
                    result_txt = (
                        f"{prefix}\n"
                        f"✅ Réponse : **`{dst_str}`** (base {dst_base})"
                    )
                    if difficulty == "hard":
                        result_txt += f"\n🔎 `{src_str}` (base {src_base}) = `{n}` en décimal"
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

            guess = answer.strip()
            if not guess:
                return

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
                modal_placeholder="Ex : 1010",
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
                modal_placeholder="Ex : 1010",
                modal_max_length=20,
                on_submit=on_submit,
                timeout=300,
            )

        # ✅ Si edit_message fourni : on édite le message existant (menu)
        # Sinon : on envoie un nouveau message
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
        name="conversion_bases",
        description="Convertis un nombre entre bases 2 et 10.",
    )
    @app_commands.describe(mode="solo ou multi (tout le monde peut jouer)")
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_conversion(
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
        name="conversion_bases",
        aliases=["cb", "base"],
        help="Convertis un nombre entre bases 2 et 10. Ajoute 'm' ou 'multi' pour jouer en multi.",
    )
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_conversion(self, ctx: commands.Context, *, arg: str = None):
        tokens = (arg or "").lower().split()
        multi = any(parse_mode(t) for t in tokens)
        await self._show_difficulty_menu(ctx.channel, author_id=ctx.author.id, multi=multi)


# ================================================================================
# 🔌 Setup du Cog
# ================================================================================
async def setup(bot: commands.Bot):
    cog = ConversionBases(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Jeux"
    await bot.add_cog(cog)
