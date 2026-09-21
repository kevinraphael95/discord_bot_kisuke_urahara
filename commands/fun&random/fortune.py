# ────────────────────────────────────────────────────────────────────────────────
# 📌 fortune.py
# Objectif : Ouvrir un biscuit chinois et révéler une prédiction (via API externe)
# Catégorie : Fun
# Accès : Tous
# Cooldown : 5s / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
import aiohttp

from utils.discord_utils import safe_send, safe_respond

# ────────────────────────────────────────────────────────────────────────────────
# 🌐 Appel API
# ────────────────────────────────────────────────────────────────────────────────
FORTUNE_API_URL = "https://fortunecookies-i3p5.onrender.com/fortune/"

# Fallback local si l'API est down (pas de dépendance externe critique)
FALLBACK_FORTUNES = [
    "A thrilling time is in your immediate future.",
    "You will find what you seek where you least expect it.",
    "The greatest risk is not taking one.",
    "Someone is thinking of you right now.",
    "Your hard work is about to pay off.",
]

async def fetch_fortune(session: aiohttp.ClientSession):
    """Appelle l'API et retourne (texte, lucky_numbers, from_fallback). Retombe sur un fallback local si l'API échoue."""
    try:
        async with session.get(FORTUNE_API_URL, timeout=aiohttp.ClientTimeout(total=8)) as resp:
            if resp.status == 200:
                data = await resp.json()
                cookie = data.get("cookie", {})
                text = cookie.get("fortune")
                lucky_numbers = cookie.get("luckyNumbers")
                if text:
                    return text, lucky_numbers, False
            print(f"[ERREUR API] Fortune cookie API a répondu {resp.status}")
    except Exception as e:
        print(f"[ERREUR API] Impossible de contacter {FORTUNE_API_URL} : {e}")

    import random
    return random.choice(FALLBACK_FORTUNES), None, True

def build_embed(fortune_text: str, lucky_numbers: list, from_fallback: bool = False):
    embed = discord.Embed(
        title="🥠 Fortune Cookie",
        description=f"*You crack open the cookie...*\n\n**{fortune_text}**",
        color=discord.Color.gold()
    )
    if lucky_numbers:
        embed.add_field(name="🍀 Lucky Numbers", value=", ".join(str(n) for n in lucky_numbers), inline=False)
    if from_fallback:
        embed.set_footer(text="⚠️ API indisponible — prédiction de secours")
    return embed

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class Fortune(commands.Cog):
    """
    Commande /fortune et !fortune — Ouvre un biscuit chinois porte-bonheur
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction interne commune
    # ────────────────────────────────────────────────────────────────────────────
    async def _send_fortune(self, channel: discord.abc.Messageable):
        async with channel.typing():
            fortune_text, lucky_numbers, from_fallback = await fetch_fortune(self.bot.aiohttp_session)
        embed = build_embed(fortune_text, lucky_numbers, from_fallback)
        await safe_send(channel, embed=embed)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(name="fortune", description="Ouvre un biscuit chinois et découvre ta prédiction.")
    @app_commands.checks.cooldown(rate=1, per=5.0, key=lambda i: i.user.id)
    async def slash_fortune(self, interaction: discord.Interaction):
        await interaction.response.defer()
        fortune_text, lucky_numbers, from_fallback = await fetch_fortune(self.bot.aiohttp_session)
        embed = build_embed(fortune_text, lucky_numbers, from_fallback)
        await safe_respond(interaction, embed=embed)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="fortune")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_fortune(self, ctx: commands.Context):
        await self._send_fortune(ctx.channel)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Fortune(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Fun&Random"
    await bot.add_cog(cog)
