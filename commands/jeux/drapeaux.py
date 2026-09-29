# ================================================================================
# 📌 drapeaux.py — Commande interactive /drapeaux et !drapeaux
# Objectif : Deviner le pays à partir d'un drapeau aléatoire (tous les pays)
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
# 📂 Liste complète des pays et codes ISO
# ================================================================================
COUNTRIES = {
    # ⚠️ GARDE ton dictionnaire complet ici
    "France": "fr",
    "Allemagne": "de",
    # ... (tout ton dictionnaire)
}

def get_flag_url(iso_code: str) -> str:
    return f"https://flagcdn.com/w320/{iso_code}.png"

# ================================================================================
# 🧠 Cog principal
# ================================================================================
class Drapeaux(commands.Cog):
    """Commande /drapeaux et !drapeaux — Deviner le pays à partir d'un drapeau"""

    SOLO_TIME  = 120
    MULTI_TIME = 120

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ============================================================================
    # 🔹 Fonction interne commune
    # ============================================================================
    async def _send_quiz(self, channel, author_id: int, multi: bool = False):
        country, iso_code = random.choice(list(COUNTRIES.items()))
        flag_url = get_flag_url(iso_code)
        winners  = []

        embed = discord.Embed(
            title="🌍 Devine le pays !",
            description=("Clique sur **🔔 Buzzer** pour prendre la main." if multi
                         else "Clique sur **✍️ Répondre** pour proposer ta réponse."),
            color=discord.Color.blurple()
        )
        embed.set_image(url=flag_url)
        embed.set_footer(text=f"⏱️ Temps : {self.MULTI_TIME if multi else self.SOLO_TIME} secondes")

        # ── Callback de validation ──
        async def on_submit(interaction, answer):
            user_answer = normalize_text(answer)
            if user_answer == normalize_text(country):
                if interaction.user not in winners:
                    winners.append(interaction.user)
                await safe_respond(interaction, "✅ Bonne réponse !", ephemeral=True)

                # En solo, on termine immédiatement
                if not multi and not state["finished"]:
                    state["finished"] = True
                    for child in view.children:
                        child.disabled = True

                    final_embed = discord.Embed(
                        title="🎉 Bravo !",
                        description=f"🏆 **{interaction.user.display_name}** a trouvé !\n\n✅ Réponse : **{country}**",
                        color=discord.Color.green()
                    )
                    final_embed.set_image(url=flag_url)
                    await safe_edit(view.message, embed=final_embed, view=view)
            else:
                await safe_respond(interaction, "❌ Mauvaise réponse !", ephemeral=True)

        # ── Callback quand quelqu'un buzze (multi seulement) ──
        async def on_buzz(interaction):
            await safe_send(
                interaction.channel,
                f"🎯 {interaction.user.mention} a buzzé ! À toi de proposer.",
            )

        state = {"finished": False}

        # ── Vue selon le mode ──
        if multi:
            view = BuzzerView(
                modal_title="🖊️ Devine le pays",
                modal_label="Entre le nom du pays",
                modal_placeholder="Exemple : France",
                modal_max_length=50,
                on_submit=on_submit,
                on_buzz=on_buzz,
                buzz_timeout=30,
                view_timeout=300,
            )
        else:
            view = ReplyView(
                user_id=author_id,
                modal_title="🖊️ Devine le pays",
                modal_label="Entre le nom du pays",
                modal_placeholder="Exemple : France",
                modal_max_length=50,
                on_submit=on_submit,
                timeout=300,
            )

        view.message = await safe_send(channel, embed=embed, view=view)
        if view.message is None:
            return

        # ── Attente ──
        try:
            await asyncio.sleep(self.MULTI_TIME if multi else self.SOLO_TIME)
        except asyncio.CancelledError:
            return

        if state["finished"]:
            return

        # ── Fin du temps ──
        final_embed = discord.Embed(
            title="🎉 Résultat",
            description=(
                f"✅ Réponse : **{country}**\n"
                f"🏆 Gagnants : {', '.join(w.mention for w in dict.fromkeys(winners))}"
                if winners else
                f"❌ Personne n'a trouvé. C'était **{country}**."
            ),
            color=discord.Color.red() if not winners else discord.Color.green(),
        )
        final_embed.set_image(url=flag_url)
        for child in view.children:
            child.disabled = True
        await safe_edit(view.message, embed=final_embed, view=view)

    # ============================================================================
    # 🔹 Commande SLASH
    # ============================================================================
    @app_commands.command(name="drapeaux", description="Devine le pays à partir d'un drapeau")
    @app_commands.describe(mode="Tapez 'm' ou 'multi' pour le mode multijoueur")
    @app_commands.checks.cooldown(1, 10.0, key=lambda i: i.user.id)
    async def slash_drapeaux(self, interaction: discord.Interaction, mode: str = None):
        await interaction.response.defer()
        multi = parse_mode(mode)
        await self._send_quiz(interaction.channel, author_id=interaction.user.id, multi=multi)
        await interaction.delete_original_response()

    # ============================================================================
    # 🔹 Commande PREFIX
    # ============================================================================
    @commands.command(name="drapeaux", help="Devine le pays à partir d'un drapeau")
    @commands.cooldown(1, 10.0, commands.BucketType.user)
    async def prefix_drapeaux(self, ctx: commands.Context, *, arg: str = None):
        multi = parse_mode(arg)
        await self._send_quiz(ctx.channel, author_id=ctx.author.id, multi=multi)


# ================================================================================
# 🔌 Setup du Cog
# ================================================================================
async def setup(bot: commands.Bot):
    cog = Drapeaux(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Jeux"
    await bot.add_cog(cog)
