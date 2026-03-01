# ────────────────────────────────────────────────────────────────────────────────
# 📌 usership.py — Commande interactive /ship et !ship (entre membres du serveur)
# Objectif : Shipper deux membres du serveur avec un score TOUJOURS identique
#            basé sur leurs IDs Discord (déterministe, reproductible)
# Catégorie : Fun&Random
# Accès : Public
# Cooldown : 1 utilisation / 3 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, button
import hashlib
from utils.discord_utils import safe_send, safe_edit, safe_interact

# ────────────────────────────────────────────────────────────────────────────────
# 🧮 Score déterministe basé sur les IDs Discord
# ────────────────────────────────────────────────────────────────────────────────
def calculer_score_users(id1: int, id2: int) -> int:
    """
    Génère un score TOUJOURS identique pour deux utilisateurs donnés.
    L'ordre des IDs n'a pas d'importance (id1+id2 == id2+id1).
    Utilise SHA-256 pour une distribution uniforme et reproductible.
    """
    # On trie les IDs pour que le résultat soit symétrique (A ship B == B ship A)
    sorted_ids = sorted([id1, id2])
    seed = f"ship:{sorted_ids[0]}:{sorted_ids[1]}"
    hash_bytes = hashlib.sha256(seed.encode()).digest()
    # On convertit les 4 premiers octets en entier et on prend modulo 101 → [0, 100]
    raw = int.from_bytes(hash_bytes[:4], "big")
    return raw % 101

def get_verdict(score: int) -> tuple[str, discord.Color]:
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
    """Barre de progression visuelle pour le score."""
    filled = round(score / 10)
    empty = 10 - filled
    return "❤️" * filled + "🖤" * empty

def generate_user_ship_embed(u1: discord.Member | discord.User, u2: discord.Member | discord.User) -> discord.Embed:
    score = calculer_score_users(u1.id, u2.id)
    verdict, color = get_verdict(score)
    bar = build_bar(score)

    embed = discord.Embed(title="💘 Ship Meter 💘", color=color)
    embed.add_field(
        name="💑 Le couple du jour",
        value=f"**{u1.display_name}** ❤️ **{u2.display_name}**",
        inline=False
    )
    embed.add_field(name="🔢 Compatibilité", value=f"`{score}%`", inline=True)
    embed.add_field(name="📊 Score", value=bar, inline=True)
    embed.add_field(name="💬 Verdict", value=f"*{verdict}*", inline=False)
    embed.set_thumbnail(url=u1.display_avatar.url)
    embed.set_image(url=u2.display_avatar.url)
    embed.set_footer(text="⚠️ Ce score est définitif et immuable — l'univers a parlé.")
    return embed

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ Vue interactive
# ────────────────────────────────────────────────────────────────────────────────
class UserShipView(View):
    def __init__(self, u1, u2, author):
        super().__init__(timeout=60)
        self.u1 = u1
        self.u2 = u2
        self.author = author
        self.message: discord.Message | None = None

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message:
            try:
                await safe_edit(self.message, view=self)
            except:
                pass

    @button(label="🔁 Afficher à nouveau", style=discord.ButtonStyle.blurple)
    async def reafficher(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = generate_user_ship_embed(self.u1, self.u2)
        await safe_interact(interaction, edit=True, embed=embed, view=self)

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class UserShipCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _send_ship(
        self,
        channel: discord.abc.Messageable,
        author: discord.Member | discord.User,
        u1: discord.Member | discord.User,
        u2: discord.Member | discord.User | None = None,
    ):
        # Si u2 non fourni, on ship l'auteur avec u1
        if u2 is None:
            u2 = u1
            u1 = author

        # On évite de se ship soi-même
        if u1.id == u2.id:
            return await safe_send(channel, "❌ On ne peut pas se shipper avec soi-même... ou si ? 🤔")

        embed = generate_user_ship_embed(u1, u2)
        view = UserShipView(u1, u2, author)
        view.message = await safe_send(channel, embed=embed, view=view)

    # ─── Commande SLASH ────────────────────────────────────────────────────────
    @app_commands.command(name="ship", description="💘 Calcule la compatibilité entre deux membres du serveur.")
    @app_commands.describe(
        membre1="Premier membre (toi par défaut)",
        membre2="Second membre (requis si tu veux shipper deux autres personnes)"
    )
    @app_commands.checks.cooldown(1, 3.0, key=lambda i: i.user.id)
    async def slash_ship(
        self,
        interaction: discord.Interaction,
        membre1: discord.Member,
        membre2: discord.Member = None
    ):
        await self._send_ship(interaction.channel, interaction.user, membre1, membre2)

    # ─── Commande PREFIX ───────────────────────────────────────────────────────
    @commands.command(
        name="ship",
        help=(
            "💘 Ship deux membres du serveur.\n"
            "Usage :\n"
            "  !ship @user         → te ship avec @user\n"
            "  !ship @user1 @user2 → ship @user1 avec @user2\n"
            "\nLe résultat est TOUJOURS le même pour les mêmes personnes !"
        )
    )
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def prefix_ship(
        self,
        ctx: commands.Context,
        membre1: discord.Member,
        membre2: discord.Member = None
    ):
        await self._send_ship(ctx.channel, ctx.author, membre1, membre2)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = UserShipCommand(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Fun&Random"
    await bot.add_cog(cog)
