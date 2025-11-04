# ────────────────────────────────────────────────────────────────────────────────#
# 📌 reiatsudaily.py — Commande troll !reiatsudaily / !rd / !dailyreiatsu
# Objectif :
#   - Faire croire à une commande de récompense journalière
#   - En réalité, affiche une image troll 😏
# Catégorie : Fun
# Accès : Public
# ────────────────────────────────────────────────────────────────────────────────#

import discord
from discord.ext import commands
from utils.discord_utils import safe_send  # ✅ pour envoi sécurisé

# ────────────────────────────────────────────────────────────────────────────────#
# 🎭 Cog principal
# ────────────────────────────────────────────────────────────────────────────────#
class ReiatsuDaily(commands.Cog):
    """
    Commande troll !reiatsudaily — affiche une image surprise 😏
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(
        name="reiatsudaily",
        aliases=["rd", "dailyreiatsu"],
        help="Récompense journalière Reiatsu (ou pas 👀)",
        description="Affiche une image mystérieuse..."
    )
    async def reiatsudaily_cmd(self, ctx: commands.Context):
        """Commande troll qui affiche une image fun."""
        image_path = "data/images/not_a_rick_roll.jpg"

        embed = discord.Embed(
            title="🎁 Récompense journalière Reiatsu !",
            description="Tu croyais vraiment recevoir quelque chose ? 😏",
            color=discord.Color.purple()
        )
        file = discord.File(image_path, filename="reward.jpg")
        embed.set_image(url="attachment://reward.jpg")

        await safe_send(ctx.channel, embed=embed, file=file)

# ────────────────────────────────────────────────────────────────────────────────#
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────#
async def setup(bot: commands.Bot):
    cog = ReiatsuDaily(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Fun"
    await bot.add_cog(cog)
