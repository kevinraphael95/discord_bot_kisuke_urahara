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
import re, random, asyncio
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
    """Évalue une expression arithmétique simple de façon sécurisée."""
    allowed_chars = "0123456789+-*/() "
    if any(c not in allowed_chars for c in expr):
        return None
    try:
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
        if not expr_raw:
            await safe_respond(interaction, "❌ Expression vide.", ephemeral=True)
            return

        found_numbers = [int(x) for x in re.findall(r"\d+", expr_raw)]
        pool = self.numbers.copy()

        for n in found_numbers:
            if n in pool:
                pool.remove(n)
            else:
                await safe_respond(interaction, "❌ Nombre non disponible ou utilisé trop de fois.", ephemeral=True)
                return

        result = safe_eval(expr_raw)
        if result is None:
            await safe_respond(interaction, "❌ Calcul invalide ou caractères interdits.", ephemeral=True)
            return

        diff = abs(self.target - result)
        short_msg = f"🧠 **{interaction.user.display_name}** → `{expr_raw}` = **{result}** (écart : {diff})"

        if diff == 0:
            self.parent_view.stop_game = True
            winner_embed = discord.Embed(
                title="🎉 Le compte est bon !",
                description=f"🏆 {interaction.user.mention} a trouvé la cible **{self.target}**\n\n"
                            f"**Proposition :** `{expr_raw}` = **{result}**",
                color=discord.Color.green()
            )
            winner_embed.add_field(name="Nombres", value=" ".join(map(str, self.numbers)), inline=False)
            await safe_send(interaction.channel, short_msg + "\n🎉 **Le compte est bon !**")
            if getattr(self.parent_view, "message", None):
                try:
                    await safe_edit(self.parent_view.message, embed=winner_embed, view=None)
                except Exception:
                    pass
            try:
                self.parent_view.stop()
            except Exception:
                pass
            await safe_respond(interaction, "✅ Tu as trouvé la cible !", ephemeral=True)
            return

        await safe_send(interaction.channel, short_msg)
        await safe_respond(interaction, f"✅ Proposition enregistrée — écart {diff}.", ephemeral=True)

class ProposerButton(Button):
    def __init__(self, parent_view: "CompteBonView"):
        super().__init__(label="🧮 Proposer un calcul", style=discord.ButtonStyle.primary)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        if not self.parent_view.is_multi and self.parent_view.author:
            if interaction.user.id != self.parent_view.author.id:
                await safe_respond(interaction, "❌ En mode solo, seul le joueur ayant lancé la partie peut proposer.", ephemeral=True)
                return
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
        self.active_games: dict[int, CompteBonView] = {}

    async def _start_game(self, channel: discord.abc.Messageable, author: discord.User = None, multi: bool = False):
        if channel.id in self.active_games:
            return await safe_send(channel, "⚠️ Une partie est déjà en cours dans ce salon.")

        numbers, target = generate_numbers()
        embed = discord.Embed(
            title="🧮 Le Compte est Bon",
            description=(
                f"**But :** Atteindre `{target}` avec les nombres suivants :\n"
                f"`{'  '.join(map(str, numbers))}`\n\n"
                "Utilise les opérations `+ - * /` pour t’en approcher le plus possible !\n\n"
                f"Mode : **{'Multijoueur' if multi else 'Solo'}** — Cliquez sur **🧮 Proposer un calcul**."
            ),
            color=discord.Color.gold()
        )
        embed.set_footer(text="Tu as 90 secondes pour proposer ton calcul.")
        view = CompteBonView(numbers, target, is_multi=multi, author=author, timeout=90)
        view.message = await safe_send(channel, embed=embed, view=view)
        self.active_games[channel.id] = view

        await view.wait()

        for c in view.children:
            c.disabled = True
        try:
            await safe_edit(view.message, view=view)
        except Exception:
            pass
        self.active_games.pop(channel.id, None)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="compte_est_bon",
        description="Lance le jeu du Compte est Bon (ajoute 'multi' pour jouer à plusieurs)"
    )
    @app_commands.describe(mode="Écris 'multi' pour activer le mode multijoueur.")
    @app_commands.checks.cooldown(1, 10.0, key=lambda i: i.user.id)
    async def slash_compte(self, interaction: discord.Interaction, mode: str = None):
        multi = bool(mode and mode.lower() in ["multi", "m"])
        await safe_respond(interaction, "🎮 Jeu lancé ! Regarde le canal pour participer.", ephemeral=True)
        await self._start_game(interaction.channel, author=interaction.user, multi=multi)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="compte_est_bon", aliases=["lceb", "lecompteestbon"])
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
