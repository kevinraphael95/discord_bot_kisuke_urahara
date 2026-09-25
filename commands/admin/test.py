# ================================================================================
# 📌 test.py
# Objectif : Affiche le ping, l'heure actuelle et la date du dernier commit
# Catégorie : Général
# Accès : Admin uniquement
# Cooldown : 3 secondes
# ================================================================================

# ================================================================================
# 📦 Imports nécessaires
# ================================================================================
import discord
import subprocess
from datetime import datetime
from discord import app_commands
from discord.ext import commands

from utils.discord_utils import safe_send, safe_respond  

# ================================================================================
# 🧠 Fonction utilitaire — récupère la date du dernier commit git
# ================================================================================
def get_last_commit_date() -> str:
    try:
        result = subprocess.check_output(
            ["git", "log", "-1", "--format=%cd", "--date=format:%d/%m/%Y %H:%M"],
            stderr=subprocess.DEVNULL
        )
        return result.decode("utf-8").strip()
    except Exception:
        return "Inconnue"

# ================================================================================
# 🧠 Cog principal
# ================================================================================
class Test(commands.Cog):
    """
    Commande /test et !test — Affiche ping, heure et dernier commit (admin uniquement)
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def build_message(self) -> str:
        ping_ms = round(self.bot.latency * 1000)
        now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        last_commit = get_last_commit_date()
        return (
            f"🏓 **Ping** : {ping_ms} ms\n"
            f"🕒 **Heure actuelle** : {now}\n"
            f"📦 **Dernier commit** : {last_commit}"
        )

    # ============================================================================
    # 🔹 Commande SLASH
    # ============================================================================
    @app_commands.command(
        name="test",
        description="(Admin) Affiche le ping, l'heure et le dernier commit du bot."
    )
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.checks.cooldown(rate=1, per=3.0, key=lambda i: i.user.id)
    async def slash_test(self, interaction: discord.Interaction):
        await safe_respond(interaction, self.build_message())

    # ============================================================================
    # 🔹 Commande PREFIX
    # ============================================================================
    @commands.command(name="test", help="(Admin) Affiche le ping, l'heure et le dernier commit du bot.")
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 3.0, commands.BucketType.user)
    async def prefix_test(self, ctx: commands.Context):
        await safe_send(ctx.channel, self.build_message())

# ================================================================================
# 🔌 Setup du Cog
# ================================================================================
async def setup(bot: commands.Bot):
    cog = Test(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Général"
    await bot.add_cog(cog)
