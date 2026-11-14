# ================================================================================
# 📌 quetes.py — Commande /quetes et !quetes
# Objectif : Afficher la liste des quêtes et leur état d’avancement
# Catégorie : Reiatsu
# Accès : Public
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ================================================================================

# ================================================================================
# 📦 Modules standards
# ================================================================================
import json

# ================================================================================
# 📦  Modules tiers
# ================================================================================
import discord
from discord import app_commands
from discord.ext import commands

# ================================================================================
# 📦 Modules internes
# ================================================================================
from utils.discord_anti429 import safe_send, safe_interact
from utils.reiatsu_utils import ensure_profile

# ================================================================================
# ⚙️ Paramètres globaux
# ================================================================================
COOLDOWN_SECONDS = 5

# ================================================================================
# 📜 Liste des quêtes disponibles
# ================================================================================
ALL_QUESTS = {
    "couleur": "Faire une fois la commande couleur",
    "pizza": "Faire une fois la commande pizza",
    "division": "Faire le quizz de la commande division",
    "entrainement": "Faire un score de minimum 5000 à l'entraînement cérébral",
    "skill": "Utiliser ton skill",
    "bmoji": "Réussi le minijeu de la commande bmoji"
}

# ================================================================================
# 🛠️ Helper : lecture sûre de la liste des quêtes faites
# ================================================================================
def _parse_quetes(raw) -> list:
    """La colonne `quetes` est un TEXT JSON ('[]') en base : accepte liste ou chaîne."""
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        try:
            data = json.loads(raw)
            return data if isinstance(data, list) else []
        except json.JSONDecodeError:
            return []
    return []

# ================================================================================
# 🧠 Cog principal
# ================================================================================
class QuetesCommand(commands.Cog):
    """
    Commande /quetes et !quetes — Affiche la liste des quêtes et leur statut
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ============================================================================
    # 🔹 Commande SLASH
    # ============================================================================
    @app_commands.command(
        name="quetes",
        description="Affiche la liste de toutes les quêtes et ton niveau actuel."
    )
    @app_commands.checks.cooldown(1, COOLDOWN_SECONDS, key=lambda i: i.user.id)
    async def slash_quetes(self, interaction: discord.Interaction):
        await self._show_quetes(interaction)

    # ============================================================================
    # 🔹 Commande PREFIX
    # ============================================================================
    @commands.command(
        name="quetes",
        help="🎮 Affiche la liste des quêtes et ton niveau actuel."
    )
    @commands.cooldown(1, COOLDOWN_SECONDS, commands.BucketType.user)
    async def prefix_quetes(self, ctx: commands.Context):
        await self._show_quetes(ctx)

    # ============================================================================
    # 🔧 Fonction commune d’affichage
    # ============================================================================
    async def _show_quetes(self, source):
        """Affiche la liste des quêtes terminées et non terminées pour un joueur."""
        is_slash = isinstance(source, discord.Interaction)
        try:
            user = source.user if is_slash else source.author

            # ⚡ Récupération ou création du profil
            profile = ensure_profile(user.id, user.name)
            niveau = profile.get("niveau") or 1
            quetes_faites = _parse_quetes(profile.get("quetes"))

            # Génération du texte des quêtes
            lines = []
            for key, desc in ALL_QUESTS.items():
                icon = "✅" if key in quetes_faites else "⁉️"
                lines.append(f"{icon} {desc}")

            done = sum(1 for key in ALL_QUESTS if key in quetes_faites)

            embed = discord.Embed(
                title=f"📜 Liste des quêtes de {user.display_name}",
                description=(
                    f"⭐ **Niveau actuel :** {niveau}\n"
                    f"🏁 **Progression :** {done}/{len(ALL_QUESTS)}\n\n"
                    + "\n".join(lines)
                ),
                color=discord.Color.gold()
            )

            # Envoi sûr
            if is_slash:
                await safe_interact(source, embed=embed)
            else:
                await safe_send(source, embed=embed)

        except Exception as e:
            print(f"[ERREUR /quetes] {e}")
            msg = "❌ Une erreur est survenue lors de la récupération des quêtes."
            if is_slash:
                await safe_interact(source, content=msg, ephemeral=True)
            else:
                await safe_send(source, msg)

    # ============================================================================
    # 🚦 Gestion du cooldown (préfixe)
    # ============================================================================
    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.CommandOnCooldown):
            await safe_send(ctx, f"⏳ Attends encore **{error.retry_after:.1f}s** avant de réutiliser cette commande.")
        else:
            print(f"[ERREUR !quetes] {error}")

    # ============================================================================
    # 🚦 Gestion du cooldown (slash)
    # ============================================================================
    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            await safe_interact(
                interaction,
                content=f"⏳ Attends encore **{error.retry_after:.1f}s** avant de réutiliser cette commande.",
                ephemeral=True
            )
        else:
            print(f"[ERREUR /quetes] {error}")

# ================================================================================
# 🔌 Setup du Cog
# ================================================================================
async def setup(bot: commands.Bot):
    cog = QuetesCommand(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Reiatsu"
    await bot.add_cog(cog)
