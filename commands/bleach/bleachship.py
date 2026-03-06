# ────────────────────────────────────────────────────────────────────────────────
# 📌 bleachship.py — Commande interactive /bleachship et !bleachship (alias !bship)
# Objectif : Tester la compatibilité entre deux personnages de Bleach
# Catégorie : Bleach
# Accès : Public
# Cooldown : 1 utilisation / 3 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import json
import os
import random

import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, button

from utils.discord_utils import safe_send, safe_edit, safe_respond, safe_followup, safe_interact

# ────────────────────────────────────────────────────────────────────────────────
# 📂 Gestion des personnages
# ────────────────────────────────────────────────────────────────────────────────
CHAR_DIR = os.path.join("data", "personnages")

def load_character(name: str):
    path = os.path.join(CHAR_DIR, f"{name.lower()}.json")
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        char = json.load(f)
        char["image"] = char.get("images", [""])[0] if char.get("images") else ""
        return char

def list_characters():
    files = os.listdir(CHAR_DIR)
    return [f.replace(".json", "") for f in files if f.endswith(".json")]

# ────────────────────────────────────────────────────────────────────────────────
# 🧮 Calcul du score de compatibilité
# ────────────────────────────────────────────────────────────────────────────────
def compatibilite_amoureuse(p1, p2):
    def peut_aimer(person, cible):
        if person["sexualite"].lower() == "hétéro":
            return cible["genre"].lower() != person["genre"].lower()
        elif person["sexualite"].lower() == "homo":
            return cible["genre"].lower() == person["genre"].lower()
        return True

    if not (peut_aimer(p1, p2) and peut_aimer(p2, p1)):
        return 0.2
    s1, s2 = p1["sexualite"].lower(), p2["sexualite"].lower()
    g1, g2 = p1["genre"].lower(), p2["genre"].lower()
    if s1 == "bi" and s2 == "bi": return 1.0
    if s1 == "hétéro" and s2 == "hétéro" and g1 != g2: return 0.9
    if s1 == "homo" and s2 == "homo" and g1 == g2: return 0.95
    if (s1 == "bi" and s2 in ["homo", "hétéro"]) or (s2 == "bi" and s1 in ["homo", "hétéro"]): return 0.85
    return 0.5

def calculer_score(p1, p2):
    score = 50
    score *= compatibilite_amoureuse(p1, p2)
    commun_races = set(p1.get("race", [])) & set(p2.get("race", []))
    score += 10 * len(commun_races)
    commun_traits = set(p1.get("personnalite", [])) & set(p2.get("personnalite", []))
    if len(commun_traits) >= 3: score += 20
    elif len(commun_traits) == 2: score += 10
    elif len(commun_traits) == 1: score += 5
    stats1, stats2 = p1.get("stats_base", {}), p2.get("stats_base", {})
    compte_proches = sum(
        1 for s in ["attaque", "defense", "pression", "kido", "intelligence", "rapidite"]
        if abs(stats1.get(s, 0) - stats2.get(s, 0)) < 20
    )
    if compte_proches >= 4: score += 15
    elif compte_proches >= 2: score += 5
    return max(0, min(int(score), 100))

def generate_ship_embed(p1, p2):
    score = calculer_score(p1, p2)
    if score >= 90:
        reaction, color = "âmes sœurs 💞", discord.Color.magenta()
    elif score >= 70:
        reaction, color = "une excellente alchimie spirituelle ! 🔥", discord.Color.red()
    elif score >= 50:
        reaction, color = "une belle entente possible 🌸", discord.Color.orange()
    elif score >= 30:
        reaction, color = "relation instable... mais pas impossible 😬", discord.Color.yellow()
    else:
        reaction, color = "aucune chance... ils sont incompatibles 💔", discord.Color.blue()

    embed = discord.Embed(title="💘 Test de compatibilité Bleach 💘", color=color)
    embed.add_field(name="👩‍❤️‍👨 Couple", value=f"**{p1['nom']}** ❤️ **{p2['nom']}**", inline=False)
    embed.add_field(name="🔢 Taux d'affinité", value=f"`{score}%`", inline=True)
    embed.add_field(name="💬 Verdict", value=f"*{reaction}*", inline=False)
    embed.set_thumbnail(url=p1["image"])
    embed.set_image(url=p2["image"])
    return embed

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ UI — View avec bouton régénération
# ────────────────────────────────────────────────────────────────────────────────

class BleachShipView(View):
    def __init__(self, persos: list, author: discord.User | discord.Member):
        super().__init__(timeout=60)
        self.persos  = persos
        self.author  = author
        self.message: discord.Message | None = None

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message:
            try:
                await safe_edit(self.message, view=self)
            except Exception:
                pass

    @button(label="💘 Nouveau ship", style=discord.ButtonStyle.blurple)
    async def nouveau_ship(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            return await safe_interact(interaction, content="❌ Ce n'est pas ton ship !", ephemeral=True)
        p1, p2    = random.sample(self.persos, 2)
        new_embed = generate_ship_embed(p1, p2)
        await safe_interact(interaction, edit=True, embed=new_embed, view=self)

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────

class BleachShipCommand(commands.Cog):
    """Commandes /bleachship et !bleachship — Teste la compatibilité entre deux personnages de Bleach."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction interne commune
    # ────────────────────────────────────────────────────────────────────────────
    def _build_ship(self, p1_name: str | None, p2_name: str | None) -> tuple[discord.Embed, BleachShipView, list] | None:
        """Charge les personnages, calcule le ship et retourne l'embed + la view."""
        persos = [p for p in (load_character(n) for n in list_characters()) if p is not None]
        if len(persos) < 2:
            return None
        p1 = (load_character(p1_name) if p1_name else None) or random.choice(persos)
        p2 = (load_character(p2_name) if p2_name else None) or random.choice(persos)
        return generate_ship_embed(p1, p2), persos

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(name="bleachship",description="💘 Teste la compatibilité entre deux personnages de Bleach.")
    @app_commands.describe(p1="Nom du premier personnage", p2="Nom du second personnage")
    @app_commands.checks.cooldown(rate=1, per=3.0, key=lambda i: i.user.id)
    async def slash_bleachship(self, interaction: discord.Interaction, p1: str = None, p2: str = None):
        result = self._build_ship(p1, p2)
        if result is None:
            return await safe_respond(interaction, "❌ Il faut au moins deux personnages pour créer un ship.", ephemeral=True)
        embed, persos = result
        view          = BleachShipView(persos, interaction.user)
        await safe_respond(interaction, embed=embed, view=view)
        view.message  = await interaction.original_response()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="bleachship",aliases=["bship"],help="💘 Teste la compatibilité entre deux personnages de Bleach.")
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def prefix_bleachship(self, ctx: commands.Context, p1: str = None, p2: str = None):
        result = self._build_ship(p1, p2)
        if result is None:
            return await safe_send(ctx.channel, "❌ Il faut au moins deux personnages pour créer un ship.")
        embed, persos = result
        view          = BleachShipView(persos, ctx.author)
        view.message  = await safe_send(ctx.channel, embed=embed, view=view)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = BleachShipCommand(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Bleach"
    await bot.add_cog(cog)
