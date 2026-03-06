# ────────────────────────────────────────────────────────────────────────────────
# 📌 compte_est_bon.py — Jeu interactif /compte_est_bon et !compte_est_bon
# Objectif : Reproduire le jeu "Le Compte est Bon" avec calculs et proposition
# Catégorie : Jeux
# Accès : Tous
# Cooldown : 1 utilisation / 10 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import re
import random
import asyncio
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput
from utils.discord_utils import safe_send, safe_edit, safe_respond

# ────────────────────────────────────────────────────────────────────────────────
# 🎮 Fonctions utilitaires
# ────────────────────────────────────────────────────────────────────────────────
def generate_numbers():
    """Génère 6 nombres (2 grands + 4 petits) et un objectif (100-999)."""
    grands = [25, 50, 75, 100]
    petits = [i for i in range(1, 11)] * 2
    selection = random.sample(grands, 2) + random.sample(petits, 4)
    random.shuffle(selection)
    objectif = random.randint(100, 999)
    return selection, objectif

def safe_eval(expr: str):
    """Évalue une expression arithmétique simple en limitant les caractères autorisés."""
    allowed_chars = "0123456789+-*/() "
    if any(c not in allowed_chars for c in expr):
        return None
    try:
        # environnement sécurisé sans builtins
        return round(eval(expr, {"__builtins__": None}, {}))
    except Exception:
        return None

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ Interface — Modal & Bouton
# ────────────────────────────────────────────────────────────────────────────────
class PropositionModal(Modal):
    def __init__(self, parent_view: "CompteBonView", numbers: list, target: int):
        super().__init__(title="🧮 Proposer un calcul")
        self.parent_view = parent_view
        self.numbers = numbers
        self.target = target
        self.expression = TextInput(
            label="Ton calcul (ex: (100-25)*3)",
            placeholder="Utilise uniquement les nombres affichés et + - * /",
            style=discord.TextStyle.short,
            required=True,
            max_length=200
        )
        self.add_item(self.expression)

    async def on_submit(self, interaction: discord.Interaction):
        expr_raw = self.expression.value.strip()
        # extra check minimal
        if not expr_raw:
            await safe_respond(interaction, "❌ Expression vide.", ephemeral=True)
            return

        # extraction des nombres littéraux présents dans l'expression
        found_numbers = [int(x) for x in re.findall(r"\d+", expr_raw)]
        pool = self.numbers.copy()

        # vérification que chaque littéral utilisé existe dans la pool (consommation)
        for n in found_numbers:
            if n in pool:
                pool.remove(n)
            else:
                await safe_respond(interaction, "❌ Tu as utilisé un nombre non disponible ou trop de fois.", ephemeral=True)
                return

        # évaluation sécurisée
        result = safe_eval(expr_raw)
        if result is None:
            await safe_respond(interaction, "❌ Calcul invalide ou utilisation de caractères interdits.", ephemeral=True)
            return

        diff = abs(self.target - result)
        short_msg = f"🧠 **{interaction.user.display_name}** → `{expr_raw}` = **{result}** (écart : {diff})"

        # si exact -> on marque la fin, on édite le message d'origine pour annoncer le gagnant
        if diff == 0:
            self.parent_view.stop_game = True
            winner_embed = discord.Embed(
                title="🎉 Le compte est bon !",
                description=f"🏆 {interaction.user.mention} a trouvé la cible **{self.target}**\n\n"
                            f"**Proposition :** `{expr_raw}` = **{result}**",
                color=discord.Color.green()
            )
            winner_embed.add_field(name="Nombres", value=" ".join(map(str, self.numbers)), inline=False)
            # envoi d'un message visible dans le salon + édit du message de jeu si possible
            await safe_send(interaction.channel, short_msg + "\n🎉 **Le compte est bon !**")
            if getattr(self.parent_view, "message", None):
                try:
                    await safe_edit(self.parent_view.message, embed=winner_embed, view=None)
                except Exception:
                    pass
            # stoppe la view pour réveiller le lanceur qui attend view.wait()
            try:
                self.parent_view.stop()
            except Exception:
                pass
            # confirmation privée au joueur
            await safe_respond(interaction, "✅ Proposition enregistrée — tu as trouvé la cible !", ephemeral=True)
            return

        # sinon on envoie la proposition en canal et on confirme en éphémère
        await safe_send(interaction.channel, short_msg)
        await safe_respond(interaction, f"✅ Proposition enregistrée — écart {diff}.", ephemeral=True)

class ProposerButton(Button):
    def __init__(self, parent_view: "CompteBonView"):
        super().__init__(label="🧮 Proposer un calcul", style=discord.ButtonStyle.primary)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        # contrôle solo vs multi
        if not self.parent_view.is_multi and self.parent_view.author:
            if interaction.user.id != self.parent_view.author.id:
                await safe_respond(interaction, "❌ En mode solo, seul·e le joueur ayant lancé la partie peut proposer.", ephemeral=True)
                return
        # ouvre le modal
        await interaction.response.send_modal(PropositionModal(self.parent_view, self.parent_view.numbers, self.parent_view.target))

class CompteBonView(View):
    def __init__(self, numbers: list, target: int, is_multi: bool = False, author: discord.User = None, timeout: int = 90):
        super().__init__(timeout=timeout)
        self.numbers = numbers
        self.target = target
        self.is_multi = is_multi
        self.author = author
        self.stop_game = False
        self.add_item(ProposerButton(self))

    async def on_timeout(self):
        # désactive les boutons et notifie si personne n'a trouvé
        for c in self.children:
            c.disabled = True
        if not self.stop_game:
            try:
                await safe_send(self.message.channel, "⏱️ Temps écoulé ! Personne n’a trouvé la solution exacte.")
            except Exception:
                pass
        try:
            await safe_edit(self.message, view=self)
        except Exception:
            pass

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class CompteEstBon(commands.Cog):
    """
    Commande /compte_est_bon et !compte_est_bon — Reproduit le jeu "Le Compte est Bon"
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Lancement du jeu (utilisé par slash et prefix)
    # ────────────────────────────────────────────────────────────────────────────
    async def _start_game(self, channel: discord.abc.Messageable, author: discord.User = None, multi: bool = False):
        numbers, target = generate_numbers()
        embed = discord.Embed(
            title="🧮 Le Compte est Bon",
            description=(
                f"**But :** Atteindre `{target}` avec les nombres suivants :\n"
                f"`{'  '.join(map(str, numbers))}`\n\n"
                "Utilise les opérations `+ - * /` pour t’en approcher le plus possible !\n\n"
                f"Mode : **{'Multijoueur' if multi else 'Solo'}** — Cliquez sur **🧮 Proposer un calcul** pour proposer."
            ),
            color=discord.Color.gold()
        )
        embed.set_footer(text="Tu as 90 secondes pour proposer ton calcul.")
        view = CompteBonView(numbers, target, is_multi=multi, author=author, timeout=90)
        view.message = await safe_send(channel, embed=embed, view=view)

        # attente jusqu'au stop (quelqu'un trouve) ou timeout (on attend view.wait())
        await view.wait()

        # au réveil : désactiver boutons (sécurité) et si pas déjà édité, on remet la view désactivée
        for c in view.children:
            c.disabled = True
        try:
            await safe_edit(view.message, view=view)
        except Exception:
            pass

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(name="compte_est_bon",description="Lance le jeu du Compte est Bon (ajoute 'multi' pour jouer à plusieurs)")
    @app_commands.describe(mode="Écris 'multi' pour activer le mode multijoueur.")
    @app_commands.checks.cooldown(1, 10.0, key=lambda i: i.user.id)
    async def slash_compte(self, interaction: discord.Interaction, mode: str = None):
        multi = bool(mode and mode.lower() in ["multi", "m"])
        # message d'acknowledge éphémère pour l'invocateur
        await safe_respond(interaction, "🎮 Jeu lancé ! Regarde le canal pour participer.", ephemeral=True)
        await self._start_game(interaction.channel, author=interaction.user, multi=multi)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="compte_est_bon", aliases=["lceb", "lecompteestbon"], help="Lance le jeu du Compte est Bon (ajoute 'multi' pour jouer à plusieurs)")
    @commands.cooldown(1, 10.0, commands.BucketType.user)
    async def prefix_compte(self, ctx: commands.Context, mode: str = None):
        multi = bool(mode and mode.lower() in ["multi", "m"])
        await self._start_game(ctx.channel, author=ctx.author, multi=multi)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = CompteEstBon(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Jeux"
    await bot.add_cog(cog)

