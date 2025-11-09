# ────────────────────────────────────────────────────────────────────────────────
# 📌 quetes.py — Commande /quetes et !quetes
# Objectif : Afficher la liste des quêtes et leur état d’avancement
# Catégorie : 🎮 Progression
# Accès : Public
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
from utils.discord_utils import safe_send, safe_respond
from supabase_client import supabase  # ton fichier de connexion Supabase

# ────────────────────────────────────────────────────────────────────────────────
# 📜 Liste des quêtes disponibles
# ────────────────────────────────────────────────────────────────────────────────
ALL_QUESTS = {
    "couleur": "Faire une fois la commande couleur",
    "pizza": "Faire une fois la commande pizza",
    "division": "Faire le quizz de la commande division",
    "entrainement": "Faire un score de minimum 5000 à l'entraînement cérébral",
    "skill": "Utiliser ton skill"
}

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class QuetesCommand(commands.Cog):
    """Commande !quetes et /quetes — Affiche la liste des quêtes et leur statut."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="quetes",
        description="Affiche la liste de toutes les quêtes et ton niveau actuel."
    )
    async def slash_quetes(self, interaction: discord.Interaction):
        await self._show_quetes(interaction)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(
        name="quetes",
        help="🎮 Affiche la liste des quêtes et ton niveau actuel."
    )
    async def prefix_quetes(self, ctx: commands.Context):
        await self._show_quetes(ctx)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔧 Fonction commune d’affichage
    # ────────────────────────────────────────────────────────────────────────────
    async def _show_quetes(self, source):
        """Affiche la liste des quêtes terminées et non terminées pour un joueur."""
        try:
            user_id = (
                source.user.id if isinstance(source, discord.Interaction)
                else source.author.id
            )

            # Récupération des données joueur depuis Supabase
            data = supabase.table("reiatsu").select("niveau", "quetes").eq("user_id", user_id).execute()

            if not data.data:
                # Création automatique si pas trouvé
                supabase.table("reiatsu").insert({
                    "user_id": user_id,
                    "niveau": 1,
                    "quetes": []
                }).execute()
                niveau = 1
                quetes_faites = []
            else:
                joueur = data.data[0]
                niveau = joueur.get("niveau", 1)
                quetes_faites = joueur.get("quetes", [])

            # Génération du texte
            lines = []
            for key, desc in ALL_QUESTS.items():
                if key in quetes_faites:
                    lines.append(f"✅ {desc}")
                else:
                    lines.append(f"⁉️ {desc}")

            embed = discord.Embed(
                title=f"📜 Liste des quêtes de {source.user.name if isinstance(source, discord.Interaction) else source.author.name}",
                description=f"⭐ **Niveau actuel :** {niveau}\n\n" + "\n".join(lines),
                color=discord.Color.gold()
            )

            # Envoi sûr
            if isinstance(source, discord.Interaction):
                await safe_respond(source, embed=embed)
            else:
                await safe_send(source, embed=embed)

        except Exception as e:
            print(f"[ERREUR /quetes] {e}")
            if isinstance(source, discord.Interaction):
                await safe_respond(source, content="❌ Une erreur est survenue lors de la récupération des quêtes.", ephemeral=True)
            else:
                await safe_send(source, "❌ Une erreur est survenue lors de la récupération des quêtes.")

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = QuetesCommand(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Progression"
    await bot.add_cog(cog)
