# ────────────────────────────────────────────────────────────────────────────────
# 📌 combat.py — Commande interactive /combat et !combat
# Objectif : Combat style Pokémon complet avec statuts et formes évolutives
# Catégorie : Bleach
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
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

from utils.discord_utils import safe_send, safe_respond, safe_interact

# ────────────────────────────────────────────────────────────────────────────────
# 📂 Gestion des personnages et combat
# ────────────────────────────────────────────────────────────────────────────────
CHAR_DIR    = os.path.join("data", "personnages")
COMBAT_FILE = os.path.join("data", "combat.json")

with open(COMBAT_FILE, "r", encoding="utf-8") as f:
    COMBAT_DATA = json.load(f)

TYPE_EFF        = COMBAT_DATA["type_effectiveness"]
TYPE_EMOJI      = COMBAT_DATA["types_emoji"]
CATEGORIE_EMOJI = COMBAT_DATA["categories_emoji"]
STATUTS         = COMBAT_DATA["statuts"]
BOOSTS          = COMBAT_DATA["boosts"]

def load_character(name: str):
    """Charge un personnage depuis le dossier data/personnages."""
    path = os.path.join(CHAR_DIR, f"{name.lower()}.json")
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        char = json.load(f)
        char["image"] = char.get("images", [""])[0] if char.get("images") else ""
        return char

def list_characters():
    """Liste tous les personnages disponibles."""
    return [f.replace(".json", "") for f in os.listdir(CHAR_DIR) if f.endswith(".json")]

def multiplier_type(atk_type, cible_type):
    """Retourne le multiplicateur de type."""
    return TYPE_EFF.get(atk_type, {}).get(cible_type, 1)

def init_combat(p: dict):
    """Initialise un personnage pour le combat."""
    p = p.copy()
    p["pv"]            = p["stats_base"]["pv"]
    p["boosts"]        = {b: 0 for b in BOOSTS}
    p["statut"]        = None
    p["forme_actuelle"] = "Normal"
    p["sleep_turns"]   = 0
    for f in p["formes"].values():
        for a in f["attaques"]:
            a["PP"] = a.get("pp_max", 10)
    return p

def attaque_disponible(p: dict):
    """Retourne les attaques avec PP > 0."""
    return [a for a in p["formes"][p["forme_actuelle"]]["attaques"] if a["PP"] > 0]

# ────────────────────────────────────────────────────────────────────────────────
# 🔧 Gestion des statuts
# ────────────────────────────────────────────────────────────────────────────────
def appliquer_statut(p: dict, narratif: list):
    """Applique les effets des statuts sur le personnage."""
    if not p["statut"]:
        return False
    s = STATUTS[p["statut"]]
    if p["statut"] == "Paralysie":
        if random.random() < s["chance_move"]:
            narratif.append(f"{s['emoji']} **{p['nom']}** est paralysé et rate son tour !")
            return True
    elif p["statut"] == "Sommeil":
        if p["sleep_turns"] == 0:
            p["sleep_turns"] = random.randint(1, s["tour_max"])
        if p["sleep_turns"] > 0:
            p["sleep_turns"] -= 1
            narratif.append(f"{s['emoji']} **{p['nom']}** dort et ne peut agir !")
            return True
    elif p["statut"] == "Gel":
        if random.random() < s["chance_move"]:
            narratif.append(f"{s['emoji']} **{p['nom']}** est gelé et rate son tour !")
            return True
    elif p["statut"] == "Confusion":
        if random.random() < s["chance_self"]:
            deg = s["degats"]
            p["pv"] -= deg
            narratif.append(f"{s['emoji']} **{p['nom']}** est confus et se blesse ({deg} PV) !")
            return True
    elif p["statut"] == "Poison":
        deg = s["degats"]
        p["pv"] -= deg
        narratif.append(f"{s['emoji']} **{p['nom']}** subit {deg} PV de dégâts de poison !")
    elif p["statut"] == "Brûlure":
        deg     = s["degats"]
        atk_mod = s["attaque_mod"]
        p["pv"] -= deg
        p["boosts"]["attaque"] *= atk_mod
        narratif.append(f"{s['emoji']} **{p['nom']}** subit {deg} PV de brûlure et attaque réduite !")
    return False

# ────────────────────────────────────────────────────────────────────────────────
# 🔧 Calcul et application des dégâts
# ────────────────────────────────────────────────────────────────────────────────
def calcul_degats(a, d, atk):
    """Calcul des dégâts style Pokémon."""
    if atk["categorie"] == "Physique":
        atk_stat = a["stats_base"]["attaque"] * (1 + a["boosts"].get("attaque", 0) / 2)
        def_stat = d["stats_base"]["defense"] * (1 + d["boosts"].get("defense", 0) / 2)
    elif atk["categorie"] == "Spécial":
        atk_stat = a["stats_base"]["special"] * (1 + a["boosts"].get("special", 0) / 2)
        def_stat = d["stats_base"]["special_def"] * (1 + d["boosts"].get("special_def", 0) / 2)
    else:
        return 0, 1, False

    base = ((2 * 50 / 5 + 2) * atk["puissance"] * (atk_stat / def_stat)) / 50 + 2
    mult = multiplier_type(atk["type"], d["type"][0])
    rand = random.uniform(0.85, 1)
    crit = 1.5 if random.random() < 0.0625 else 1
    return int(base * mult * rand * crit), mult, crit > 1

def appliquer_attaque(a, d, atk, narratif):
    """Applique une attaque (Soin / Statut / Dégâts / Antithèse / Boost)."""

    # ─── Soin ───
    if atk["categorie"] == "Soin":
        soin   = atk["puissance"]
        a["pv"] = min(a["stats_base"]["pv"], a["pv"] + soin)
        narratif.append(f"{CATEGORIE_EMOJI['Soin']} **{a['nom']}** utilise *{atk['nom']}* et récupère {soin} PV !")
        return

    # ─── Statut ───
    if atk["categorie"] == "Statut" and atk.get("statut") != "Antithèse":
        narratif.append(f"{CATEGORIE_EMOJI['Statut']} **{a['nom']}** utilise *{atk['nom']}* !")
        if atk.get("statut"):
            d["statut"] = atk["statut"]
            s = STATUTS[atk["statut"]]
            narratif.append(f"{s['emoji']} **{d['nom']}** est affecté par **{atk['statut']}** !")
        if atk.get("boosts"):
            for stat, value in atk["boosts"].items():
                target = a if value > 0 else d
                target["boosts"][stat] += abs(value)
                narratif.append(f"⚡ **{target['nom']}** voit sa statistique **{stat}** {'augmentée' if value > 0 else 'diminuée'} !")
        return

    # ─── Antithèse ───
    if atk.get("statut") == "Antithèse":
        a["pv"],     d["pv"]     = d["pv"],     a["pv"]
        a["boosts"], d["boosts"] = d["boosts"], a["boosts"]
        a["statut"], d["statut"] = d["statut"], a["statut"]
        narratif.append(f"🔁 **{a['nom']}** active *{atk['nom']}* ! Tous les effets entre **{a['nom']}** et **{d['nom']}** sont inversés !")
        return

    # ─── Offensif ───
    degats, mult, crit = calcul_degats(a, d, atk)
    d["pv"] -= degats
    emoji_type = TYPE_EMOJI.get(atk["type"], "")
    txt = f"{CATEGORIE_EMOJI.get(atk['categorie'], '⚔️')} **{a['nom']}** utilise *{atk['nom']}* {emoji_type} et inflige {degats} PV !"
    if crit: txt += " ⚡ Coup critique !"
    if mult > 1: txt += " 💥 Super efficace !"
    elif mult < 1: txt += " ⚠️ Peu efficace..."
    narratif.append(txt)
    if atk.get("statut") and atk["statut"] not in ["Antithèse"]:
        d["statut"] = atk["statut"]

# ────────────────────────────────────────────────────────────────────────────────
# 🔧 Forme suivante (évolution en combat)
# ────────────────────────────────────────────────────────────────────────────────
def forme_suivante(p: dict):
    """Gestion de l'évolution en combat."""
    formes = list(p["formes"].keys())
    idx    = formes.index(p["forme_actuelle"])
    if idx < len(formes) - 1 and random.random() < 0.15:
        p["forme_actuelle"] = formes[idx + 1]
        return f"✨ **{p['nom']}** passe en **{p['forme_actuelle']}** !"
    return None

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────

class CombatCommand(commands.Cog):
    """Commandes /combat et !combat — Combat style Pokémon complet avec statuts et formes évolutives."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction interne commune
    # ────────────────────────────────────────────────────────────────────────────
    async def _run_combat(self, channel: discord.abc.Messageable):
        persos = [p for p in (load_character(n) for n in list_characters()) if p]
        if len(persos) < 2:
            return await safe_send(channel, "❌ Pas assez de personnages.")

        p1, p2   = random.sample(persos, 2)
        p1, p2   = init_combat(p1), init_combat(p2)
        narratif = [f"⚔️ **Combat : {p1['nom']} vs {p2['nom']}** ⚔️\n"]

        tour = 0
        while p1["pv"] > 0 and p2["pv"] > 0 and tour < 50:
            tour += 1
            narratif.append(f"\n🔁 **Tour {tour}**")
            tour_order = sorted([p1, p2], key=lambda x: x["stats_base"]["rapidite"] + random.randint(0, 10), reverse=True)
            for attaquant in tour_order:
                defenseur = p2 if attaquant == p1 else p1
                if attaquant["pv"] <= 0 or defenseur["pv"] <= 0:
                    continue
                if appliquer_statut(attaquant, narratif):
                    continue
                dispo = attaque_disponible(attaquant)
                if not dispo:
                    atk = {"nom": "Tacle", "type": "Normal", "categorie": "Physique", "puissance": 40, "PP": 1}
                else:
                    atk = random.choice(dispo)
                    atk["PP"] -= 1
                appliquer_attaque(attaquant, defenseur, atk, narratif)
                fs = forme_suivante(attaquant)
                if fs:
                    narratif.append(fs)
                if defenseur["pv"] <= 0:
                    narratif.append(f"\n🏆 **{attaquant['nom']}** remporte le combat !")
                    break
            else:
                continue
            break

        # ─── Pagination du narratif ───
        PAGINATION_TAILLE = 3500
        texte_combat = "\n".join(narratif)
        pages = [texte_combat[i:i + PAGINATION_TAILLE] for i in range(0, len(texte_combat), PAGINATION_TAILLE)]
        index = 0

        embed = discord.Embed(
            title=f"🗡️ {p1['nom']} vs {p2['nom']}",
            description=pages[index],
            color=discord.Color.red()
        )
        embed.set_thumbnail(url=p1["image"])
        embed.set_image(url=p2["image"])

        class PagesView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=120)

            @discord.ui.button(label="◀️", style=discord.ButtonStyle.secondary)
            async def prev(self, interaction: discord.Interaction, button: discord.ui.Button):
                nonlocal index
                index           = (index - 1) % len(pages)
                embed.description = pages[index]
                await safe_interact(interaction, embed=embed, view=self, edit=True)

            @discord.ui.button(label="▶️", style=discord.ButtonStyle.secondary)
            async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
                nonlocal index
                index           = (index + 1) % len(pages)
                embed.description = pages[index]
                await safe_interact(interaction, embed=embed, view=self, edit=True)

        await safe_send(channel, embed=embed, view=PagesView())

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(name="combat",description="⚔️ Combat style Pokémon entre 2 persos.")
    @app_commands.checks.cooldown(rate=1, per=5.0, key=lambda i: i.user.id)
    async def slash_combat(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self._run_combat(interaction.channel)
        await interaction.delete_original_response()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="combat",help="⚔️ Combat style Pokémon entre 2 persos.")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_combat(self, ctx: commands.Context):
        await self._run_combat(ctx.channel)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = CombatCommand(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Bleach"
    await bot.add_cog(cog)
