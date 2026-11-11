# ================================================================================
# 📌 bleachship.py — Commande interactive /bleachship et !bleachship (alias !bship)
# Objectif : Tester la compatibilité entre deux personnages de Bleach
# Catégorie : Bleach
# Accès : Public
# Cooldown : 1 utilisation / 3 secondes / utilisateur
# ================================================================================

# ================================================================================
# 📦 Imports nécessaires
# ================================================================================
import random
import re
import unicodedata

import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, button

from utils.discord_anti429 import safe_send, safe_edit, safe_respond, safe_interact

# On importe les fonctions de perso.py pour aller chercher sur le wiki
try:
    from .perso import fetch_character, fetch_random_character, search_candidates
except ImportError:
    from perso import fetch_character, fetch_random_character, search_candidates

# ================================================================================
# 🧮 Détection de même famille
# ================================================================================
def get_wiki_field(char: dict, *aliases: str) -> str:
    """Récupère un champ de l'infobox wiki en ignorant la casse et les accents."""
    def norm(s):
        s = unicodedata.normalize('NFD', str(s).lower())
        s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
        return re.sub(r'[^a-z0-9]', '', s)
    
    wanted = [norm(a) for a in aliases]
    for label, value in char.get("fields", []):
        if norm(label) in wanted:
            return str(value)
    return ""

def split_list(val: str) -> list:
    return [s.strip().lower() for s in re.split(r',\s*', val) if s.strip()] if val else []

def a_meme_famille(p1, p2):
    """Retourne True si les deux persos ont au moins un mot en commun dans leur nom ou famille."""
    f1, f2 = get_wiki_field(p1, "Famille", "Family"), get_wiki_field(p2, "Famille", "Family")
    if f1 and f2:
        m1 = set(re.split(r'[,、\s]+', f1.lower()))
        m2 = set(re.split(r'[,、\s]+', f2.lower()))
        if any(x in m2 and len(x) > 2 for x in m1):
            return True
            
    mots1 = set(p1["title"].lower().split())
    mots2 = set(p2["title"].lower().split())
    return any(x in mots2 and len(x) > 2 for x in mots1)

# ================================================================================
# 🧮 Calcul du score de compatibilité
# ================================================================================
def extraire_mois(date: str) -> int:
    mois_map = {"janvier":1, "fevrier":2, "mars":3, "avril":4, "mai":5, "juin":6,
                "juillet":7, "aout":8, "septembre":9, "octobre":10, "novembre":11, "decembre":12}
    norm = unicodedata.normalize('NFD', (date or "").lower())
    norm = ''.join(c for c in norm if unicodedata.category(c) != 'Mn')
    
    for m, num in mois_map.items():
        if m in norm: return num
    match = re.search(r'\b(\d{1,2})[/\-](\d{1,2})\b', norm)
    if match:
        a, b = int(match.group(1)), int(match.group(2))
        return a if 1 <= a <= 12 else (b if 1 <= b <= 12 else 0)
    return 0

def calculer_score(p1, p2):
    # 🚫 Même famille → score 0
    if a_meme_famille(p1, p2):
        return 0

    score = 50

    # Race commune
    r1, r2 = split_list(get_wiki_field(p1, "Race", "Espèce")), split_list(get_wiki_field(p2, "Race", "Espèce"))
    score += 12 * len(set(r1) & set(r2))

    # Sexe
    g1, g2 = get_wiki_field(p1, "Sexe", "Genre").lower(), get_wiki_field(p2, "Sexe", "Genre").lower()
    if g1 and g2:
        score += 5 if g1 == g2 else 18

    # Affiliation
    a1, a2 = split_list(get_wiki_field(p1, "Affiliation")), split_list(get_wiki_field(p2, "Affiliation"))
    if set(a1) & set(a2): score += 12

    # Équipe
    e1, e2 = split_list(get_wiki_field(p1, "Équipe", "Equipe")), split_list(get_wiki_field(p2, "Équipe", "Equipe"))
    if set(e1) & set(e2): score += 8

    # Partenaire
    part1, part2 = get_wiki_field(p1, "Partenaire").lower(), get_wiki_field(p2, "Partenaire").lower()
    if p2["title"].lower() in part1 and p1["title"].lower() in part2: score += 20
    elif p2["title"].lower() in part1 or p1["title"].lower() in part2: score += 8

    # Anniversaire
    m1, m2 = extraire_mois(get_wiki_field(p1, "Anniversaire")), extraire_mois(get_wiki_field(p2, "Anniversaire"))
    if m1 and m1 == m2: score += 6

    # Statut vital
    s1, s2 = get_wiki_field(p1, "status", "Statut").lower(), get_wiki_field(p2, "status", "Statut").lower()
    dead = ["mort", "décédé", "deceased", "dead"]
    if any(d in s1 for d in dead) != any(d in s2 for d in dead): score -= 15

    # Taille / Poids
    t1_val, t2_val = get_wiki_field(p1, "Taille"), get_wiki_field(p2, "Taille")
    t1 = int(re.search(r'\d+', t1_val).group(0)) if re.search(r'\d+', t1_val) else 0
    t2 = int(re.search(r'\d+', t2_val).group(0)) if re.search(r'\d+', t2_val) else 0
    if t1 and t2 and abs(t1 - t2) <= 10: score += 4

    # Base d'opérations
    b1, b2 = split_list(get_wiki_field(p1, "Base d'opérations", "Base d'operations")), split_list(get_wiki_field(p2, "Base d'opérations", "Base d'operations"))
    if set(b1) & set(b2): score += 5

    # Si aucun champ n'a matché, le score monte un peu au hasard pour ne pas être bloqué à 50
    if score == 50 and r1 and r2: 
        score += random.randint(-10, 10)

    return max(0, min(int(score), 100))

def generate_ship_embed(p1, p2):
    # 🚫 Cas spécial : même famille → 0%
    if a_meme_famille(p1, p2):
        embed = discord.Embed(
            title="💘 Test de compatibilité Bleach 💘",
            color=discord.Color.dark_gray()
        )
        embed.add_field(
            name="👩‍❤️‍👨 Couple",
            value=f"**{p1['title']}** ❤️ **{p2['title']}**",
            inline=False
        )
        embed.add_field(
            name="🔢 Taux d'affinité",
            value="`0%`",
            inline=True
        )
        embed.add_field(
            name="💬 Verdict",
            value="*Non, parce que dans la même famille. 🚫*",
            inline=False
        )
        if p1.get("image"): embed.set_thumbnail(url=p1["image"])
        if p2.get("image"): embed.set_image(url=p2["image"])
        return embed

    # ✅ Cas normal
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
    embed.add_field(name="👩‍❤️‍👨 Couple", value=f"**{p1['title']}** ❤️ **{p2['title']}**", inline=False)
    embed.add_field(name="🔢 Taux d'affinité", value=f"`{score}%`", inline=True)
    embed.add_field(name="💬 Verdict", value=f"*{reaction}*", inline=False)
    if p1.get("image"): embed.set_thumbnail(url=p1["image"])
    if p2.get("image"): embed.set_image(url=p2["image"])
    return embed

# ================================================================================
# 🎛️ UI — View avec bouton régénération
# ================================================================================

class BleachShipView(View):
    def __init__(self, author: discord.User | discord.Member, session):
        super().__init__(timeout=60)
        self.author  = author
        self.session = session
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

        # ✅ On defer pour éviter le message privé et faire patienter
        await interaction.response.defer()

        # ✅ On boucle jusqu'à trouver 2 persos avec de vraies infobox
        p1, p2 = None, None
        attempts = 0
        while (not p1 or not p2) and attempts < 5:
            p1 = await fetch_random_character(self.session)
            p2 = await fetch_random_character(self.session)
            attempts += 1

        if not p1 or not p2 or p1["title"] == p2["title"]:
            return await safe_edit(interaction.message, content="❌ Impossible de trouver assez de personnages valides sur le wiki. Réessaie plus tard.", embed=None, view=None)

        new_embed = generate_ship_embed(p1, p2)
        await safe_edit(interaction.message, embed=new_embed, view=self)

# ================================================================================
# 🧠 Cog principal
# ================================================================================

class BleachShipCommand(commands.Cog):
    """Commandes /bleachship et !bleachship — Teste la compatibilité entre deux personnages de Bleach."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ============================================================================
    # 🔹 Fonction interne commune
    # ============================================================================
    async def _build_ship(self, p1_name: str | None, p2_name: str | None):
        session = getattr(self.bot, "aiohttp_session", None)
        if session is None:
            return {"embed": None, "error": "⏳ Le bot n'est pas encore prêt, réessaie dans un instant."}

        # --- Perso 1 ---
        if p1_name:
            p1 = await fetch_character(session, p1_name, require_character=True)
            if not p1:
                candidates = await search_candidates(session, p1_name)
                if candidates:
                    p1 = await fetch_character(session, candidates[0]["title"])
        else:
            # ✅ On force la recherche jusqu'à avoir un perso avec infobox
            p1 = None
            attempts = 0
            while not p1 and attempts < 5:
                p1 = await fetch_random_character(session)
                attempts += 1

        if not p1:
            return {"embed": None, "error": f"❌ Personnage `{p1_name or 'aléatoire'}` introuvable sur le wiki."}

        # --- Perso 2 ---
        if p2_name:
            p2 = await fetch_character(session, p2_name, require_character=True)
            if not p2:
                candidates = await search_candidates(session, p2_name)
                if candidates:
                    p2 = await fetch_character(session, candidates[0]["title"])
        else:
            p2 = None
            attempts = 0
            while (not p2 or (p1 and p2["title"] == p1["title"])) and attempts < 5:
                p2 = await fetch_random_character(session)
                attempts += 1

        if not p2:
            return {"embed": None, "error": f"❌ Personnage `{p2_name or 'aléatoire'}` introuvable sur le wiki."}

        embed = generate_ship_embed(p1, p2)
        return {"embed": embed, "error": None}

    # ============================================================================
    # 🔹 Commande SLASH
    # ============================================================================
    @app_commands.command(name="bleachship", description="💘 Teste la compatibilité entre deux personnages de Bleach.")
    @app_commands.describe(p1="Nom du premier personnage", p2="Nom du second personnage")
    @app_commands.checks.cooldown(rate=1, per=3.0, key=lambda i: i.user.id)
    async def slash_bleachship(self, interaction: discord.Interaction, p1: str = None, p2: str = None):
        await interaction.response.defer()
        
        result = await self._build_ship(p1, p2)
        if result["error"]:
            return await safe_respond(interaction, result["error"], ephemeral=True)
        
        session = getattr(self.bot, "aiohttp_session", None)
        view = BleachShipView(interaction.user, session)
        await safe_respond(interaction, embed=result["embed"], view=view)
        view.message = await interaction.original_response()

    # ============================================================================
    # 🔹 Commande PREFIX
    # ============================================================================
    @commands.command(name="bleachship", aliases=["bship"], help="💘 Teste la compatibilité entre deux personnages de Bleach.")
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def prefix_bleachship(self, ctx: commands.Context, p1: str = None, p2: str = None):
        async with ctx.typing():
            result = await self._build_ship(p1, p2)
            
        if result["error"]:
            return await safe_send(ctx.channel, result["error"])
            
        session = getattr(self.bot, "aiohttp_session", None)
        view = BleachShipView(ctx.author, session)
        view.message = await safe_send(ctx.channel, embed=result["embed"], view=view)

    # ============================================================================
    # 🔹 Gestion des cooldowns (sinon l'utilisateur ne voit rien)
    # ============================================================================
    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                f"⏳ Doucement ! Réessaie dans {error.retry_after:.1f}s.", ephemeral=True
            )
            return
        raise error

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.CommandOnCooldown):
            await safe_send(ctx.channel, f"⏳ Doucement ! Réessaie dans {error.retry_after:.1f}s.")
            return
        raise error

# ================================================================================
# 🔌 Setup du Cog
# ================================================================================
async def setup(bot: commands.Bot):
    cog = BleachShipCommand(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Bleach"
    await bot.add_cog(cog)
