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
import discord
from discord import app_commands
from discord.ext import commands
import random, os, json, asyncio
from utils.discord_utils import safe_send, safe_respond  # ✅ Utilitaires sécurisés

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
    p["pv"] = p["stats_base"]["pv"]
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
    degats = calcul_degats(a, d, atk)
    d["pv"] -= degats
    return f"**{a['nom']}** utilise *{atk['nom']}* et inflige {degats} PV à **{d['nom']}** !"

def barre_pv(current, maximum, length=20):
    """Retourne une barre de PV style Pokémon"""
    filled = int(current / maximum * length)
    empty = length - filled
    return f"🟥{'█'*filled}{'⬜'*empty} {current}/{maximum} PV"

def barre_pp(atk):
    filled = atk.get("PP",0)
    maximum = atk.get("pp_max",10)
    return f"🟦{'█'*filled}{'⬜'*(maximum-filled)} {filled}/{maximum} PP"

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class VersusCommand(commands.Cog):
    """
    Commande /versus et !versus — Combat interactif style Pokémon avec barres PV et PP
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="versus",
        description="⚔️ Lance un combat interactif contre le bot."
    )
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_versus(self, interaction: discord.Interaction):
        await self.run_combat(interaction)

    @commands.command(name="versus")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_versus(self, ctx: commands.Context):
        await self.run_combat(ctx)

    async def run_combat(self, ctx_or_inter):
        try:
            persos = [load_character(n) for n in list_characters()]
            persos = [p for p in persos if p]
            if len(persos) < 2:
                return await safe_send(ctx_or_inter, "❌ Pas assez de personnages.")

            p1 = init_combat(random.choice(persos))
            p2 = init_combat(random.choice([c for c in persos if c["nom"] != p1["nom"]]))

            def create_embed():
                embed = discord.Embed(
                    title=f"⚔️ {p1['nom']} VS {p2['nom']}",
                    description="\n".join(view.narratif) if view.narratif else "Le combat commence !",
                    color=discord.Color.red()
                )
                embed.add_field(name=f"{p1['nom']} (Joueur)", value=barre_pv(p1['pv'], p1['stats_base']['pv']), inline=False)
                embed.add_field(name=f"{p2['nom']} (Bot)", value=barre_pv(p2['pv'], p2['stats_base']['pv']), inline=False)
                embed.set_thumbnail(url=p1["image"])
                embed.set_image(url=p2["image"])
                return embed

            class AttackView(discord.ui.View):
                def __init__(self, player, bot_perso):
                    super().__init__(timeout=120)
                    self.player = player
                    self.bot_perso = bot_perso
                    self.narratif = []
                    self.message = None
                    self.turn = "player"
                    self.update_buttons()

                def update_buttons(self):
                    # Clear previous buttons
                    for child in self.children:
                        self.remove_item(child)
                    if self.turn != "player":
                        return
                    # Ajouter les attaques
                    self.attaques = self.player["formes"][self.player["forme_actuelle"]]["attaques"][:4]
                    for atk in self.attaques:
                        pp_text = f"[{atk.get('PP',0)}/{atk.get('pp_max',10)}]"
                        button = self.AttackButton(atk)
                        button.label = f"{atk['nom']} {pp_text}"
                        button.disabled = atk.get("PP",0) <= 0
                        self.add_item(button)
                    # Tacle par défaut si toutes les attaques à 0 PP
                    if not attaque_disponible(self.player):
                        atk = {"nom": "Tacle", "categorie": "Physique", "type": "Normal", "puissance": 40, "PP": 1, "pp_max": 1}
                        button = self.AttackButton(atk)
                        button.label = f"{atk['nom']} [1/1]"
                        self.add_item(button)

                class AttackButton(discord.ui.Button):
                    def __init__(self, attaque):
                        super().__init__(label=attaque["nom"], style=discord.ButtonStyle.primary)
                        self.atk = attaque

                    async def callback(self, interaction: discord.Interaction):
                        view: AttackView = self.view
                        if self.atk["PP"] <= 0:
                            await interaction.response.send_message(f"❌ Plus de PP pour *{self.atk['nom']}* !", ephemeral=True)
                            return
                        self.atk["PP"] -= 1
                        txt = appliquer_attaque(view.player, view.bot_perso, self.atk)
                        view.narratif.append(txt)
                        # Vérifie victoire
                        if view.bot_perso["pv"] <= 0:
                            view.narratif.append(f"🏆 **{view.player['nom']}** remporte le combat !")
                            for child in view.children:
                                child.disabled = True
                            await interaction.response.edit_message(embed=create_embed(), view=view)
                            return
                        view.turn = "bot"
                        view.update_buttons()
                        await interaction.response.edit_message(embed=create_embed(), view=view)
                        await view.bot_turn()

                async def bot_turn(self):
                    await asyncio.sleep(1)
                    dispo = attaque_disponible(self.bot_perso)
                    if not dispo:
                        atk = {"nom": "Tacle", "categorie": "Physique", "type": "Normal", "puissance": 40, "PP": 1, "pp_max": 1}
                    else:
                        atk = random.choice(dispo)
                        atk["PP"] -= 1
                    txt = appliquer_attaque(self.bot_perso, self.player, atk)
                    self.narratif.append(txt)
                    if self.player["pv"] <= 0:
                        self.narratif.append(f"🏆 **{self.bot_perso['nom']}** remporte le combat !")
                        for child in self.children:
                            child.disabled = True
                        await self.message.edit(embed=create_embed(), view=self)
                        return
                    self.turn = "player"
                    self.update_buttons()
                    await self.message.edit(embed=create_embed(), view=self)

            view = AttackView(p1, p2)
            view.message = await safe_send(ctx_or_inter, embed=create_embed(), view=view)

        except Exception as e:
            import traceback
            traceback.print_exc()
            await safe_send(ctx_or_inter, f"❌ Erreur dans !versus : `{e}`")

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = VersusCommand(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Bleach"
    await bot.add_cog(cog)
