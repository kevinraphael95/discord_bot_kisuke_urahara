# ================================================================================
# 📌 capitales.py — Commande interactive /capitales et !capitales
# Objectif : Deviner la capitale d'un pays
# Modes : Solo (1 joueur, 2 minutes) et Multi (plusieurs joueurs, 2 minutes)
# Réponses : via bouton (solo = ✍️ Répondre, multi = 🔔 Buzzer)
# Catégorie : Jeux
# Accès : Tous
# Cooldown : 1 utilisation / 10 secondes / utilisateur
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

from utils.discord_utils import safe_send, safe_respond, safe_edit
from utils.jeux_utils import normalize_text, parse_mode, ReplyView, BuzzerView

log = logging.getLogger(__name__)

# ================================================================================
# 📂 Liste des pays et leurs capitales
# ================================================================================
CAPITALS = {
    # ⚠️ GARDE ton dictionnaire complet ici (je ne le recopie pas pour ne pas surcharger)
    # Copie-colle ton dictionnaire actuel à cette place
    "France": "Paris",
    "Allemagne": "Berlin",
    # ... (tout ton dictionnaire)
}

# ================================================================================
# 🧠 Cog principal
# ================================================================================
class Capitales(commands.Cog):
    """Commande /capitales et !capitales — Deviner la capitale d'un pays"""
    SOLO_TIME  = 120
    MULTI_TIME = 120

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ============================================================================
    # 🔹 Fonction interne commune
    # ============================================================================
    async def _send_quiz(self, channel, author_id: int, multi: bool = False):
        country = random.choice(list(CAPITALS.keys()))
        capital = CAPITALS[country]
        winners = []

        title       = "Devine la Capitale - Mode Multijoueur 🌍" if multi else "Devine la Capitale - Mode Solo 🧍‍♂️"
        footer_text = f"⏱️ Temps : {self.MULTI_TIME if multi else self.SOLO_TIME} secondes"

        embed = discord.Embed(
            title=title,
            description=f"Quelle est la capitale de **{country}** ?" +
                        ("\nClique sur **🔔 Buzzer** pour prendre la main." if multi else "\nClique sur **✍️ Répondre** pour proposer ta réponse."),
            color=discord.Color.blurple()
        )
        embed.set_footer(text=footer_text)

        # ── Callback de validation (partagé) ──
        async def on_submit(interaction, answer):
            user_answer = normalize_text(answer)
            if user_answer == normalize_text(capital):
                if interaction.user not in winners:
                    winners.append(interaction.user)
                await safe_respond(interaction, "✅ Bonne réponse !", ephemeral=True)

                # En solo, on termine immédiatement
                if not multi and not getattr(view, "finished", False):
                    view.finished = True
                    for child in view.children:
                        child.disabled = True

                    final_embed = discord.Embed(
                        title="🎉 Le compte est bon !",
                        description=f"🏆 **{interaction.user.display_name}** a trouvé !\n\n✅ Réponse : **{capital}**",
                        color=discord.Color.green()
                    )
                    await safe_edit(view.message, embed=final_embed, view=view)
            else:
                await safe_respond(interaction, "❌ Mauvaise réponse !", ephemeral=True)

        # ── Création de la view selon le mode ──
        if multi:
            # ── MULTI : BuzzerView (1 seul joueur à la fois) ──
            async def on_buzz(interaction):
                await safe_send(
                    interaction.channel,
                    f"🎯 {interaction.user.mention} a buzzé ! À toi de proposer."
                )

            view = BuzzerView(
                modal_title="🖊️ Devine la capitale",
                modal_label="Entre la capitale",
                modal_placeholder="Exemple : Paris",
                modal_max_length=50,
                on_submit=on_submit,
                on_buzz=on_buzz,
                buzz_timeout=30,
                view_timeout=300,
            )
        else:
            # ── SOLO : ReplyView (bouton "✍️ Répondre") ──
            view = ReplyView(
                user_id=author_id,
                modal_title="🖊️ Devine la capitale",
                modal_label="Entre la capitale",
                modal_placeholder="Exemple : Paris",
                modal_max_length=50,
                on_submit=on_submit,
                timeout=300,
            )

        view.message  = None
        view.finished = False

        msg = await safe_send(channel, embed=embed, view=view)
        if msg is None:
            return
        view.message = msg

        # ── Attente (le temps du quiz) ──
        try:
            await asyncio.sleep(self.MULTI_TIME if multi else self.SOLO_TIME)
        except asyncio.CancelledError:
            return

        if view.finished:
            return

        # ── Fin du temps ──
        final_embed = discord.Embed(
            title="🎉 Résultat",
            description=(
                f"✅ Réponse : **{capital}**\n"
                f"🏆 Gagnants : {', '.join(w.mention for w in dict.fromkeys(winners))}"
                if winners else
                f"❌ Personne n'a trouvé. C'était **{capital}**."
            ),
            color=discord.Color.red() if not winners else discord.Color.green(),
        )
        for child in view.children:
            child.disabled = True
        await safe_edit(view.message, embed=final_embed, view=view)

    # ============================================================================
    # 🔹 Commande SLASH
    # ============================================================================
    @app_commands.command(name="capitales", description="Devine la capitale d'un pays")
    @app_commands.describe(mode="Tapez 'm' ou 'multi' pour le mode multijoueur")
    @app_commands.checks.cooldown(1, 10.0, key=lambda i: i.user.id)
    async def slash_capitales(self, interaction: discord.Interaction, mode: str = None):
        await interaction.response.defer()
        multi = parse_mode(mode)
        await self._send_quiz(interaction.channel, author_id=interaction.user.id, multi=multi)
        await interaction.delete_original_response()

    # ============================================================================
    # 🔹 Commande PREFIX
    # ============================================================================
    @commands.command(name="capitales", help="Devine la capitale d'un pays")
    @commands.cooldown(1, 10.0, commands.BucketType.user)
    async def prefix_capitales(self, ctx: commands.Context, *, arg: str = None):
        multi = parse_mode(arg)
        await self._send_quiz(ctx.channel, author_id=ctx.author.id, multi=multi)


# ================================================================================
# 🔌 Setup du Cog
# ================================================================================
async def setup(bot: commands.Bot):
    cog = Capitales(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Jeux"
    await bot.add_cog(cog)
