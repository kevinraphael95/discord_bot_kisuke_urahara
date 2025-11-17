# ────────────────────────────────────────────────────────────────────────────────
# 📌 compte_est_bon.py — Jeu interactif /compte_est_bon et !compte_est_bon
# Objectif : Un seul jeu actif à la fois, propositions via modal, timeout 90s
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
# 🎮 Vue principale du jeu Compte est Bon
# ────────────────────────────────────────────────────────────────────────────────
class CompteBonView(View):
    """Classe représentant une partie de Compte est Bon"""

    TIMEOUT = 90  # secondes

    def __init__(self, numbers: list, target: int, author: discord.User = None, multi: bool = False):
        super().__init__(timeout=self.TIMEOUT)
        self.numbers = numbers
        self.target = target
        self.author = author
        self.multi = multi
        self.finished = False
        self.message = None
        self.start_time = asyncio.get_event_loop().time()
        self.add_item(ProposerButton(self))

    async def on_timeout(self):
        self.finished = True
        for c in self.children:
            c.disabled = True
        if self.message:
            try:
                await safe_send(self.message.channel, "⏱️ Temps écoulé ! Personne n’a trouvé la solution exacte.")
                await safe_edit(self.message, view=self)
            except:
                pass

class ProposerButton(Button):
    def __init__(self, parent_view: CompteBonView):
        super().__init__(label="🧮 Proposer un calcul", style=discord.ButtonStyle.primary)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        if not self.parent_view.multi and self.parent_view.author:
            if interaction.user.id != self.parent_view.author.id:
                await safe_respond(interaction, "❌ En mode solo, seul le joueur ayant lancé la partie peut proposer.", ephemeral=True)
                return
        await interaction.response.send_modal(PropositionModal(self.parent_view))

class PropositionModal(Modal):
    def __init__(self, parent_view: CompteBonView):
        super().__init__(title="🧮 Proposer un calcul")
        self.parent_view = parent_view
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
            return await safe_respond(interaction, "❌ Expression vide.", ephemeral=True)

        # Vérifier que les nombres utilisés existent
        found_numbers = [int(x) for x in re.findall(r"\d+", expr_raw)]
        pool = self.parent_view.numbers.copy()
        for n in found_numbers:
            if n in pool:
                pool.remove(n)
            else:
                return await safe_respond(interaction, "❌ Nombre non disponible ou utilisé trop de fois.", ephemeral=True)

        # Calcul
        result = safe_eval(expr_raw)
        if result is None:
            return await safe_respond(interaction, "❌ Calcul invalide ou caractères interdits.", ephemeral=True)

        diff = abs(self.parent_view.target - result)
        short_msg = f"🧠 **{interaction.user.display_name}** → `{expr_raw}` = **{result}** (écart : {diff})"
        await safe_send(interaction.channel, short_msg)

        if diff == 0:
            self.parent_view.finished = True
            winner_embed = discord.Embed(
                title="🎉 Le compte est bon !",
                description=f"🏆 {interaction.user.mention} a trouvé la cible **{self.parent_view.target}**\n\n"
                            f"**Proposition :** `{expr_raw}` = **{result}**",
                color=discord.Color.green()
            )
            winner_embed.add_field(name="Nombres", value=" ".join(map(str, self.parent_view.numbers)), inline=False)
            if self.parent_view.message:
                try:
                    await safe_edit(self.parent_view.message, embed=winner_embed, view=None)
                except:
                    pass
            try:
                self.parent_view.stop()
            except:
                pass
            return await safe_respond(interaction, "✅ Tu as trouvé la cible !", ephemeral=True)
        else:
            await safe_respond(interaction, f"✅ Proposition enregistrée — écart {diff}.", ephemeral=True)

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class CompteEstBon(commands.Cog):
    """Commande /compte_est_bon et !compte_est_bon — jeu interactif"""

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
        embed.set_footer(text=f"Tu as {CompteBonView.TIMEOUT} secondes pour proposer ton calcul.")

        view = CompteBonView(numbers, target, author=author, multi=multi)
        view.message = await safe_send(channel, embed=embed, view=view)
        self.active_games[channel.id] = view

        await view.wait()  # attend fin de partie ou timeout

        for c in view.children:
            c.disabled = True
        try:
            await safe_edit(view.message, view=view)
        except:
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
