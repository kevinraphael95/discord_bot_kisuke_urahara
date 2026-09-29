# ================================================================================
# 📌 devinelenombre.py — Commande interactive /devinelenombre et !devinelenombre
# Objectif : Deviner un nombre entre 0 et 100
# Modes : Solo (1 joueur) et Multi (plusieurs joueurs)
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

import discord
from discord import app_commands
from discord.ext import commands

from utils.discord_utils import safe_send, safe_edit, safe_respond
from utils.jeux_utils import parse_mode, ReplyView, BuzzerView

log = logging.getLogger(__name__)

# ================================================================================
# 🧠 Cog principal
# ================================================================================
class Devinelenombre(commands.Cog):
    """Commande /devinelenombre et !devinelenombre — Deviner un nombre entre 0 et 100"""
    SOLO_TIME  = 120
    MULTI_TIME = 120
    MAX_ATTEMPTS = 10

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ============================================================================
    # 🔹 Construction de l'embed
    # ============================================================================
    def _build_embed(self, target: int, attempts: list, multi: bool, finished: bool) -> discord.Embed:
        mode_text = "Multi" if multi else "Solo"
        embed = discord.Embed(
            title=f"🎯 Devinelenombre - Mode {mode_text}",
            description=(
                "Devine le nombre entre 0 et 100.\n" +
                ("Clique sur **🔔 Buzzer** pour prendre la main." if multi
                 else "Clique sur **✍️ Répondre** pour proposer.")
            ),
            color=discord.Color.orange()
        )

        if attempts:
            lines = []
            for idx, val in enumerate(attempts, 1):
                if val < target:
                    symbol = "⬆️ Trop bas"
                elif val > target:
                    symbol = "⬇️ Trop haut"
                else:
                    symbol = "✅ Exact !"
                lines.append(f"{idx}. {val} → {symbol}")
            embed.add_field(
                name=f"Essais ({len(attempts)}/{self.MAX_ATTEMPTS})",
                value="\n".join(lines),
                inline=False,
            )
        else:
            embed.add_field(name="Essais", value="*(Aucun essai pour l'instant)*", inline=False)

        if finished:
            if attempts and attempts[-1] == target:
                embed.color = discord.Color.green()
                embed.set_footer(text="🎉 Bravo ! Le nombre a été trouvé.")
            else:
                embed.color = discord.Color.red()
                embed.set_footer(text=f"💀 Partie terminée. Le nombre était {target}.")
        else:
            embed.set_footer(text=f"⏳ Temps restant : {self.MULTI_TIME if multi else self.SOLO_TIME} secondes")

        return embed

    # ============================================================================
    # 🔹 Lancement du jeu
    # ============================================================================
    async def _start_game(self, channel: discord.abc.Messageable, author_id: int, multi: bool = False):
        target   = random.randint(0, 100)
        attempts = []
        state    = {"finished": False}

        embed = self._build_embed(target, attempts, multi, state["finished"])

        # ── Callback de validation ──
        async def on_submit(interaction, answer):
            if state["finished"]:
                await safe_respond(interaction, "⚠️ La partie est terminée.", ephemeral=True)
                return

            try:
                guess = int(answer.strip())
            except ValueError:
                await safe_respond(interaction, "❌ Ce n'est pas un nombre valide.", ephemeral=True)
                return

            if not (0 <= guess <= 100):
                await safe_respond(interaction, "⚠️ Le nombre doit être entre 0 et 100.", ephemeral=True)
                return

            attempts.append(guess)

            if guess == target or len(attempts) >= self.MAX_ATTEMPTS:
                state["finished"] = True
                for child in view.children:
                    child.disabled = True

            # Met à jour l'embed
            new_embed = self._build_embed(target, attempts, multi, state["finished"])
            await safe_edit(view.message, embed=new_embed, view=view)

            # Réponse éphémère au joueur
            if guess == target:
                await safe_respond(interaction, f"🎉 Bravo ! C'était bien **{target}**.", ephemeral=True)
            elif len(attempts) >= self.MAX_ATTEMPTS:
                await safe_respond(interaction, f"💀 Perdu ! Le nombre était **{target}**.", ephemeral=True)
            elif guess < target:
                await safe_respond(interaction, "⬆️ Trop bas !", ephemeral=True)
            else:
                await safe_respond(interaction, "⬇️ Trop haut !", ephemeral=True)

        # ── Callback quand quelqu'un buzze (multi seulement) ──
        async def on_buzz(interaction):
            await safe_send(
                interaction.channel,
                f"🎯 {interaction.user.mention} a buzzé ! À toi de proposer un nombre.",
            )

        # ── Vue selon le mode ──
        if multi:
            view = BuzzerView(
                modal_title="🎯 Propose un nombre",
                modal_label="Nombre entre 0 et 100",
                modal_placeholder="Exemple : 42",
                modal_max_length=3,
                on_submit=on_submit,
                on_buzz=on_buzz,
                buzz_timeout=30,
                view_timeout=self.MULTI_TIME,
            )
        else:
            view = ReplyView(
                user_id=author_id,
                modal_title="🎯 Propose un nombre",
                modal_label="Nombre entre 0 et 100",
                modal_placeholder="Exemple : 42",
                modal_max_length=3,
                on_submit=on_submit,
                timeout=self.SOLO_TIME,
            )

        view.message = await safe_send(channel, embed=embed, view=view)
        if view.message is None:
            return

        # ── Attente (timeout) ──
        try:
            await asyncio.sleep(self.MULTI_TIME if multi else self.SOLO_TIME)
        except asyncio.CancelledError:
            return

        if state["finished"]:
            return

        # ── Fin par timeout ──
        state["finished"] = True
        for child in view.children:
            child.disabled = True
        final_embed = self._build_embed(target, attempts, multi, True)
        await safe_edit(view.message, embed=final_embed, view=view)
        await safe_send(channel, f"⏳ Temps écoulé ! Le nombre était **{target}**.")

    # ============================================================================
    # 🔹 Commande SLASH
    # ============================================================================
    @app_commands.command(name="devinelenombre", description="Devine un nombre entre 0 et 100")
    @app_commands.describe(mode="Tapez 'm' ou 'multi' pour le mode multijoueur")
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_devinelenombre(self, interaction: discord.Interaction, mode: str = None):
        await interaction.response.defer()
        multi = parse_mode(mode)
        await self._start_game(interaction.channel, author_id=interaction.user.id, multi=multi)
        await interaction.delete_original_response()

    # ============================================================================
    # 🔹 Commande PREFIX
    # ============================================================================
    @commands.command(name="devinelenombre", help="Devine un nombre entre 0 et 100 (multi = plusieurs joueurs)")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_devinelenombre(self, ctx: commands.Context, mode: str = None):
        multi = parse_mode(mode)
        await self._start_game(ctx.channel, author_id=ctx.author.id, multi=multi)


# ================================================================================
# 🔌 Setup du Cog
# ================================================================================
async def setup(bot: commands.Bot):
    cog = Devinelenombre(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Jeux"
    await bot.add_cog(cog)
