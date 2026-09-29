# ================================================================================
# 📌 inspire.py
# Objectif : Génère une "citation inspirante" absurde via InspiroBot
# Catégorie : Fun&Random
# Accès : Tous
# Cooldown : 5s / utilisateur
# ================================================================================

# ================================================================================
# 📦 Imports nécessaires
# ================================================================================
import logging

import discord
from discord import app_commands
from discord.ext import commands
import aiohttp

from utils.discord_utils import safe_send, safe_followup

log = logging.getLogger(__name__)

# ================================================================================
# 🌐 Appel API
# ================================================================================
INSPIROBOT_API_URL = "https://inspirobot.me/api?generate=true"

async def fetch_inspiro_image(session: aiohttp.ClientSession):
    try:
        async with session.get(INSPIROBOT_API_URL, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status == 200:
                url = (await resp.text()).strip()
                if url.startswith("http"):
                    return url, True
            log.warning("[inspire] InspiroBot a répondu %s", resp.status)
    except Exception as e:
        log.exception("[inspire] Impossible de contacter %s : %s", INSPIROBOT_API_URL, e)

    return None, False

def build_embed(image_url: str):
    embed = discord.Embed(
        title="✨ Citation inspirante",
        color=discord.Color.purple()
    )
    embed.set_image(url=image_url)
    embed.set_footer(text="inspirobot.me")
    return embed

# ================================================================================
# 🧠 Cog principal
# ================================================================================
class Inspire(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _send_inspire(self, channel: discord.abc.Messageable):
        async with channel.typing():
            image_url, ok = await fetch_inspiro_image(self.bot.aiohttp_session)
        if not ok:
            await safe_send(channel, "❌ L'univers n'a pas de sagesse à offrir pour l'instant. Réessaie plus tard.")
            return
        await safe_send(channel, embed=build_embed(image_url))

    @app_commands.command(name="inspire", description="Reçois une citation inspirante... très inspirante.")
    @app_commands.checks.cooldown(rate=1, per=5.0, key=lambda i: i.user.id)
    async def slash_inspire(self, interaction: discord.Interaction):
        await interaction.response.defer()
        image_url, ok = await fetch_inspiro_image(self.bot.aiohttp_session)
        if not ok:
            await safe_followup(interaction, "❌ L'univers n'a pas de sagesse à offrir pour l'instant. Réessaie plus tard.")
            return
        await safe_followup(interaction, embed=build_embed(image_url))

    @commands.command(name="inspire", help="Reçois une citation inspirante... très inspirante.")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_inspire(self, ctx: commands.Context):
        await self._send_inspire(ctx.channel)

# ================================================================================
# 🔌 Setup du Cog
# ================================================================================
async def setup(bot: commands.Bot):
    cog = Inspire(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Fun&Random"
    await bot.add_cog(cog)
