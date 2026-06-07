# ────────────────────────────────────────────────────────────────────────────────
# 🎲 dice.py — Commande /dice et !dice
# Objectif : Lance des dés personnalisés au format NdX (ex: 2d6, 1d20, 4d100)
# Catégorie : Fun&Random
# Accès : Tous
# Cooldown : 1 utilisation / 2 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
import random
import re
from discord import app_commands
from discord.ext import commands
from utils.discord_utils import safe_send, safe_respond

# ────────────────────────────────────────────────────────────────────────────────
# ⚙️ Constantes
# ────────────────────────────────────────────────────────────────────────────────
MAX_DES   = 20
MAX_FACES = 1000

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Fonction utilitaire : parse la formule et génère l'embed
# ────────────────────────────────────────────────────────────────────────────────
def lancer_des(formule: str, author: discord.Member | discord.User) -> tuple[discord.Embed | None, str | None]:
    """
    Parse une formule NdX et retourne un embed de résultat.
    Retourne (embed, None) si OK, (None, message_erreur) si invalide.
    """
    match = re.fullmatch(r'(\d+)[dD](\d+)', formule.strip())
    if not match:
        return None, "❌ Format invalide. Utilise `NdX` — ex: `2d6`, `1d20`, `4d100`."

    n, x = int(match.group(1)), int(match.group(2))

    if not (1 <= n <= MAX_DES):   return None, f"❌ Entre **1** et **{MAX_DES}** dés maximum."
    if not (2 <= x <= MAX_FACES): return None, f"❌ Entre **2** et **{MAX_FACES}** faces par dé."

    resultats = [random.randint(1, x) for _ in range(n)]
    total     = sum(resultats)

    if total == n * x: emoji, color = "🎯", discord.Color.gold()
    elif total == n:   emoji, color = "💀", discord.Color.dark_red()
    else:              emoji, color = "🎲", discord.Color.blurple()

    def fmt(r):
        if r == x: return f"**{r}**"
        if r == 1: return f"~~{r}~~"
        return str(r)

    detail = " + ".join(fmt(r) for r in resultats)

    embed = discord.Embed(
        description=f"{detail}\n# = {total}",
        color=color
    )
    embed.set_author(
        name=f"{emoji} {author.display_name} a lancé {formule.upper()}",
        icon_url=author.display_avatar.url
    )

    if total == n * x: embed.set_footer(text="🎯 Score parfait !")
    elif total == n:   embed.set_footer(text="💀 Score catastrophique.")

    return embed, None


# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class DiceCommand(commands.Cog):
    """Commande /dice et !dice — Lance des dés au format NdX."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(name="dice", description="🎲 Lance des dés. Ex: 2d6, 1d20, 4d100")
    @app_commands.checks.cooldown(1, 2.0, key=lambda i: i.user.id)
    @app_commands.describe(formule="Format NdX — ex: 2d6, 1d20, 4d100")
    async def slash_dice(self, interaction: discord.Interaction, formule: str):
        embed, erreur = lancer_des(formule, interaction.user)
        if erreur:
            await safe_respond(interaction, erreur, ephemeral=True)
            return
        embed.timestamp = interaction.created_at
        await safe_respond(interaction, embed=embed)

    @slash_dice.error
    async def slash_dice_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            await safe_respond(interaction, f"⏳ Attends encore {error.retry_after:.1f}s.", ephemeral=True)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="dice", help="🎲 Lance des dés. Ex: !dice 2d6, !dice 1d20")
    @commands.cooldown(1, 2, commands.BucketType.user)
    async def prefix_dice(self, ctx: commands.Context, formule: str = None):
        if not formule:
            await safe_send(ctx, "❌ Précise une formule. Ex: `!dice 2d6`, `!dice 1d20`")
            return
        embed, erreur = lancer_des(formule, ctx.author)
        if erreur:
            await safe_send(ctx, erreur)
            return
        embed.timestamp = ctx.message.created_at
        await safe_send(ctx, embed=embed)

    @prefix_dice.error
    async def prefix_dice_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.CommandOnCooldown):
            await safe_send(ctx, f"⏳ Attends encore {error.retry_after:.1f}s.")


# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = DiceCommand(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Fun&Random"
    await bot.add_cog(cog)
