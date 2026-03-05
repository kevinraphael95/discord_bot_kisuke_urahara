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
import json
import os
import random

import discord
from discord import app_commands
from discord.ext import commands

from utils.discord_utils import safe_send

# ────────────────────────────────────────────────────────────────────────────────
# 📂 Dossier contenant les JSON des personnages
# ────────────────────────────────────────────────────────────────────────────────
CHAR_DIR = os.path.join("data", "personnages")

def load_character(name: str):
    """Charge la fiche JSON d'un personnage par nom."""
    path = os.path.join(CHAR_DIR, f"{name.lower()}.json")
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def list_characters():
    """Liste tous les personnages disponibles."""
    return [f.replace(".json", "") for f in os.listdir(CHAR_DIR) if f.endswith(".json")]

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────

class Perso(commands.Cog):
    """Commandes /perso et !perso — Affiche la fiche d'un personnage."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction interne commune
    # ────────────────────────────────────────────────────────────────────────────
    async def _send_character(self, channel: discord.abc.Messageable, name: str = None):
        if not name:
            name = random.choice(list_characters())

        char = load_character(name)
        if not char:
            await safe_send(channel, f"❌ Personnage `{name}` introuvable.")
            return

        embed = discord.Embed(
            title=f"{char.get('nom', 'Inconnu')}",
            description=f"**Genre:** {char.get('genre', 'N/A')} | **Sexualité:** {char.get('sexualite', 'N/A')}",
            color=discord.Color.orange()
        )
        embed.add_field(name="Personnalité", value=", ".join(char.get("personnalite", ["N/A"])), inline=False)
        embed.add_field(name="Race(s)",      value=", ".join(char.get("race",         ["N/A"])), inline=False)
        embed.add_field(name="Type(s)",      value=", ".join(char.get("type",         ["N/A"])), inline=False)

        # ─── Stats ───
        stats       = char.get("stats_base", {})
        total_stats = sum(stats.get(k, 0) for k in ["pv", "attaque", "defense", "special", "special_def", "rapidite"])
        embed.add_field(
            name="Stats de base",
            value=(
                f"• PV : {stats.get('pv', 0)}\n"
                f"• Attaque : {stats.get('attaque', 0)}\n"
                f"• Défense : {stats.get('defense', 0)}\n"
                f"• Spécial : {stats.get('special', 0)}\n"
                f"• Spécial Défense : {stats.get('special_def', 0)}\n"
                f"• Rapidité : {stats.get('rapidite', 0)}\n"
                f"• Total stats : {total_stats}"
            ),
            inline=False
        )

        # ─── Formes + attaques ───
        for forme_name, forme in char.get("formes", {}).items():
            attaques_text_list = []
            for atk in forme.get("attaques", []):
                if atk.get("statut"):
                    effet_text = f"  └ Effet : {atk['statut']}"
                elif atk.get("boosts"):
                    effet_text = "  └ Boost : " + ", ".join(f"{k} +{v}" for k, v in atk["boosts"].items())
                else:
                    effet_text = ""
                attaques_text_list.append(
                    f"• **{atk.get('nom', 'Inconnu')}**\n"
                    f"  ├ Puissance : {atk.get('puissance', 0)}\n"
                    f"  ├ PP max : {atk.get('pp_max', 0)}\n"
                    f"  ├ Type : {atk.get('type', 'Normal')}\n"
                    f"{effet_text}"
                )
            embed.add_field(
                name=f"Forme: {forme_name}",
                value=(
                    f"**Activation :** {forme.get('activation') or 'N/A'}\n"
                    + ("\n".join(attaques_text_list) or "Aucune attaque.")
                ),
                inline=False
            )

        # ─── Image ───
        images     = char.get("images") or []
        image_path = images[0] if images else "data/images/image_par_defaut.jpg"

        if image_path.startswith("http"):
            embed.set_image(url=image_path)
            await safe_send(channel, embed=embed)
        elif os.path.exists(image_path):
            file = discord.File(image_path, filename=os.path.basename(image_path))
            embed.set_image(url=f"attachment://{os.path.basename(image_path)}")
            await safe_send(channel, embed=embed, file=file)
        else:
            await safe_send(channel, embed=embed)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="perso",
        description="Affiche la fiche d'un personnage Bleach."
    )
    @app_commands.describe(name="Nom du personnage (laisser vide pour aléatoire)")
    @app_commands.checks.cooldown(rate=1, per=5.0, key=lambda i: i.user.id)
    async def slash_perso(self, interaction: discord.Interaction, name: str = None):
        await interaction.response.defer()
        await self._send_character(interaction.channel, name)
        await interaction.delete_original_response()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(
        name="perso",
        help="Affiche la fiche d'un personnage Bleach."
    )
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_perso(self, ctx: commands.Context, *, name: str = None):
        await self._send_character(ctx.channel, name)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Perso(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Bleach"
    await bot.add_cog(cog)
