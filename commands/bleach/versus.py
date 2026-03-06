# ────────────────────────────────────────────────────────────────────────────────
# 📌 versus.py — Commande interactive /versus et !versus
# Objectif : Combat interactif style Pokémon avec barres de PV et PP
# Catégorie : Bleach
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import asyncio
import json
import os
import random

import discord
from discord import app_commands
from discord.ext import commands

from utils.discord_utils import safe_send, safe_interact, safe_edit

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
    return [f.replace(".json", "") for f in os.listdir(CHAR_DIR) if f.endswith(".json")]

def init_combat(p: dict):
    p = p.copy()
    p["pv"]             = p["stats_base"]["pv"]
    p["forme_actuelle"] = "Normal"
    for a in p["formes"][p["forme_actuelle"]]["attaques"]:
        a["PP"] = a.get("pp_max", 10)
    return p

def attaque_disponible(p: dict):
    return [a for a in p["formes"][p["forme_actuelle"]]["attaques"] if a["PP"] > 0]

def calcul_degats(a, d, atk):
    if atk["categorie"] == "Physique":
        atk_stat = a["stats_base"]["attaque"]
        def_stat = d["stats_base"]["defense"]
    else:
        atk_stat = a["stats_base"]["special"]
        def_stat = d["stats_base"]["special_def"]
    base = ((2 * 50 / 5 + 2) * atk["puissance"] * (atk_stat / def_stat)) / 50 + 2
    rand = random.uniform(0.85, 1)
    crit = 1.5 if random.random() < 0.0625 else 1
    return int(base * rand * crit)

def appliquer_attaque(a, d, atk):
    degats   = calcul_degats(a, d, atk)
    d["pv"] -= degats
    return f"**{a['nom']}** utilise *{atk['nom']}* et inflige {degats} PV à **{d['nom']}** !"

def barre_pv(current, maximum, length=20):
    filled = int(current / maximum * length)
    return f"🟥{'█' * filled}{'⬜' * (length - filled)} {current}/{maximum} PV"

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────

class VersusCommand(commands.Cog):
    """
    Commandes /versus et !versus — Combat interactif style Pokémon avec barres PV et PP.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction interne commune
    # ────────────────────────────────────────────────────────────────────────────
    async def _run_combat(self, channel: discord.abc.Messageable):
        persos = [p for p in (load_character(n) for n in list_characters()) if p]
        if len(persos) < 2:
            return await safe_send(channel, "❌ Pas assez de personnages.")

        p1 = init_combat(random.choice(persos))
        p2 = init_combat(random.choice([c for c in persos if c["nom"] != p1["nom"]]))

        def create_embed(narratif: list) -> discord.Embed:
            embed = discord.Embed(
                title=f"⚔️ {p1['nom']} VS {p2['nom']}",
                description="\n".join(narratif) if narratif else "Le combat commence !",
                color=discord.Color.red()
            )
            embed.add_field(name=f"{p1['nom']} (Joueur)", value=barre_pv(p1["pv"], p1["stats_base"]["pv"]), inline=False)
            embed.add_field(name=f"{p2['nom']} (Bot)",    value=barre_pv(p2["pv"], p2["stats_base"]["pv"]), inline=False)
            embed.set_thumbnail(url=p1["image"])
            embed.set_image(url=p2["image"])
            return embed

        class AttackButton(discord.ui.Button):
            def __init__(self, attaque: dict):
                pp_text = f"[{attaque.get('PP', 0)}/{attaque.get('pp_max', 10)}]"
                super().__init__(
                    label=f"{attaque['nom']} {pp_text}",
                    style=discord.ButtonStyle.primary,
                    disabled=attaque.get("PP", 0) <= 0
                )
                self.atk = attaque

            async def callback(self, interaction: discord.Interaction):
                view: AttackView = self.view
                if self.atk["PP"] <= 0:
                    return await safe_respond(interaction, f"❌ Plus de PP pour *{self.atk['nom']}* !", ephemeral=True)

                self.atk["PP"] -= 1
                view.narratif.append(appliquer_attaque(p1, p2, self.atk))

                if p2["pv"] <= 0:
                    view.narratif.append(f"🏆 **{p1['nom']}** remporte le combat !")
                    for child in view.children:
                        child.disabled = True
                    await safe_interact(interaction, embed=create_embed(view.narratif), view=view, edit=True)
                    view.stop()
                    return

                view.turn = "bot"
                view._update_buttons()
                await safe_interact(interaction, embed=create_embed(view.narratif), view=view, edit=True)
                await view.bot_turn()

        class AttackView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=120)
                self.narratif = []
                self.message  = None
                self.turn     = "player"
                self._update_buttons()

            def _update_buttons(self):
                self.clear_items()
                if self.turn != "player":
                    return
                attaques = p1["formes"][p1["forme_actuelle"]]["attaques"][:4]
                for atk in attaques:
                    self.add_item(AttackButton(atk))
                if not attaque_disponible(p1):
                    tacle = {"nom": "Tacle", "categorie": "Physique", "type": "Normal", "puissance": 40, "PP": 1, "pp_max": 1}
                    self.add_item(AttackButton(tacle))

            async def bot_turn(self):
                await asyncio.sleep(1)
                dispo = attaque_disponible(p2)
                if not dispo:
                    atk = {"nom": "Tacle", "categorie": "Physique", "type": "Normal", "puissance": 40, "PP": 1, "pp_max": 1}
                else:
                    atk        = random.choice(dispo)
                    atk["PP"] -= 1

                self.narratif.append(appliquer_attaque(p2, p1, atk))

                if p1["pv"] <= 0:
                    self.narratif.append(f"🏆 **{p2['nom']}** remporte le combat !")
                    for child in self.children:
                        child.disabled = True
                    await safe_edit(self.message, embed=create_embed(self.narratif), view=self)
                    self.stop()
                    return

                self.turn = "player"
                self._update_buttons()
                await safe_edit(self.message, embed=create_embed(self.narratif), view=self)

        view         = AttackView()
        view.message = await safe_send(channel, embed=create_embed(view.narratif), view=view)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(name="versus",description="⚔️ Lance un combat interactif contre le bot.")
    @app_commands.checks.cooldown(rate=1, per=5.0, key=lambda i: i.user.id)
    async def slash_versus(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self._run_combat(interaction.channel)
        await interaction.delete_original_response()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="versus",help="⚔️ Lance un combat interactif contre le bot.")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_versus(self, ctx: commands.Context):
        await self._run_combat(ctx.channel)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = VersusCommand(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Bleach"
    await bot.add_cog(cog)
