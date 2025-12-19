# ────────────────────────────────────────────────────────────────────────────────
# 📌 stats.py — Commande /stats et !stats
# Objectif : Afficher des statistiques condensées sur le bot
# Catégorie : Admin
# Accès : Admin uniquement
# Cooldown : 1 utilisation / 10 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
import psutil
import platform
import datetime
from utils.discord_utils import safe_send, safe_respond  # ✅ Sécurisé

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class Stats(commands.Cog):
    """Commande /stats et !!stats — Affiche les statistiques du bot"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.process = psutil.Process()
        self.launch_time = datetime.datetime.utcnow()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction interne pour générer l’embed
    # ────────────────────────────────────────────────────────────────────────────
    def build_embed(self) -> discord.Embed:
        uptime_delta = datetime.datetime.utcnow() - self.launch_time
        memory = self.process.memory_full_info().rss / 1024**2
        cpu = psutil.cpu_percent(interval=1)

        embed = discord.Embed(
            title="📊 Statistiques du Bot",
            description="Voici les informations système et bot condensées.",
            color=discord.Color.blurple(),
            timestamp=datetime.datetime.utcnow()
        )

        embed.add_field(
            name="⚙️ Système",
            value=f"OS: `{platform.system()} {platform.release()}`\n"
                  f"Python: `{platform.python_version()}`\n"
                  f"discord.py: `{discord.__version__}`",
            inline=False
        )

        embed.add_field(
            name="🤖 Bot",
            value=f"Nom: **{self.bot.user}**\n"
                  f"ID: `{self.bot.user.id}`\n"
                  f"Prefix: `!!` + Slash\n"
                  f"Serveurs: `{len(self.bot.guilds)}`\n"
                  f"Utilisateurs: `{len(self.bot.users)}`",
            inline=False
        )

        embed.add_field(
            name="📈 Performance",
            value=f"CPU: `{cpu}%`\n"
                  f"RAM: `{memory:.2f} MB`\n"
                  f"Uptime: `{str(uptime_delta).split('.')[0]}`",
            inline=False
        )

        embed.set_footer(text="Kisuke Urahara — Admin Only")
        return embed

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="stats",
        description="Affiche les statistiques du bot (admin uniquement)."
    )
    @app_commands.checks.cooldown(1, 10.0, key=lambda i: i.user.id)
    async def slash_stats(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            return await safe_respond(interaction, "❌ Accès refusé (admin uniquement).", ephemeral=True)

        embed = self.build_embed()
        await safe_respond(interaction, embed=embed)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="stats", help="Affiche les statistiques du bot (admin uniquement).")
    @commands.cooldown(1, 10.0, commands.BucketType.user)
    async def prefix_stats(self, ctx: commands.Context):
        if not ctx.author.guild_permissions.administrator:
            return await safe_send(ctx.channel, "❌ Accès refusé (admin uniquement).")

        embed = self.build_embed()
        await safe_send(ctx.channel, embed=embed)


# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Stats(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Admin"
    await bot.add_cog(cog)
