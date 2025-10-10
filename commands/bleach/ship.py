# ────────────────────────────────────────────────────────────────────────────────
# 📌 ship.py — Commande interactive /ship et !ship
# Objectif : Tester la compatibilité entre deux personnages de Bleach
# Catégorie : Bleach
# Accès : Public
# Cooldown : 1 utilisation / 3 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, button
import os
import json
import random
from utils.discord_utils import safe_send, safe_edit, safe_respond

# ────────────────────────────────────────────────────────────────────────────────
# 📂 Gestion des personnages
# ────────────────────────────────────────────────────────────────────────────────
CHAR_DIR = os.path.join("data", "personnages")

def load_character(name: str):
    """Charge un personnage depuis un JSON individuel"""
    path = os.path.join(CHAR_DIR, f"{name.lower()}.json")
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        char = json.load(f)
        char["image"] = char.get("images", [""])[0] if char.get("images") else ""
        return char

def list_characters():
    """Retourne la liste des noms de personnages disponibles"""
    files = os.listdir(CHAR_DIR)
    return [f.replace(".json", "") for f in files if f.endswith(".json")]

# ────────────────────────────────────────────────────────────────────────────────
# 🧮 Calcul du score de compatibilité
# ────────────────────────────────────────────────────────────────────────────────
def is_compatible(p1, p2):
    """Vérifie la compatibilité de genre et sexualité"""
    def can_love(person, target):
        if person["sexualite"].lower() == "hétéro":
            return target["genre"].lower() != person["genre"].lower()
        elif person["sexualite"].lower() == "homo":
            return target["genre"].lower() == person["genre"].lower()
        return True  # Inconnu ou bi (non renseigné)
    return can_love(p1, p2) and can_love(p2, p1)

def calculer_score(p1, p2):
    """Calcule un score de compatibilité logique et simple"""
    if not is_compatible(p1, p2):
        return 0
    score = 50  # base
    # --- Races communes
    races1 = set(p1.get("race", []))
    races2 = set(p2.get("race", []))
    commun_races = races1 & races2
    score += 10 * len(commun_races)
    # --- Traits de personnalité
    traits1 = set(p1.get("personnalite", []))
    traits2 = set(p2.get("personnalite", []))
    commun_traits = traits1 & traits2
    if len(commun_traits) >= 2:
        score += 15
    elif len(commun_traits) == 1:
        score += 5
    # --- Stats proches
    stats1 = p1.get("stats_base", {})
    stats2 = p2.get("stats_base", {})
    compte_proches = sum(
        1 for s in ["attaque", "defense", "pression", "kido", "intelligence", "rapidite"]
        if abs(stats1.get(s, 0) - stats2.get(s, 0)) < 20
    )
    if compte_proches >= 3:
        score += 10
    return max(0, min(score, 100))

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ Vue interactive : Bouton Nouveau Ship
# ────────────────────────────────────────────────────────────────────────────────
class ShipView(View):
    def __init__(self, persos):
        super().__init__(timeout=60)
        self.persos = persos

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True

    @button(label="💘 Nouveau ship", style=discord.ButtonStyle.blurple)
    async def nouveau_ship(self, interaction: discord.Interaction, button: discord.ui.Button):
        p1, p2 = random.sample(self.persos, 2)
        await self._send_result(interaction, p1, p2)

    async def _send_result(self, target, p1, p2):
        score = calculer_score(p1, p2)
        if score >= 90:
            reaction = "âmes sœurs 💞"
            color = discord.Color.magenta()
        elif score >= 70:
            reaction = "une excellente alchimie spirituelle ! 🔥"
            color = discord.Color.red()
        elif score >= 50:
            reaction = "une belle entente possible 🌸"
            color = discord.Color.orange()
        elif score >= 30:
            reaction = "relation instable... mais pas impossible 😬"
            color = discord.Color.yellow()
        else:
            reaction = "aucune chance... ils sont incompatibles 💔"
            color = discord.Color.blue()

        embed = discord.Embed(title="💘 Test de compatibilité 💘", color=color)
        embed.add_field(name="👩‍❤️‍👨 Couple", value=f"**{p1['nom']}** ❤️ **{p2['nom']}**", inline=False)
        embed.add_field(name="🔢 Taux d’affinité", value=f"`{score}%`", inline=True)
        embed.add_field(name="💬 Verdict", value=f"*{reaction}*", inline=False)
        embed.set_thumbnail(url=p1["image"])
        embed.set_image(url=p2["image"])

        if isinstance(target, discord.abc.Messageable):
            await safe_send(target, embed=embed, view=self)
        else:
            await target.response.send_message(embed=embed, view=self)

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class ShipCommand(commands.Cog):
    """Commande /ship et !ship — Tire au sort deux personnages de Bleach et calcule leur compatibilité"""
    def __init__(self, bot):
        self.bot = bot

    async def _send_ship(self, channel: discord.abc.Messageable, p1_name=None, p2_name=None):
        persos = [load_character(n) for n in list_characters()]
        persos = [p for p in persos if p is not None]

        if len(persos) < 2:
            await safe_send(channel, "❌ Il faut au moins **deux personnages** pour créer un ship.")
            return

        if p1_name and p2_name:
            p1 = load_character(p1_name) or random.choice(persos)
            p2 = load_character(p2_name) or random.choice(persos)
        else:
            p1, p2 = random.sample(persos, 2)

        view = ShipView(persos)
        await view._send_result(channel, p1, p2)

    # 🔹 Commande SLASH
    @app_commands.command(name="ship", description="💘 Teste la compatibilité entre deux personnages de Bleach.")
    @app_commands.describe(p1="Nom du premier personnage", p2="Nom du second personnage")
    @app_commands.checks.cooldown(1, 3.0, key=lambda i: i.user.id)
    async def slash_ship(self, interaction: discord.Interaction, p1: str = None, p2: str = None):
        await self._send_ship(interaction.channel, p1_name=p1, p2_name=p2)

    # 🔹 Commande PREFIX
    @commands.command(name="ship")
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def prefix_ship(self, ctx: commands.Context, p1: str = None, p2: str = None):
        await self._send_ship(ctx.channel, p1_name=p1, p2_name=p2)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = ShipCommand(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Bleach"
    await bot.add_cog(cog)


