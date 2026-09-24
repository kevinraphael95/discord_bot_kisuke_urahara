# ================================================================================
# 📌 reiatsuprofil.py — Commande interactive /reiatsuprofil et !reiatsuprofil
# Objectif : Affiche le profil Reiatsu d’un joueur (classe, compétences, cooldowns)
# Catégorie : Reiatsu
# Accès : Tous
# Cooldown : 5 secondes
# ================================================================================

# ================================================================================
# 📦 Imports nécessaires
# ================================================================================
import discord
from discord import app_commands
from discord.ext import commands
from dateutil import parser
from datetime import datetime, timedelta, timezone
import os
import json
import sqlite3

from utils.discord_utils import safe_send, safe_respond
from utils.reiatsu_utils import ensure_profile  # ✅ Ajout pour auto-création profil

# ================================================================================
# 📂 Chargement des classes depuis JSON
# ================================================================================
CONFIG_JSON_PATH = os.path.join("data", "reiatsu_config.json")
DB_PATH = "database/reiatsu.db"

def get_conn():
    return sqlite3.connect(DB_PATH)

def load_classes():
    try:
        with open(CONFIG_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("CLASSES", {})
    except Exception as e:
        print(f"[ERREUR JSON] Impossible de charger {CONFIG_JSON_PATH} : {e}")
        return {}

# ================================================================================
# 🧠 Cog principal
# ================================================================================
class ReiatsuProfil(commands.Cog):
    """Commande /reiatsuprofil et !reiatsuprofil — Affiche le profil personnel Reiatsu d’un joueur"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ============================================================================
    # 🔹 Fonction interne commune
    # ============================================================================
    async def _send_profil(self, channel_or_interaction, author, target_user):
        user = target_user or author
        user_id = int(user.id)

        # ✅ Création automatique du profil si inexistant
        ensure_profile(user_id, user.name)

        # Récupération des données Reiatsu depuis SQLite
        try:
            with get_conn() as conn:
                cur = conn.cursor()
                cur.execute("""
                    SELECT username, points, bonus5, classe, last_steal_attempt,
                           steal_cd, last_skilled_at, active_skill, niveau
                    FROM reiatsu WHERE user_id = ?
                """, (user_id,))
                row = cur.fetchone()
        except Exception as e:
            print(f"[ERREUR DB] Lecture Reiatsu échouée : {e}")
            return await safe_send(channel_or_interaction, "❌ Impossible de récupérer ton profil.")

        if not row:
            return await safe_send(channel_or_interaction, "⚠️ Impossible de créer ton profil Reiatsu.")

        username, points, bonus, classe_nom, last_steal, steal_cd, last_skill, active_skill, niveau = row
        points = points or 0
        bonus = bonus or 0
        niveau = niveau or 0

        # Gestion des classes
        CLASSES = load_classes()
        classe_data = None
        classe_symbole = ""
        if classe_nom:
            classe_nom_clean = classe_nom.strip().lower()
            for key, value in CLASSES.items():
                if key.strip().lower() == classe_nom_clean:
                    classe_data = value
                    classe_nom = key
                    classe_symbole = value.get("Symbole", "")
                    break

        # Cooldown de vol
        cooldown_vol = "✅ Disponible"
        if last_steal and steal_cd:
            try:
                last_dt = parser.parse(last_steal)
                if not last_dt.tzinfo:
                    last_dt = last_dt.replace(tzinfo=timezone.utc)
                next_cd = last_dt + timedelta(hours=steal_cd)
                now_dt = datetime.now(timezone.utc)
                if now_dt < next_cd:
                    restant = next_cd - now_dt
                    h, m = divmod(int(restant.total_seconds() // 60), 60)
                    cooldown_vol = f"⏳ {restant.days}j {h}h{m}m" if restant.days else f"⏳ {h}h{m}m"
            except:
                pass

        # Cooldown du skill
        cooldown_skill = "✅ Disponible"
        if last_skill:
            try:
                last_dt = parser.parse(last_skill)
                if not last_dt.tzinfo:
                    last_dt = last_dt.replace(tzinfo=timezone.utc)
                base_cd = 12  # par défaut
                if classe_data:
                    base_cd = classe_data.get("Cooldown", 12)
                next_cd = last_dt + timedelta(hours=base_cd)
                now_dt = datetime.now(timezone.utc)
                if now_dt < next_cd:
                    restant = next_cd - now_dt
                    h, m = divmod(int(restant.total_seconds() // 60), 60)
                    cooldown_skill = f"⏳ {restant.days}j {h}h{m}m" if restant.days else f"⏳ {h}h{m}m"
            except:
                pass

        if active_skill:
            cooldown_skill = "🌀 En cours"

        # Embed profil
        embed = discord.Embed(
            title=f"🎴 Profil Reiatsu de {user.display_name}",
            description="> *L’énergie spirituelle circule en toi...*",
            color=discord.Color.purple()
        )

        # Statistiques
        embed.add_field(
            name="💠 Statistiques",
            value=f"**Reiatsu :** {points}\n**Niveau :** {niveau} ★\n(`!!quetes` pour voir les quêtes à faire pour monter de niveau)",
            inline=False
        )

        # Classe
        if classe_data:
            embed.add_field(
                name=f"🏷️ Classe : **{classe_symbole} {classe_nom}**",
                value=f"**• Passif :** {classe_data['Passive']}\n**• Skill :** {classe_data['Active']}",
                inline=False
            )
        else:
            embed.add_field(
                name=f"🏷️ Classe : Aucune classe choisie",
                value="`!!classe` pour choisir une classe",
                inline=False
            )

        # Cooldowns
        embed.add_field(
            name="⏳ Cooldowns",
            value=f"**Vol :** `!!rtsv` — {cooldown_vol}\n**Skill :** `!!skill` — {cooldown_skill}",
            inline=False
        )

        embed.set_footer(text="💠 Utilise `!!tutoreiatsu` ou `!!tutorts` pour en savoir plus sur le Reiatsu.")

        # Envoi du profil
        if isinstance(channel_or_interaction, discord.Interaction):
            await channel_or_interaction.response.send_message(embed=embed)
        else:
            await safe_send(channel_or_interaction, embed=embed)

    # ============================================================
    # 🔹 Commande SLASH
    # ============================================================
    @app_commands.command(
        name="reiatsuprofil",
        description="💠 Affiche ton profil Reiatsu détaillé."
    )
    @app_commands.describe(member="Voir le profil Reiatsu d’un autre joueur")
    @app_commands.checks.cooldown(rate=1, per=5.0, key=lambda i: i.user.id)
    async def slash_profil(self, interaction: discord.Interaction, member: discord.Member = None):
        await self._send_profil(interaction, interaction.user, member)

    # ============================================================
    # 🔹 Commande PREFIX
    # ============================================================
    @commands.command(
        name="reiatsuprofil",
        aliases=["rtsp", "rtsprofil", "profil", "p"],
        help="💠 Affiche ton profil Reiatsu détaillé."
    )
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_profil(self, ctx: commands.Context, member: discord.Member = None):
        await self._send_profil(ctx.channel, ctx.author, member)

# ================================================================
# 🔌 Setup du Cog
# ================================================================
async def setup(bot: commands.Bot):
    cog = ReiatsuProfil(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Reiatsu"
    await bot.add_cog(cog)
