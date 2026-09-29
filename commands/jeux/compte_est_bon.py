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
        footer_text = "⏱️ Temps : 90 secondes"

        embed = discord.Embed(
            title="🧮 Le Compte est Bon",
            description=(
                f"**But :** Atteindre `{target}` avec les nombres suivants :\n"
                f"`{'  '.join(map(str, numbers))}`\n\n"
                "Utilise les opérations `+ - * /` pour t'en approcher le plus possible !\n\n"
                f"Mode : **{'Multijoueur 🌍' if multi else 'Solo 🧍‍♂️'}**\n"
                + ("Clique sur **🔔 Buzzer** pour prendre la main." if multi else "Clique sur **✍️ Répondre** pour proposer ton calcul.")
            ),
            color=discord.Color.gold()
        )
        embed.set_footer(text=footer_text)

        best_attempt = {
            "user": None,
            "expr": None,
            "result": None,
            "diff": float("inf")
        }
        found_exact = {"value": False}

        # ── Callback de validation (commun solo + multi) ──
        async def on_submit(interaction, answer):
            if found_exact["value"]:
                await safe_respond(interaction, "❌ La partie est terminée.", ephemeral=True)
                return

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

            # Mettre à jour la meilleure tentative
            if diff < best_attempt["diff"]:
                best_attempt["user"] = interaction.user
                best_attempt["expr"] = expr_raw
                best_attempt["result"] = result
                best_attempt["diff"] = diff

            # ── Cible exacte trouvée (écart 0) ──
            if diff == 0:
                found_exact["value"] = True

                await safe_respond(interaction, "🎉 Le compte est bon !", ephemeral=True)

                winner_embed = discord.Embed(
                    title="🧮 Le Compte est Bon — Gagné !",
                    description=(
                        f"**Cible :** `{target}` | **Nombres :** `{'  '.join(map(str, numbers))}`\n\n"
                        f"🏆 **{interaction.user.mention}** a trouvé le compte exact !\n"
                        f"✅ **Calcul :** `{expr_raw}` = **{result}**"
                    ),
                    color=discord.Color.green()
                )
                winner_embed.set_footer(text="Partie terminée")
                await view.mark_finished(embed=winner_embed)
                return

            # ── Calcul valide mais pas exact ──
            await safe_respond(
                interaction,
                f"✅ Calcul enregistré : `{expr_raw}` = **{result}** (Écart : {diff})",
                ephemeral=True,
            )

        # ── Callback quand quelqu'un buzze (multi seulement) ──
        async def on_buzz(user: discord.User | discord.Member):
            if view.message and view.message.embeds:
                # 1. Griser les boutons de la view
                for child in view.children:
                    if isinstance(child, discord.ui.Button):
                        child.disabled = True

                # 2. Indiquer le joueur qui a pris la main dans le footer
                current_embed = view.message.embeds[0]
                current_embed.set_footer(text=f"🎯 Main prise par {user.display_name} | {footer_text}")

                # 3. Transmettre view=view pour enregistrer l'état grisé
                await safe_edit(view.message, embed=current_embed, view=view)

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

        # ── Attente (90 secondes) ──
        await view.wait()

        if found_exact["value"]:
            return

        # ── Fin par timeout ──
        if best_attempt["user"] is not None:
            final_embed = discord.Embed(
                title="🧮 Le Compte est Bon — Terminé",
                description=(
                    f"**Cible :** `{target}` | **Nombres :** `{'  '.join(map(str, numbers))}`\n\n"
                    f"🥇 Meilleure approche par **{best_attempt['user'].mention}** !\n"
                    f"🎯 **Calcul :** `{best_attempt['expr']}` = **{best_attempt['result']}** (écart de {best_attempt['diff']})"
                ),
                color=discord.Color.gold()
            )
        else:
            final_embed = discord.Embed(
                title="⏱️ Temps écoulé !",
                description=(
                    f"**Cible :** `{target}` | **Nombres :** `{'  '.join(map(str, numbers))}`\n\n"
                    "❌ Personne n'a proposé de calcul valide."
                ),
                color=discord.Color.red()
            )

        final_embed.set_footer(text="Partie terminée")
        await view.mark_finished(embed=final_embed)

    # ============================================================================
    # 🔹 Commande SLASH
    # ============================================================================
    @app_commands.command(name="compte_est_bon", description="Lance le jeu du Compte est Bon (ajoute 'multi' pour jouer à plusieurs)")
    @app_commands.describe(mode="Écris 'multi' pour activer le mode multijoueur.")
    @app_commands.checks.cooldown(1, 10.0, key=lambda i: i.user.id)
    async def slash_compte(self, interaction: discord.Interaction, mode: str = None):
        await interaction.response.defer()
        multi = bool(mode and mode.lower() in ("multi", "m"))
        await self._start_game(interaction.channel, author=interaction.user, multi=multi)
        await interaction.delete_original_response()

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
