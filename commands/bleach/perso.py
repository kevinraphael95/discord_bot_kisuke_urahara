# ────────────────────────────────────────────────────────────────────────────────
# 📌 perso.py — Commande interactive /perso et !perso
# Objectif : Affiche la fiche d'un personnage Bleach depuis un JSON
# Catégorie : Bleach
# Accès : Tous
# Cooldown : 5s par utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import random

from utils.discord_utils import safe_send

# ────────────────────────────────────────────────────────────────────────────────
# 📂 Dossier contenant les JSON des personnages
# ────────────────────────────────────────────────────────────────────────────────
CHAR_DIR = os.path.join("data", "personnages")

with open("data/config_types.json", "r", encoding="utf-8") as f:
    CONFIG_TYPES = json.load(f)
TYPES_EMOJI = CONFIG_TYPES["types_emoji"]
CATEGORIES_EMOJI = CONFIG_TYPES["categories_emoji"]

def load_character(name: str):
    """Charge la fiche JSON d'un personnage par nom."""
    path = os.path.join(CHAR_DIR, f"{name.lower()}.json")
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def list_characters():
    """Liste tous les personnages disponibles."""
    files = os.listdir(CHAR_DIR)
    return [f.replace(".json", "") for f in files if f.endswith(".json")]

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class Perso(commands.Cog):
    """Commande /perso et !perso — Affiche la fiche d'un personnage."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def send_character(self, channel: discord.abc.Messageable, name: str = None, forme_name: str = "Normal"):
        # Choix aléatoire si aucun nom donné
        if not name:
            name = random.choice(list_characters())

        char = load_character(name)
        if not char:
            await safe_send(channel, f"❌ Personnage `{name}` introuvable.")
            return

        await self.send_embed(channel, char, forme_name)

    async def send_embed(self, channel, char, forme_name):
        """Embed d'une seule forme avec menu déroulant pour changer de forme."""
        forme = char.get("formes", {}).get(forme_name, {})
        stats = char.get("stats_base", {})
        total_stats = sum(stats.get(k,0) for k in ["pv","attaque","defense","special","special_def","rapidite"])
        types_text = " | ".join(f"{TYPES_EMOJI.get(t,t)} {t}" for t in char.get("type",[]))

        # ─────────────────────────────────────
        # 📌 Embed principal
        # ─────────────────────────────────────
        embed = discord.Embed(
            title=f"{char.get('nom','Inconnu')} — Forme : {forme_name}",
            description=f"**Genre:** {char.get('genre','N/A')} | **Sexualité:** {char.get('sexualite','N/A')}\n**Type:** {types_text}",
            color=discord.Color.orange()
        )

        embed.add_field(
            name="Personnalité",
            value=", ".join(char.get("personnalite", ["N/A"])),
            inline=False
        )
        embed.add_field(
            name="Race(s)",
            value=", ".join(char.get("race", ["N/A"])),
            inline=False
        )

        # ─────────────────────────────────────
        # 📊 Stats
        # ─────────────────────────────────────
        embed.add_field(
            name="Stats de base",
            value=(
                f"• PV : {stats.get('pv',0)}\n"
                f"• Attaque : {stats.get('attaque',0)}\n"
                f"• Défense : {stats.get('defense',0)}\n"
                f"• Spécial : {stats.get('special',0)}\n"
                f"• Spécial Défense : {stats.get('special_def',0)}\n"
                f"• Rapidité : {stats.get('rapidite',0)}\n"
                f"• Total stats : {total_stats}"
            ),
            inline=False
        )

        # ─────────────────────────────────────
        # 🗡️ Attaques de la forme
        # ─────────────────────────────────────
        attaques_text_list = []
        for atk in forme.get("attaques", []):
            effet_text = ""
            if atk.get("statut"):
                effet_text = f"  └ Effet : {atk['statut']}"
            elif atk.get("boosts"):
                effet_text = "  └ Boost : " + ", ".join(f"{k} +{v}" for k,v in atk["boosts"].items())
            attaques_text_list.append(
                f"• **{atk.get('nom','Inconnu')}**\n"
                f"  ├ Puissance : {atk.get('puissance',0)}\n"
                f"  ├ PP max : {atk.get('pp_max',0)}\n"
                f"  ├ Type : {atk.get('type','Normal')}\n"
                f"{effet_text}"
            )
        attaques_text = "\n".join(attaques_text_list) or "Aucune attaque."

        embed.add_field(
            name=f"Activation : {forme.get('activation') or 'N/A'}",
            value=attaques_text,
            inline=False
        )

        # ─────────────────────────────────────
        # 🖼️ Gestion des images
        # ─────────────────────────────────────
        images = char.get("images") or []
        image_path = images[0] if images else "data/images/image_par_defaut.jpg"

        if image_path.startswith("http"):
            embed.set_image(url=image_path)
        elif os.path.exists(image_path):
            file = discord.File(image_path, filename=os.path.basename(image_path))
            embed.set_image(url=f"attachment://{os.path.basename(image_path)}")
        else:
            file = None

        # ─────────────────────────────────────
        # Menu déroulant pour changer de forme
        # ─────────────────────────────────────
        class FormeSelect(discord.ui.Select):
            def __init__(self):
                options = [
                    discord.SelectOption(label=f, description=f"Voir la forme {f}", emoji=None)
                    for f in char.get("formes", {})
                ]
                super().__init__(placeholder="Choisir une forme", min_values=1, max_values=1, options=options)

            async def callback(self, interaction: discord.Interaction):
                await self.view.message.delete()
                await self.view.cog.send_embed(interaction.channel, char, self.values[0])

        class FormeView(discord.ui.View):
            def __init__(self, cog):
                super().__init__(timeout=120)
                self.cog = cog
                self.message = None
                self.add_item(FormeSelect())

        view = FormeView(self)
        if file:
            msg = await safe_send(channel, embed=embed, file=file, view=view)
        else:
            msg = await safe_send(channel, embed=embed, view=view)
        view.message = msg

    # ────────────────────────────────────────────────────────────────────────────
    # 🟦 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="perso",
        description="Affiche la fiche d'un personnage Bleach."
    )
    @app_commands.describe(name="Nom du personnage (laisser vide pour aléatoire)")
    @app_commands.checks.cooldown(rate=1, per=5.0, key=lambda i: i.user.id)
    async def slash_perso(self, interaction: discord.Interaction, name: str = None):
        await interaction.response.defer()
        await self.send_character(interaction.channel, name)
        await interaction.delete_original_response()

    # ────────────────────────────────────────────────────────────────────────────
    # 🟥 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="perso", help="Affiche la fiche d'un personnage Bleach.")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_perso(self, ctx: commands.Context, *, name: str = None):
        await self.send_character(ctx.channel, name)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Perso(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Bleach"
    await bot.add_cog(cog)
