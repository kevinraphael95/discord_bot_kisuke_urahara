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

from utils.discord_utils import safe_edit, safe_send
from utils.jeux_utils import BuzzerView, ReplyView, parse_mode

log = logging.getLogger(__name__)

# ================================================================================
# 🧠 Cog principal
# ================================================================================
class Devinelenombre(commands.Cog):
    """Commande /devinelenombre et !devinelenombre — Deviner un nombre entre 0 et 100"""
    SOLO_TIME   = 120
    MULTI_TIME  = 120
    MAX_ATTEMPTS = 10

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ============================================================================
    # 🔹 Construction de l'embed
    # ============================================================================
    def _build_embed(
        self,
        target: int,
        attempts: list[dict],
        multi: bool,
        finished: bool,
        winner: discord.User | discord.Member | None = None,
        last_error: str | None = None
    ) -> discord.Embed:
        mode_text = "Multi 🌍" if multi else "Solo 🧍‍♂️"
        embed = discord.Embed(
            title=f"🎯 Devinelenombre - Mode {mode_text}",
            description=(
                "Devine le nombre entre 0 et 100.\n" +
                ("Clique sur **🔔 Buzzer** pour prendre la main." if multi
                 else "Clique sur **✍️ Répondre** pour proposer un nombre.")
            ),
            color=discord.Color.orange()
        )

        if attempts:
            lines = []
            for idx, entry in enumerate(attempts, 1):
                val = entry['value']
                author_name = entry['author']
                if val < target:
                    symbol = "⬆️ Trop bas"
                elif val > target:
                    symbol = "⬇️ Trop haut"
                else:
                    symbol = "✅ Exact !"
                lines.append(f"{idx}. {author_name}: **{val}** → {symbol}")
            embed.add_field(
                name=f"Essais ({len(attempts)}/{self.MAX_ATTEMPTS})",
                value="\n".join(lines),
                inline=False,
            )
        else:
            embed.add_field(name="Essais", value="*(Aucun essai pour l'instant)*", inline=False)

        if last_error and not finished:
            embed.add_field(name="⚠️ Remarque", value=last_error, inline=False)

        if finished:
            if winner:
                embed.title = "🎯 Devinelenombre - Gagné !"
                embed.color = discord.Color.green()
                embed.description = f"🏆 **{winner.mention}** a trouvé le bon nombre ! C'était bien **{target}**."
                embed.set_footer(text="Partie terminée")
            elif attempts and attempts[-1]['value'] == target:
                embed.title = "🎯 Devinelenombre - Gagné !"
                embed.color = discord.Color.green()
                embed.description = f"🎉 Le nombre exact **{target}** a été trouvé !"
                embed.set_footer(text="Partie terminée")
            else:
                embed.title = "🎯 Devinelenombre - Terminé"
                embed.color = discord.Color.red()
                embed.description = f"❌ Partie terminée ! Le nombre était **{target}**."
                embed.set_footer(text="Partie terminée")
        else:
            embed.set_footer(text=f"⏳ Temps restant : {self.MULTI_TIME if multi else self.SOLO_TIME} secondes")

        return embed

    # ============================================================================
    # 🔹 Lancement du jeu
    # ============================================================================
    async def _start_game(self, channel: discord.abc.Messageable, author_id: int, multi: bool = False):
        target   = random.randint(0, 100)
        attempts: list[dict] = []
        state    = {"finished": False, "winner": None, "last_error": None}

        embed = self._build_embed(target, attempts, multi, state["finished"])

        # ── Callback de validation ──
        async def on_submit(interaction, answer):
            # Acquittement silencieux de l'interaction (aucun message éphémère)
            if not interaction.response.is_done():
                await interaction.response.defer()

            if state["finished"]:
                return

            try:
                guess = int(answer.strip())
            except ValueError:
                return

            if not (0 <= guess <= 100):
                return

            state["last_error"] = None

            # Vérification anti-doublon
            if any(entry['value'] == guess for entry in attempts):
                state["last_error"] = f"Le nombre `{guess}` a déjà été proposé !"
                new_embed = self._build_embed(
                    target, attempts, multi, state["finished"], last_error=state["last_error"]
                )
                await safe_edit(view.message, embed=new_embed)
                return

            attempts.append({'value': guess, 'author': interaction.user.display_name})

            # ✅ Gagné ou limite atteinte
            if guess == target or len(attempts) >= self.MAX_ATTEMPTS:
                state["finished"] = True
                if guess == target:
                    state["winner"] = interaction.user

                new_embed = self._build_embed(
                    target, attempts, multi, state["finished"], winner=state["winner"]
                )
                await view.mark_finished(embed=new_embed)

            # ❌ Partie toujours en cours
            else:
                new_embed = self._build_embed(target, attempts, multi, state["finished"])
                await safe_edit(view.message, embed=new_embed)

        # ── Callback quand quelqu'un buzze (multi seulement) ──
        async def on_buzz(user: discord.User | discord.Member):
            if view.message:
                for child in view.children:
                    if isinstance(child, discord.ui.Button):
                        child.disabled = True

                current_embed = self._build_embed(target, attempts, multi, state["finished"])
                current_embed.set_footer(text=f"🎯 Main prise par {user.display_name}")

                await safe_edit(view.message, embed=current_embed, view=view)

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
        final_embed = self._build_embed(target, attempts, multi, True, winner=state["winner"])
        await view.mark_finished(embed=final_embed)

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
