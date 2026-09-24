# ================================================================================
# 📌 ping.py
# Objectif : Vérifie la latence du bot (WebSocket + API réelle) avec embed détaillé
# Catégorie : 🧱 Général
# Accès : Public
# Cooldown : 5s
# ================================================================================

# ================================================================================
# 📦 Imports nécessaires
# ================================================================================
import time
import platform
import discord
from discord import app_commands
from discord.ext import commands

from utils.discord_utils import safe_send

# ================================================================================
# 🧠 Cog principal
# ================================================================================
class Ping(commands.Cog):
    """Commande /ping et !ping — Vérifie la latence du bot (WS + API) avec infos système."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Timestamp de démarrage du bot (fallback si non défini ailleurs)
        if not hasattr(bot, "launch_time"):
            bot.launch_time = time.time()

    # ============================================================================
    # 🔹 Helpers
    # ============================================================================
    @staticmethod
    def _format_uptime(seconds: float) -> str:
        """Formate un nombre de secondes en 'Xj Xh Xm Xs'."""
        seconds = int(seconds)
        jours, reste = divmod(seconds, 86400)
        heures, reste = divmod(reste, 3600)
        minutes, secondes = divmod(reste, 60)
        parts = []
        if jours:
            parts.append(f"{jours}j")
        if heures:
            parts.append(f"{heures}h")
        if minutes:
            parts.append(f"{minutes}m")
        parts.append(f"{secondes}s")
        return " ".join(parts)

    @staticmethod
    def _latence_color_emoji(ms: float):
        """Retourne (couleur embed, emoji) selon la qualité de la latence."""
        if ms < 150:
            return discord.Color.green(), "🟢"
        elif ms < 300:
            return discord.Color.orange(), "🟠"
        else:
            return discord.Color.red(), "🔴"

    def _build_embed(self, ws_latence: float, api_latence: float) -> discord.Embed:
        """Construit l'embed complet avec toutes les infos de latence/système."""
        color, emoji = self._latence_color_emoji(max(ws_latence, api_latence))

        uptime = self._format_uptime(time.time() - self.bot.launch_time)
        shard_info = (
            f"{self.bot.shard_id if self.bot.shard_id is not None else 0}/{self.bot.shard_count}"
            if getattr(self.bot, "shard_count", None)
            else "Non shardé"
        )

        embed = discord.Embed(
            title=f"{emoji} Pong !",
            color=color,
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="📡 Latence WebSocket", value=f"`{ws_latence} ms`", inline=True)
        embed.add_field(name="🔁 Latence API (round-trip)", value=f"`{api_latence} ms`", inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=True)  # espace pour aligner sur 3 colonnes

        embed.add_field(name="⏱️ Uptime", value=uptime, inline=True)
        embed.add_field(name="🌐 Serveurs", value=str(len(self.bot.guilds)), inline=True)
        embed.add_field(name="👥 Utilisateurs", value=str(len(self.bot.users)), inline=True)

        embed.add_field(name="🧩 Shard", value=shard_info, inline=True)
        embed.add_field(name="🐍 discord.py", value=discord.__version__, inline=True)
        embed.add_field(name="🖥️ Python", value=platform.python_version(), inline=True)

        embed.set_footer(text=f"Demandé sur {platform.system()}")
        return embed

    # ============================================================================
    # 🔹 Commande SLASH
    # ============================================================================
    @app_commands.command(
        name="ping",
        description="Affiche la latence détaillée du bot (WebSocket + API)."
    )
    @app_commands.checks.cooldown(rate=1, per=5.0, key=lambda i: i.user.id)
    async def slash_ping(self, interaction: discord.Interaction):
        try:
            ws_latence = round(self.bot.latency * 1000)

            start = time.perf_counter()
            await interaction.response.defer()
            api_latence = round((time.perf_counter() - start) * 1000)

            embed = self._build_embed(ws_latence, api_latence)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            print("[ERREUR ping]", e)
            await interaction.followup.send("❌ Une erreur est survenue lors de l'exécution de la commande.")

    # ============================================================================
    # 🔹 Commande PREFIX
    # ============================================================================
    @commands.command(name="ping", aliases=["pong", "latence"], help="Affiche la latence détaillée du bot.")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_ping(self, ctx: commands.Context):
        try:
            ws_latence = round(self.bot.latency * 1000)

            start = time.perf_counter()
            message = await safe_send(ctx.channel, "🏓 Calcul en cours...")
            api_latence = round((time.perf_counter() - start) * 1000)

            embed = self._build_embed(ws_latence, api_latence)
            await message.edit(content=None, embed=embed)
        except Exception as e:
            print("[ERREUR ping]", e)
            await safe_send(ctx.channel, "❌ Une erreur est survenue lors de l'exécution de la commande.")

# ================================================================================
# 🔌 Setup du Cog
# ================================================================================
async def setup(bot: commands.Bot):
    cog = Ping(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Général"
    await bot.add_cog(cog)
