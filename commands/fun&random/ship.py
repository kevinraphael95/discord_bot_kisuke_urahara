# ────────────────────────────────────────────────────────────────────────────────
# 📌 ship.py — Commande interactive /ship et !ship (membres du serveur)
# Objectif : Shipper deux membres du serveur avec un score déterministe permanent
# Catégorie : Fun&Random
# Accès : Tous
# Cooldown : 1 utilisation / 3 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import hashlib
import logging

import discord
from discord import app_commands
from discord.ext import commands

from utils.discord_utils import safe_send

log = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────────────────────────
# 🧮 Calcul du score déterministe (basé sur les IDs Discord)
# ────────────────────────────────────────────────────────────────────────────────

def calculer_score(id1: int, id2: int) -> int:
    """
    Génère un score TOUJOURS identique pour deux utilisateurs donnés.
    - Symétrique : A ship B == B ship A (IDs triés avant le hash)
    - Basé sur SHA-256 → distribution uniforme et reproductible
    - Retourne un entier entre 0 et 100
    """
    sorted_ids = sorted([id1, id2])
    seed       = f"ship:{sorted_ids[0]}:{sorted_ids[1]}"
    hash_bytes = hashlib.sha256(seed.encode()).digest()
    return int.from_bytes(hash_bytes[:4], "big") % 101

def get_verdict(score: int) -> tuple[str, discord.Color]:
    """Retourne le verdict et la couleur associés au score."""
    if score >= 95:
        return "MARIAGE IMMÉDIAT 💍 C'est une évidence cosmique !", discord.Color.magenta()
    elif score >= 85:
        return "Âmes sœurs ✨ Ils sont faits l'un pour l'autre !", discord.Color.from_rgb(255, 105, 180)
    elif score >= 70:
        return "Super alchimie 🔥 Ça pourrait vraiment bien marcher !", discord.Color.red()
    elif score >= 55:
        return "Belle entente 🌸 Il y a un potentiel sérieux ici !", discord.Color.orange()
    elif score >= 40:
        return "Pourquoi pas... 😊 Avec un peu d'effort, qui sait ?", discord.Color.yellow()
    elif score >= 25:
        return "Relation compliquée 😬 Ça risque d'être sportif...", discord.Color.from_rgb(180, 180, 0)
    elif score >= 10:
        return "Très peu probable 😅 Il faudrait un miracle !", discord.Color.dark_orange()
    else:
        return "Incompatibles totaux 💔 L'univers dit NON.", discord.Color.blue()

def build_bar(score: int) -> str:
    """Génère une barre de progression visuelle pour le score."""
    filled = round(score / 10)
    return "❤️" * filled + "🖤" * (10 - filled)

# ────────────────────────────────────────────────────────────────────────────────
# 🖼️ Génération de l'embed
# ────────────────────────────────────────────────────────────────────────────────

def generate_ship_embed(u1: discord.Member | discord.User, u2: discord.Member | discord.User) -> discord.Embed:
    """Construit et retourne l'embed du ship entre u1 et u2."""
    score          = calculer_score(u1.id, u2.id)
    verdict, color = get_verdict(score)
    bar            = build_bar(score)

    embed = discord.Embed(title="💘 Ship Meter 💘", color=color)
    embed.add_field(name="💑 Le couple",    value=f"**{u1.display_name}** ❤️ **{u2.display_name}**", inline=False)
    embed.add_field(name="🔢 Compatibilité", value=f"`{score}%`",  inline=True)
    embed.add_field(name="📊 Score",         value=bar,            inline=True)
    embed.add_field(name="💬 Verdict",       value=f"*{verdict}*", inline=False)
    embed.set_thumbnail(url=u1.display_avatar.url)
    embed.set_image(url=u2.display_avatar.url)
    embed.set_footer(text="⚠️ Ce score est définitif et immuable — l'univers a parlé.")
    return embed

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────

class ShipCommand(commands.Cog):
    """Commandes /ship et !ship — Shipper deux membres du serveur."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction interne commune
    # ────────────────────────────────────────────────────────────────────────────
    async def _send_ship(
        self,
        channel: discord.abc.Messageable,
        author:  discord.Member | discord.User,
        u1:      discord.Member | discord.User,
        u2:      discord.Member | discord.User | None = None,
    ):
        if u2 is None:
            u1, u2 = author, u1

        if u1.id == u2.id:
            return await safe_send(channel, "❌ On ne peut pas se shipper avec soi-même... ou si ? 🤔")

        await safe_send(channel, embed=generate_ship_embed(u1, u2))

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="ship",
        description="💘 Calcule la compatibilité entre deux membres du serveur."
    )
    @app_commands.describe(
        membre1="Premier membre (toi par défaut si un seul membre fourni)",
        membre2="Second membre (optionnel)"
    )
    @app_commands.checks.cooldown(rate=1, per=3.0, key=lambda i: i.user.id)
    async def slash_ship(self, interaction: discord.Interaction, membre1: discord.Member, membre2: discord.Member = None):
        await interaction.response.defer(ephemeral=True)
        await self._send_ship(interaction.channel, interaction.user, membre1, membre2)
        await interaction.delete_original_response()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(
        name="ship",
        help="💘 Ship deux membres. Usage : !ship @user | !ship @user1 @user2"
    )
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def prefix_ship(self, ctx: commands.Context, membre1: discord.Member, membre2: discord.Member = None):
        await self._send_ship(ctx.channel, ctx.author, membre1, membre2)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = ShipCommand(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Fun&Random"
    await bot.add_cog(cog)
