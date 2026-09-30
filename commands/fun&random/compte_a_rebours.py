# ================================================================================
# 📌 compte_a_rebours.py — Commande /compte_a_rebours et !compte_a_rebours
# Objectif : Compter à rebours de 20 à 0 dans une base choisie (2-10)
# Catégorie : Fun
# Accès : Tous
# Cooldown : 1 utilisation / 15 secondes / utilisateur
# ================================================================================

# ================================================================================
# 📦 Imports nécessaires
# ================================================================================
import asyncio
import logging

import discord
from discord import app_commands
from discord.ext import commands

from utils.discord_utils import safe_edit, safe_send

log = logging.getLogger(__name__)

DIGITS = "0123456789"

# ================================================================================
# 🔧 Helpers
# ================================================================================
def to_base(n: int, base: int) -> str:
    """Convertit un entier en chaîne dans la base donnée (2-10)."""
    if n == 0:
        return "0"
    out = []
    while n > 0:
        out.append(DIGITS[n % base])
        n //= base
    return "".join(reversed(out))


# ================================================================================
# 🧠 Cog principal
# ================================================================================
class CompteARebours(commands.Cog):
    """Commande /compte_a_rebours et !compte_a_rebours — Compte à rebours en base 2-10."""

    TICK_DELAY = 1.0  # secondes entre chaque tick

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ============================================================================
    # 🎨 Construction de l'embed
    # ============================================================================
    def _build_embed(
        self,
        n: int,
        elapsed: int,
        total: int,
        base: int,
        stopped: bool = False,
        finished: bool = False,
    ) -> discord.Embed:
        ratio = elapsed / max(1, total)  # 0 → 1 au fur et à mesure

        # Couleur dynamique
        if finished:
            color = discord.Color.green()
        elif stopped:
            color = discord.Color.orange()
        elif ratio < 0.33:
            color = discord.Color.green()
        elif ratio < 0.66:
            color = discord.Color.yellow()
        else:
            color = discord.Color.red()

        # Barre de progression (20 blocs)
        filled = int(round(ratio * 20))
        bar = "█" * filled + "░" * (20 - filled)

        embed = discord.Embed(color=color)

        if finished:
            embed.title = f"🎉 Décollage ! — Base {base}"
            embed.description = (
                "Le compte à rebours est terminé.\n\n"
                "```\n"
                "  ╭─────────────────╮\n"
                "  │    🚀  0  🚀    │\n"
                "  ╰─────────────────╯\n"
                "```"
            )
        elif stopped:
            embed.title = f"⏹️ Arrêté — Base {base}"
            embed.description = (
                f"Compte à rebours interrompu à **`{to_base(n, base)}`** "
                f"(base {base} → décimal **{n}**)."
            )
        else:
            embed.title = f"⏳ Compte à rebours — Base {base}"
            # Boîte ASCII centrée (largeur 15 caractères utiles)
            display = to_base(n, base)
            pad = max(0, 11 - len(display))
            left = pad // 2
            right = pad - left
            embed.description = (
                "```\n"
                "     ┏━━━━━━━━━━━━━━━┓\n"
                "     ┃               ┃\n"
                f"     ┃{' ' * left}{display}{' ' * right}┃\n"
                "     ┃               ┃\n"
                "     ┗━━━━━━━━━━━━━━━┛\n"
                "```"
            )

        # Progression
        embed.add_field(
            name="📊 Progression",
            value=f"`{bar}`  {elapsed}/{total}",
            inline=False,
        )

        # Décimal / Base / Suivant
        embed.add_field(name="🔢 Décimal", value=f"**{n}**", inline=True)
        embed.add_field(name=f"🔠 Base {base}", value=f"**`{to_base(n, base)}`**", inline=True)

        if n > 0 and not stopped and not finished:
            embed.add_field(
                name="➡️ Suivant",
                value=f"**`{to_base(n - 1, base)}`**",
                inline=True,
            )
        else:
            embed.add_field(name="\u200b", value="\u200b", inline=True)

        # Footer
        if finished:
            embed.set_footer(text="Compte à rebours terminé ✅")
        elif stopped:
            embed.set_footer(text="Arrêté manuellement ⏹️")
        else:
            embed.set_footer(text=f"Base {base} | Tick toutes les secondes")

        return embed

    # ============================================================================
    # 🎮 Logique
    # ============================================================================
    async def _start_countdown(
        self,
        channel: discord.abc.Messageable,
        base: int,
        start: int = 20,
        author_id: int | None = None,
    ):
        view = discord.ui.View(timeout=300)
        stop_btn = discord.ui.Button(label="⏹️ Arrêter", style=discord.ButtonStyle.danger)
        stopped = {"value": False}

        async def stop_callback(interaction: discord.Interaction):
            if author_id and interaction.user.id != author_id:
                await interaction.response.send_message(
                    "❌ Ce n'est pas ton compte à rebours.", ephemeral=True
                )
                return
            stopped["value"] = True
            stop_btn.disabled = True
            await interaction.response.defer()
            await safe_edit(
                interaction.message,
                embed=self._build_embed(0, 0, start, base, stopped=True),
                view=view,
            )

        stop_btn.callback = stop_callback
        view.add_item(stop_btn)

        # Envoi initial
        msg = await safe_send(
            channel,
            embed=self._build_embed(start, 0, start, base),
            view=view,
        )
        if msg is None:
            return

        # Décompte
        for n in range(start, -1, -1):
            if stopped["value"]:
                return

            elapsed = start - n
            if n == 0:
                stop_btn.disabled = True
                await safe_edit(
                    msg,
                    embed=self._build_embed(0, start, start, base, finished=True),
                    view=view,
                )
                return

            await safe_edit(
                msg,
                embed=self._build_embed(n, elapsed, start, base),
                view=view,
            )

            try:
                await asyncio.sleep(self.TICK_DELAY)
            except asyncio.CancelledError:
                return

    # ============================================================================
    # 🔹 Commande SLASH
    # ============================================================================
    @app_commands.command(
        name="compte_a_rebours",
        description="Compte à rebours de 20 à 0 dans une base (2-10).",
    )
    @app_commands.describe(
        base="Base dans laquelle compter (2 à 10)",
        depart="Nombre de départ (par défaut 20)",
    )
    @app_commands.checks.cooldown(1, 15.0, key=lambda i: i.user.id)
    async def slash_countdown(
        self,
        interaction: discord.Interaction,
        base: app_commands.Range[int, 2, 10],
        depart: app_commands.Range[int, 1, 100] = 20,
    ):
        await interaction.response.defer()
        await self._start_countdown(
            interaction.channel,
            base=base,
            start=depart,
            author_id=interaction.user.id,
        )
        await interaction.delete_original_response()

    # ============================================================================
    # 🔹 Commande PREFIX
    # ============================================================================
    @commands.command(
        name="compte_a_rebours",
        aliases=["car", "countdown"],
        help="Compte à rebours dans une base. Usage : !compte_a_rebours <base> [départ]",
    )
    @commands.cooldown(1, 15.0, commands.BucketType.user)
    async def prefix_countdown(self, ctx: commands.Context, base: int = 10, depart: int = 20):
        if base < 2 or base > 10:
            await ctx.send("❌ La base doit être entre **2** et **10**.")
            return
        if depart < 1 or depart > 100:
            await ctx.send("❌ Le nombre de départ doit être entre **1** et **100**.")
            return
        await self._start_countdown(
            ctx.channel,
            base=base,
            start=depart,
            author_id=ctx.author.id,
        )


# ================================================================================
# 🔌 Setup du Cog
# ================================================================================
async def setup(bot: commands.Bot):
    cog = CompteARebours(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Fun"
    await bot.add_cog(cog)
