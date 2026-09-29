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
import asyncio
import logging
import random
import re

import discord
from discord import app_commands
from discord.ext import commands

from utils.discord_utils import safe_send, safe_edit
from utils.jeux_utils import parse_mode, ReplyView, BuzzerView

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
# 🎮 Classe de gestion du jeu
# ================================================================================
class CompteEstBonGame:
    def __init__(self, numbers: list[int], target: int, author_id: int, multi: bool = False, duration: int = 90):
        self.numbers = numbers
        self.target = target
        self.author_id = author_id
        self.multi = multi
        self.duration = duration
        self.finished = False
        self.winner: str | None = None
        self.attempts: list[dict] = []
        self.best_attempt: dict | None = None
        self.message = None
        self.start_time = asyncio.get_event_loop().time()

    def build_embed(self) -> discord.Embed:
        mode_text = "Multijoueur 🌍" if self.multi else "Solo 🧍‍♂️"
        title = f"🧮 Le Compte est Bon - Mode {mode_text}"

        action_text = "Clique sur **🔔 Buzzer** pour prendre la main." if self.multi else "Clique sur **✍️ Répondre** pour proposer ton calcul."
        description = (
            f"# 🎯 `{self.target}`\n"
            f"# 🎲 `{'  '.join(map(str, self.numbers))}`\n\n"
            "Utilise uniquement les opérations `+ - * /` pour t'en approcher le plus possible !\n"
            f"{action_text}"
        )

        embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Color.gold()
        )

        if self.attempts:
            lines = []
            for entry in self.attempts:
                if entry.get('error'):
                    lines.append(f"{entry['author']}: `{entry['expr']}` ❌ ({entry['error']})")
                else:
                    status = "✅ (Compte Bon !)" if entry['diff'] == 0 else f" (Écart: {entry['diff']})"
                    lines.append(f"{entry['author']}: `{entry['expr']}` = **{entry['result']}**{status}")
            tries_text = "\n".join(lines[-5:])  # Affiche les 5 derniers essais
            embed.add_field(name=f"Essais ({len(self.attempts)})", value=tries_text, inline=False)

        if self.finished:
            if self.winner:
                embed.title = f"{title} — Gagné !"
                embed.color = discord.Color.green()
                best = self.best_attempt
                embed.description = (
                    f"# 🎯 `{self.target}`\n"
                    f"# 🎲 `{'  '.join(map(str, self.numbers))}`\n\n"
                    f"🏆 **{self.winner}** a trouvé le compte exact !\n"
                    f"✅ **Calcul :** `{best['expr']}` = **{best['result']}**"
                )
            elif self.best_attempt:
                embed.title = f"{title} — Terminé"
                best = self.best_attempt
                embed.description = (
                    f"# 🎯 `{self.target}`\n"
                    f"# 🎲 `{'  '.join(map(str, self.numbers))}`\n\n"
                    f"🥇 Meilleure approche par **{best['user_mention']}** !\n"
                    f"🎯 **Calcul :** `{best['expr']}` = **{best['result']}** (écart de {best['diff']})"
                )
            else:
                embed.title = "⏰ Temps écoulé !"
                embed.color = discord.Color.red()
                embed.description = (
                    f"# 🎯 `{self.target}`\n"
                    f"# 🎲 `{'  '.join(map(str, self.numbers))}`\n\n"
                    "❌ Personne n'a proposé de calcul valide."
                )
            embed.set_footer(text="Partie terminée")
        else:
            elapsed = int(asyncio.get_event_loop().time() - self.start_time)
            remaining = max(0, self.duration - elapsed)
            embed.set_footer(text=f"⏱️ Temps restant : {remaining} secondes")

        return embed

# ================================================================================
# 🧠 Cog principal
# ================================================================================
class CompteEstBon(commands.Cog):
    """Commande /compte_est_bon et !compte_est_bon — Reproduit le jeu "Le Compte est Bon" """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ============================================================================
    # 🔹 Lancement du jeu
    # ============================================================================
    async def _start_game(self, channel: discord.abc.Messageable, author_id: int, multi: bool = False):
        numbers, target = generate_numbers()
        game = CompteEstBonGame(numbers, target, author_id, multi, duration=90)

        state = {"finished": False}
        embed = game.build_embed()

        # ── Callback de validation ──
        async def on_submit(interaction: discord.Interaction, answer: str):
            if not interaction.response.is_done():
                await interaction.response.defer()

            if state["finished"]:
                return

            if not game.multi and interaction.user.id != game.author_id:
                return

            expr_raw = answer.strip()
            if not expr_raw:
                return

            # Vérification de l'utilisation des nombres
            found_numbers = [int(x) for x in re.findall(r"\d+", expr_raw)]
            pool = game.numbers.copy()
            invalid_num = False

            for n in found_numbers:
                if n in pool:
                    pool.remove(n)
                else:
                    invalid_num = True
                    break

            if invalid_num:
                game.attempts.append({
                    'author': interaction.user.display_name,
                    'expr': expr_raw,
                    'error': "Nombre non disponible"
                })
                if game.message:
                    await safe_edit(game.message, embed=game.build_embed())
                return

            result = safe_eval(expr_raw)
            if result is None:
                game.attempts.append({
                    'author': interaction.user.display_name,
                    'expr': expr_raw,
                    'error': "Calcul invalide"
                })
                if game.message:
                    await safe_edit(game.message, embed=game.build_embed())
                return

            diff = abs(target - result)
            attempt_data = {
                'author': interaction.user.display_name,
                'user_mention': interaction.user.mention,
                'expr': expr_raw,
                'result': result,
                'diff': diff,
                'error': None
            }
            game.attempts.append(attempt_data)

            # Mise à jour de la meilleure tentative
            if game.best_attempt is None or diff < game.best_attempt['diff']:
                game.best_attempt = attempt_data

            # ── Cible exacte trouvée ──
            if diff == 0:
                state["finished"] = True
                game.finished = True
                game.winner = interaction.user.mention

                final_embed = game.build_embed()
                await view.mark_finished(embed=final_embed)
            else:
                if game.message:
                    await safe_edit(game.message, embed=game.build_embed())

        # ── Callback quand quelqu'un buzze (multi seulement) ──
        async def on_buzz(user: discord.User | discord.Member):
            if view.message:
                for child in view.children:
                    if isinstance(child, discord.ui.Button):
                        child.disabled = True

                current_embed = game.build_embed()
                elapsed = int(asyncio.get_event_loop().time() - game.start_time)
                remaining = max(0, game.duration - elapsed)
                current_embed.set_footer(text=f"🎯 Main prise par {user.display_name} | ⏱️ Temps restant : {remaining}s")

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
                user_id=author_id,
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
        game.message = view.message

        # ── Attente (90 secondes) ──
        try:
            await asyncio.sleep(game.duration)
        except asyncio.CancelledError:
            return

        if state["finished"]:
            return

        # ── Fin par timeout ──
        game.finished = True
        final_embed = game.build_embed()
        await view.mark_finished(embed=final_embed)

    # ============================================================================
    # 🔹 Commande SLASH
    # ============================================================================
    @app_commands.command(name="compte_est_bon", description="Lance le jeu du Compte est Bon")
    @app_commands.describe(mode="Tapez 'm' ou 'multi' pour le mode multijoueur")
    @app_commands.checks.cooldown(1, 10.0, key=lambda i: i.user.id)
    async def slash_compte(self, interaction: discord.Interaction, mode: str = None):
        await interaction.response.defer()
        multi = parse_mode(mode)
        await self._start_game(interaction.channel, author_id=interaction.user.id, multi=multi)
        await interaction.delete_original_response()

    # ============================================================================
    # 🔹 Commande PREFIX
    # ============================================================================
    @commands.command(name="compte_est_bon", aliases=["lceb", "lecompteestbon"], help="Lance le jeu du Compte est Bon")
    @commands.cooldown(1, 10.0, commands.BucketType.user)
    async def prefix_compte(self, ctx: commands.Context, *, arg: str = None):
        multi = parse_mode(arg)
        await self._start_game(ctx.channel, author_id=ctx.author.id, multi=multi)


# ================================================================================
# 🔌 Setup du Cog
# ================================================================================
async def setup(bot: commands.Bot):
    cog = CompteEstBon(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Jeux"
    await bot.add_cog(cog)
