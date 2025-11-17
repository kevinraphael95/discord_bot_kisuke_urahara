# ────────────────────────────────────────────────────────────────────────────────
# 📌 compte_est_bon.py — Commande interactive /compte_est_bon et !compte_est_bon
# Objectif : Reproduit le jeu "Le Compte est Bon" avec solo et multi, fin auto après 3 minutes
# Catégorie : Jeux
# Accès : Tous
# Cooldown : 1 utilisation / 10 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput
import random, asyncio, re
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
        return round(eval(expr, {"__builtins__": None}, {}))
    except Exception:
        return None

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ Modal pour proposer un calcul
# ────────────────────────────────────────────────────────────────────────────────
class CompteBonModal(Modal):
    def __init__(self, parent_view, numbers, target):
        super().__init__(title="🧮 Proposer un calcul")
        self.parent_view = parent_view
        self.numbers = numbers
        self.target = target
        self.add_item(TextInput(label="Ton calcul", placeholder="Ex: (100-25)*3", style=discord.TextStyle.short, required=True, max_length=200))

    async def on_submit(self, interaction: discord.Interaction):
        expr = self.children[0].value.strip()
        if not expr:
            return await safe_respond(interaction, "❌ Expression vide.", ephemeral=True)
        # Vérification que les nombres utilisés sont dans la pool
        found_numbers = [int(x) for x in re.findall(r"\d+", expr)]
        pool = self.numbers.copy()
        for n in found_numbers:
            if n in pool:
                pool.remove(n)
            else:
                return await safe_respond(interaction, "❌ Nombre non disponible ou utilisé trop de fois.", ephemeral=True)
        result = safe_eval(expr)
        if result is None:
            return await safe_respond(interaction, "❌ Calcul invalide.", ephemeral=True)
        if result == self.target:
            self.parent_view.finished = True
            if self.parent_view.message:
                embed = self.parent_view.build_embed()
                embed.color = discord.Color.green()
                embed.set_footer(text=f"🎉 Exact ! {interaction.user.display_name} a trouvé {self.target}")
                await safe_edit(self.parent_view.message, embed=embed)
            return await safe_respond(interaction, "✅ Exact ! Tu as trouvé la cible.", ephemeral=True)
        # Sinon on ajoute l'essai (mais on ne garde pas de messages visibles)
        self.parent_view.attempts.append((interaction.user.display_name, expr, result))
        await safe_respond(interaction, f"✅ Proposition enregistrée — écart {abs(self.target - result)}.", ephemeral=True)

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ Bouton Proposer
# ────────────────────────────────────────────────────────────────────────────────
class CompteBonButton(Button):
    def __init__(self, parent_view):
        super().__init__(label="🧮 Proposer un calcul", style=discord.ButtonStyle.primary)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        if not self.parent_view.multi and interaction.user.id != self.parent_view.author_id:
            return await safe_respond(interaction, "❌ Seul le lanceur peut proposer en solo.", ephemeral=True)
        await interaction.response.send_modal(CompteBonModal(self.parent_view, self.parent_view.numbers, self.parent_view.target))

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ Vue principale du jeu
# ────────────────────────────────────────────────────────────────────────────────
class CompteBonView(View):
    def __init__(self, numbers, target, multi=False, author_id=None):
        super().__init__(timeout=None)
        self.numbers = numbers
        self.target = target
        self.multi = multi
        self.author_id = author_id
        self.attempts = []
        self.message = None
        self.finished = False
        self.start_time = asyncio.get_event_loop().time()
        self.add_item(CompteBonButton(self))

    def build_embed(self) -> discord.Embed:
        mode_text = "Multi 🌍" if self.multi else "Solo 🧍‍♂️"
        embed = discord.Embed(
            title=f"🧮 Le Compte est Bon - {mode_text}",
            description=f"**But :** Atteindre `{self.target}` avec les nombres :\n`{'  '.join(map(str, self.numbers))}`",
            color=discord.Color.gold()
        )
        instructions = (
            "💡 **Comment jouer :**\n"
            "1️⃣ Cliquez sur **🧮 Proposer un calcul**.\n"
            "2️⃣ Utilisez uniquement les nombres affichés et les opérateurs + - * /.\n"
            "3️⃣ La partie se termine après 3 minutes ou si quelqu'un trouve la cible.\n"
            "4️⃣ Mode solo : seul le lanceur peut proposer.\n"
            "5️⃣ Mode multi : tout le monde peut proposer."
        )
        embed.add_field(name="📝 Instructions", value=instructions, inline=False)
        if self.finished:
            embed.color = discord.Color.green() if any(r == self.target for _, _, r in self.attempts) else discord.Color.red()
            embed.set_footer(text=f"💀 Partie terminée. La cible était {self.target}")
        else:
            remaining = max(0, 180 - int(asyncio.get_event_loop().time() - self.start_time))
            embed.set_footer(text=f"⏳ Temps restant : {remaining} secondes")
        return embed

    async def start_timeout(self):
        while not self.finished:
            await asyncio.sleep(5)
            if asyncio.get_event_loop().time() - self.start_time >= 180:
                self.finished = True
                if self.message:
                    embed = self.build_embed()
                    embed.color = discord.Color.red()
                    embed.set_footer(text=f"💀 Temps écoulé ! La cible était {self.target}")
                    await safe_edit(self.message, embed=embed)

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class CompteEstBon(commands.Cog):
    """Commande /compte_est_bon et !compte_est_bon — Le Compte est Bon"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active_games: dict[int, CompteBonView] = {}

    async def _start_game(self, channel, user_id, multi=False):
        if channel.id in self.active_games and not self.active_games[channel.id].finished:
            return await safe_send(channel, "⚠️ Une partie est déjà en cours dans ce salon.")
        numbers, target = generate_numbers()
        view = CompteBonView(numbers, target, multi=multi, author_id=None if multi else user_id)
        view.message = await safe_send(channel, embed=view.build_embed(), view=view)
        self.active_games[channel.id] = view
        asyncio.create_task(view.start_timeout())

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(name="compte_est_bon", description="Joue au Compte est Bon (ajoute 'm' ou 'multi' pour le mode multi)")
    async def slash_compte(self, interaction: discord.Interaction, mode: str = None):
        multi = mode and mode.lower() in ("m", "multi")
        await interaction.response.defer()
        await self._start_game(interaction.channel, user_id=interaction.user.id, multi=multi)
        await interaction.delete_original_response()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="compte_est_bon", aliases=["lceb", "lecompteestbon"])
    async def prefix_compte(self, ctx, mode: str = None):
        multi = mode and mode.lower() in ("m", "multi")
        await self._start_game(ctx.channel, user_id=ctx.author.id, multi=multi)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = CompteEstBon(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Jeux"
    await bot.add_cog(cog)
