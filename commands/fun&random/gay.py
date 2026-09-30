# ================================================================================
# 📌 gay.py — Commande simple /gay et !gay
# Objectif : Calcule un taux de gaytitude fun qui change chaque jour
# Catégorie : 🌈 Fun&Random
# Accès : Tous
# Cooldown : 1 utilisation / 3 secondes / utilisateur
# ================================================================================

# ================================================================================
# 📦 Imports nécessaires
# ================================================================================
import discord
from discord import app_commands
from discord.ext import commands
import hashlib
import random
from datetime import datetime
from utils.discord_utils import safe_send, safe_respond

# ================================================================================
# 🧠 Fonction utilitaire pour calculer le score et générer l'embed
# ================================================================================
def calculer_gaytitude_embed(member: discord.Member) -> discord.Embed:
    # ✅ Hash basé sur user_id + date du jour
    date_jour = datetime.now().strftime("%Y-%m-%d")
    base_str  = f"{member.id}-{date_jour}"
    hash_val  = hashlib.md5(base_str.encode()).digest()

    # Score de base (0-100)
    base_score = int.from_bytes(hash_val, "big") % 101

    # ✅ Variation du jour : -20 à +20
    bonus_jour = (int.from_bytes(hash_val[:4], "big") % 41) - 20

    # Score final borné 0-100
    score = max(0, min(100, base_score + bonus_jour))

    # ✅ Message de variation selon le bonus
    if bonus_jour >= 10:
        variation_msg = f"📈 **Aujourd'hui, ton gaydar est en surchauffe ! (+{bonus_jour}%)**"
        variation_color = discord.Color.from_rgb(255, 100, 200)
    elif bonus_jour <= -10:
        variation_msg = f"📉 **Aujourd'hui, c'est pas ton jour... ({bonus_jour}%)**"
        variation_color = discord.Color.from_rgb(100, 150, 200)
    else:
        variation_msg = f"➡️ **Journée normale (variation : {bonus_jour:+d}%)**"
        variation_color = None

    # Barre de progression
    filled = "█" * (score // 10)
    empty  = "░" * (10 - (score // 10))
    bar    = f"`{filled}{empty}`"

    niveaux = [
        {"min": 90, "emoji": "🌈", "titre": "Légende arc-en-ciel", "couleur": discord.Color.magenta(), "descriptions": [
            "Ton aura pourrait repeindre une Pride entière.",
            "Tu transformes chaque salle en comédie musicale.",
            "Ta playlist est légalement un drapeau."
        ]},
        {"min": 70, "emoji": "💖", "titre": "Icône de style", "couleur": discord.Color.pink(), "descriptions": [
            "Tu portes plus de motifs que Zara.",
            "Tu brilles sans filtre.",
            "Ton regard déclenche des coming-outs."
        ]},
        {"min": 50, "emoji": "🌀", "titre": "Curieux·se affirmé·e", "couleur": discord.Color.blurple(), "descriptions": [
            "Tu es une énigme en glitter.",
            "Explorateur·rice de toutes les vibes.",
            "Ton cœur a plus de bissections qu'un shōnen."
        ]},
        {"min": 30, "emoji": "🤔", "titre": "Questionnement doux", "couleur": discord.Color.gold(), "descriptions": [
            "Tu dis 'non' mais ton historique dit 'peut-être'.",
            "Un mojito et tout peut basculer.",
            "T'as déjà dit 'je suis fluide, genre dans l'humour'."
        ]},
        {"min": 0, "emoji": "📏", "titre": "Straight mode activé", "couleur": discord.Color.dark_gray(), "descriptions": [
            "Tu joues à FIFA et ça te suffit.",
            "Ton placard contient 50 tee-shirts gris.",
            "Même ton Wi-Fi est en ligne droite."
        ]}
    ]

    niveau      = next(n for n in niveaux if score >= n["min"])
    commentaire = random.choice(niveau["descriptions"])

    # Couleur finale : celle du jour si variation forte, sinon celle du niveau
    couleur_finale = variation_color if variation_color else niveau["couleur"]

    embed = discord.Embed(
        title=f"{niveau['emoji']} {niveau['titre']}",
        description=commentaire,
        color=couleur_finale
    )
    embed.set_author(
        name=f"Taux de gaytitude de {member.display_name}",
        icon_url=member.display_avatar.url
    )
    embed.add_field(name="📊 Pourcentage", value=f"**{score}%**", inline=True)
    embed.add_field(name="📈 Niveau", value=bar, inline=False)
    embed.add_field(name="🌅 Aujourd'hui", value=variation_msg, inline=False)
    embed.set_footer(text=f"✨ Calculé pour le {date_jour}. Change chaque jour !")

    return embed

# ================================================================================
# 🧠 Cog principal
# ================================================================================
class GayCommand(commands.Cog):
    """Commande /gay et !gay — Calcule un taux de gaytitude qui change chaque jour."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ============================================================================
    # 🔹 Commande SLASH
    # ============================================================================
    @app_commands.command(name="gay", description="🌈 Calcule ton taux de gaytitude du jour.")
    @app_commands.checks.cooldown(1, 3.0, key=lambda i: i.user.id)
    @app_commands.describe(member="Utilisateur pour qui calculer la gaytitude (optionnel)")
    async def slash_gay(self, interaction: discord.Interaction, member: discord.Member = None):
        member = member or interaction.user
        embed  = calculer_gaytitude_embed(member)
        embed.timestamp = interaction.created_at
        await safe_respond(interaction, embed=embed)

    # ============================================================================
    # 🔹 Commande PREFIX
    # ============================================================================
    @commands.command(name="gay", help="🌈 Calcule ton taux de gaytitude du jour.")
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def prefix_gay(self, ctx: commands.Context, member: discord.Member = None):
        member = member or ctx.author
        embed  = calculer_gaytitude_embed(member)
        embed.timestamp = ctx.message.created_at
        await safe_send(ctx, embed=embed)

# ================================================================================
# 🔌 Setup du Cog
# ================================================================================
async def setup(bot: commands.Bot):
    cog = GayCommand(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Fun&Random"
    await bot.add_cog(cog)
