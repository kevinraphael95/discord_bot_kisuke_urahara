# ================================================================================
# 📌 compte_est_bon.py — Jeu interactif /compte_est_bon et !compte_est_bon
# Objectif : Reproduire le jeu "Le Compte est Bon" avec calculs et proposition
# Catégorie : Jeux
# Accès : Tous
# Cooldown : 1 utilisation / 10 secondes / utilisateur
# ================================================================================

# ================================================================================
# 📦 Imports nécessaires
# ================================================================================
import logging
import random
import re

import discord
from discord import app_commands
from discord.ext import commands

from utils.discord_utils import safe_send, safe_edit, safe_respond
from utils.jeux_utils import ReplyView, BuzzerView

log = logging.getLogger(__name__)

# ================================================================================
# 🎮 Fonctions utilitaires
# ================================================================================
def generate_numbers():
    """Génère 6 nombres (2 grands + 4 petits) et un objectif (100-999)."""
    grands = [25, 50, 75, 100]
    petits = [i for i in range(1, 11)] * 2
    selection = random.sample(grands, 2) + random.sample(petits, 4)
    random.shuffle(selection)
    objectif = random.randint(100, 999)
    return selection, objectif

def safe_eval(expr: str):
    """Évalue une expression arithmétique simple."""
    allowed_chars = "0123456789+-*/() "
    if any(c not in allowed_chars for c in expr):
        return None
    try:
        return round(eval(expr, {"__builtins__": None}, {}))
    except Exception:
        return None

# ================================================================================
# 🧠 Cog principal
# ================================================================================
class CompteEstBon(commands.Cog):
    """
    Commande /compte_est_bon et !compte_est_bon — Reproduit le jeu "Le Compte est Bon"
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ============================================================================
    # 🔹 Lancement du jeu
    # ============================================================================
    async def _start_game(self, channel: discord.abc.Messageable, author: discord.User = None, multi: bool = False):
        numbers, target = generate_numbers()

        embed = discord.Embed(
            title="🧮 Le Compte est Bon",
            description=(
                f"**But :** Atteindre `{target}` avec les nombres suivants :\n"
                f"`{'  '.join(map(str, numbers))}`\n\n"
                "Utilise les opérations `+ - * /` pour t'en approcher le plus possible !\n\n"
                f"Mode : **{'Multijoueur' if multi else 'Solo'}**"
            ),
            color=discord.Color.gold()
        )
        embed.set_footer(
            text=("Clique sur 🔔 Buzzer pour prendre la main (90 secondes)."
                  if multi else
                  "Clique sur ✍️ Répondre pour proposer ton calcul (90 secondes).")
        )

        found_exact = {"value": False}

        # ── Callback de validation (commun solo + multi) ──
        async def on_submit(interaction, answer):
            expr_raw = answer.strip()

            if not expr_raw:
                await safe_respond(interaction, "❌ Expression vide.", ephemeral=True)
                return

            found_numbers = [int(x) for x in re.findall(r"\d+", expr_raw)]
            pool = numbers.copy()

            for n in found_numbers:
                if n in pool:
                    pool.remove(n)
                else:
                    await safe_respond(
                        interaction,
                        "❌ Tu as utilisé un nombre non disponible ou trop de fois.",
                        ephemeral=True,
                    )
                    return

            result = safe_eval(expr_raw)
            if result is None:
                await safe_respond(
                    interaction,
                    "❌ Calcul invalide ou caractères interdits.",
                    ephemeral=True,
                )
                return

            diff = abs(target - result)
            short_msg = f"🧠 **{interaction.user.display_name}** → `{expr_raw}` = **{result}** (écart : {diff})"

            # ── Cible trouvée : fin de partie ──
            if diff == 0:
                found_exact["value"] = True

                winner_embed = discord.Embed(
                    title="🎉 Le compte est bon !",
                    description=(
                        f"🏆 {interaction.user.mention} a trouvé la cible **{target}**\n\n"
                        f"**Proposition :** `{expr_raw}` = **{result}**"
                    ),
                    color=discord.Color.green()
                )
                winner_embed.add_field(name="Nombres", value="  ".join(map(str, numbers)), inline=False)

                await safe_send(interaction.channel, short_msg + "\n🎉 **Le compte est bon !**")
                if view.message:
                    try:
                        await safe_edit(view.message, embed=winner_embed, view=None)
                    except Exception:
                        pass

                await safe_respond(
                    interaction,
                    "✅ Proposition enregistrée — tu as trouvé la cible !",
                    ephemeral=True,
                )
                return

            # ── Sinon : on relaie la proposition ──
            await safe_send(interaction.channel, short_msg)
            await safe_respond(
                interaction,
                f"✅ Proposition enregistrée — écart {diff}.",
                ephemeral=True,
            )

        # ── Callback quand quelqu'un buzze (multi seulement) ──
        async def on_buzz(interaction):
            await safe_send(
                interaction.channel,
                f"🎯 {interaction.user.mention} a buzzé ! À toi de proposer un calcul.",
            )

        # ── Vue selon le mode ──
        if multi:
            view = BuzzerView(
                modal_title="🧮 Proposer un calcul",
                modal_label="Ton calcul (ex: (100-25)*3)",
                modal_placeholder="Utilise uniquement les nombres affichés et + - * /",
                modal_max_length=200,
                on_submit=on_submit,
                on_buzz=on_buzz,
                buzz_timeout=30,
                view_timeout=90,
            )
        else:
            view = ReplyView(
                user_id=author.id if author else None,
                modal_title="🧮 Proposer un calcul",
                modal_label="Ton calcul (ex: (100-25)*3)",
                modal_placeholder="Utilise uniquement les nombres affichés et + - * /",
                modal_max_length=200,
                on_submit=on_submit,
                timeout=90,
            )

        view.message = await safe_send(channel, embed=embed, view=view)
        if view.message is None:
            return

        # ── Attente (90 secondes ou fin de partie) ──
        await view.wait()

        if found_exact["value"]:
            return

        # ── Fin par timeout ──
        for c in view.children:
            c.disabled = True
        try:
            await safe_edit(view.message, view=view)
        except Exception:
            pass
        await safe_send(channel, "⏱️ Temps écoulé ! Personne n'a trouvé la solution exacte.")

    # ============================================================================
    # 🔹 Commande SLASH
    # ============================================================================
    @app_commands.command(name="compte_est_bon", description="Lance le jeu du Compte est Bon (ajoute 'multi' pour jouer à plusieurs)")
    @app_commands.describe(mode="Écris 'multi' pour activer le mode multijoueur.")
    @app_commands.checks.cooldown(1, 10.0, key=lambda i: i.user.id)
    async def slash_compte(self, interaction: discord.Interaction, mode: str = None):
        multi = bool(mode and mode.lower() in ("multi", "m"))
        await safe_respond(interaction, "🎮 Jeu lancé ! Regarde le canal pour participer.", ephemeral=True)
        await self._start_game(interaction.channel, author=interaction.user, multi=multi)

    # ============================================================================
    # 🔹 Commande PREFIX
    # ============================================================================
    @commands.command(name="compte_est_bon", aliases=["lceb", "lecompteestbon"], help="Lance le jeu du Compte est Bon (ajoute 'multi' pour jouer à plusieurs)")
    @commands.cooldown(1, 10.0, commands.BucketType.user)
    async def prefix_compte(self, ctx: commands.Context, mode: str = None):
        multi = bool(mode and mode.lower() in ("multi", "m"))
        await self._start_game(ctx.channel, author=ctx.author, multi=multi)


# ================================================================================
# 🔌 Setup du Cog
# ================================================================================
async def setup(bot: commands.Bot):
    cog = CompteEstBon(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Jeux"
    await bot.add_cog(cog)
