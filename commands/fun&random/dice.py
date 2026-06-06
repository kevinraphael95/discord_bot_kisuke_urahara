# ────────────────────────────────────────────────────────────────────────────────
# 🎲 dice.py — Commande /dice et !dice
# Objectif : Lance des dés personnalisés au format NdX (ex: 2d6, 1d20, 4d100)
# Catégorie : 🕹️ Jeux
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
MAX_DES   = 20    # Nombre maximum de dés en une fois
MAX_FACES = 1000  # Nombre maximum de faces par dé

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

    if n < 1 or n > MAX_DES:
        return None, f"❌ Entre **1** et **{MAX_DES}** dés maximum."
    if x < 2 or x > MAX_FACES:
        return None, f"❌ Entre **2** et **{MAX_FACES}** faces par dé."

    resultats = [random.randint(1, x) for _ in range(n)]
    total     = sum(resultats)
    
    # Emoji selon le résultat global
    if n == 1:
        if resultats[0] == x:   emoji = "🎯"   # score max
        elif resultats[0] == 1: emoji = "💀"   # score min
        else:                   emoji = "🎲"
    else:
        ratio = total / (n * x)
        if ratio >= 0.9:   emoji = "🎯"
        elif ratio <= 0.1: emoji = "💀"
        else:              emoji = "🎲"

    # Affichage des dés individuels (limité pour ne pas surcharger)
    if n == 1:
        detail = f"**{resultats[0]}**"
    elif n <= 10:
        detail = " + ".join(f"`{r}`" for r in resultats) + f" = **{total}**"
    else:
        top3 = ", ".join(f"`{r}`" for r in resultats[:3])
        detail = f"{top3} … *(+{n-3} autres)* = **{total}**"

    embed = discord.Embed(
        title=f"{emoji} Lancer de dés — {formule.upper()}",
        color=discord.Color.gold() if total == n * x else
              discord.Color.dark_red() if total == n else
              discord.Color.blurple()
    )
    embed.set_author(
        name=f"Lancer de {author.display_name}",
        icon_url=author.display_avatar.url
    )
    embed.add_field(name="🎲 Résultat",   value=detail,          inline=False)
    embed.add_field(name="📊 Total",      value=f"**{total}**",  inline=True)
    embed.add_field(name="📈 Maximum",    value=f"`{n * x}`",    inline=True)
    embed.add_field(name="📉 Minimum",    value=f"`{n}`",        inline=True)

    if n == 1 and resultats[0] == x:
        embed.set_footer(text="🎯 Score parfait !")
    elif n == 1 and resultats[0] == 1:
        embed.set_footer(text="💀 Score catastrophique.")
    else:
        embed.set_footer(text=f"{n} dé{'s' if n > 1 else ''} à {x} face{'s' if x > 1 else ''}")

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
        try:
            embed, erreur = lancer_des(formule, interaction.user)
            if erreur:
                await safe_respond(interaction, erreur, ephemeral=True)
                return
            embed.timestamp = interaction.created_at
            await safe_respond(interaction, embed=embed)
        except app_commands.CommandOnCooldown as e:
            await safe_respond(interaction, f"⏳ Attends encore {e.retry_after:.1f}s.", ephemeral=True)
        except Exception as e:
            print(f"[ERREUR /dice] {e}")
            await safe_respond(interaction, "❌ Une erreur est survenue.", ephemeral=True)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="dice", help="🎲 Lance des dés. Ex: !dice 2d6, !dice 1d20")
    @commands.cooldown(1, 2, commands.BucketType.user)
    async def prefix_dice(self, ctx: commands.Context, formule: str = None):
        try:
            if not formule:
                await safe_send(ctx, "❌ Précise une formule. Ex: `!dice 2d6`, `!dice 1d20`")
                return
            embed, erreur = lancer_des(formule, ctx.author)
            if erreur:
                await safe_send(ctx, erreur)
                return
            embed.timestamp = ctx.message.created_at
            await safe_send(ctx, embed=embed)
        except commands.CommandOnCooldown as e:
            await safe_send(ctx, f"⏳ Attends encore {e.retry_after:.1f}s.")
        except Exception as e:
            print(f"[ERREUR !dice] {e}")
            await safe_send(ctx, "❌ Une erreur est survenue.")


# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = DiceCommand(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Fun&Random"
    await bot.add_cog(cog)
