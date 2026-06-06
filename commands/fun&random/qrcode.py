# ────────────────────────────────────────────────────────────────────────────────
# 📌 qrcode.py — Commande simple /qrcode et !qrcode
# Objectif : Génère un QR code depuis un texte ou une URL et l'envoie en image
# Catégorie : Fun&Random
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
import qrcode
import io
from utils.discord_utils import safe_send, safe_respond

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Fonction utilitaire pour générer le QR code et l'embed
# ────────────────────────────────────────────────────────────────────────────────
def generer_qrcode_embed(texte: str, author: discord.User | discord.Member) -> tuple[discord.Embed, discord.File]:
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(texte)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    file = discord.File(buffer, filename="qrcode.png")

    est_url = texte.startswith("http://") or texte.startswith("https://")
    apercu = texte if len(texte) <= 60 else texte[:57] + "..."

    embed = discord.Embed(
        title="📷 QR Code généré",
        description=f"{'🔗 URL' if est_url else '📝 Texte'} : `{apercu}`",
        color=discord.Color.dark_teal()
    )
    embed.set_author(name=f"Demandé par {author.display_name}", icon_url=author.display_avatar.url)
    embed.set_image(url="attachment://qrcode.png")
    embed.set_footer(text="📲 Scanne-moi avec ton téléphone !")

    return embed, file

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class QRCodeCommand(commands.Cog):
    """Commande /qrcode et !qrcode — Génère un QR code depuis un texte ou une URL."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(name="qrcode", description="📷 Génère un QR code depuis un texte ou une URL.")
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)  # Cooldown 5s par utilisateur
    @app_commands.describe(texte="Le texte ou l'URL à encoder dans le QR code")
    async def slash_qrcode(self, interaction: discord.Interaction, texte: str):
        try:
            if len(texte) > 1000:
                await safe_respond(interaction, "❌ Le texte est trop long (max 1000 caractères).", ephemeral=True)
                return
            await interaction.response.defer()
            embed, file = generer_qrcode_embed(texte, interaction.user)
            embed.timestamp = interaction.created_at
            await interaction.followup.send(embed=embed, file=file)
        except app_commands.CommandOnCooldown as e:
            await safe_respond(interaction, f"⏳ Attends encore {e.retry_after:.1f}s.", ephemeral=True)
        except Exception as e:
            print(f"[ERREUR /qrcode] {e}")
            await safe_respond(interaction, "❌ Une erreur est survenue.", ephemeral=True)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="qrcode", help="📷 Génère un QR code depuis un texte ou une URL.")
    @commands.cooldown(1, 5, commands.BucketType.user)  # Cooldown 5s par utilisateur
    async def prefix_qrcode(self, ctx: commands.Context, *, texte: str = None):
        try:
            if not texte:
                await safe_send(ctx, "❌ Fournis un texte ou une URL. Ex : `!qrcode https://example.com`")
                return
            if len(texte) > 1000:
                await safe_send(ctx, "❌ Le texte est trop long (max 1000 caractères).")
                return
            embed, file = generer_qrcode_embed(texte, ctx.author)
            embed.timestamp = ctx.message.created_at
            await safe_send(ctx, embed=embed, file=file)
        except commands.CommandOnCooldown as e:
            await safe_send(ctx, f"⏳ Attends encore {e.retry_after:.1f}s.")
        except Exception as e:
            print(f"[ERREUR !qrcode] {e}")
            await safe_send(ctx, "❌ Une erreur est survenue.")

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = QRCodeCommand(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Fun&Random"
    await bot.add_cog(cog)
