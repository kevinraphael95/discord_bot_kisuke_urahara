# ────────────────────────────────────────────────────────────────────────────────
# 📌 skill.py — Commande interactive /skill et !skill
# Objectif : Activer la compétence active de la classe du joueur 
# (Illusionniste, Voleur, Absorbeur, Parieur)
# Catégorie : Reiatsu
# Accès : Tous
# Cooldown : 12h (8h pour Illusionniste)
# ────────────────────────────────────────────────────────────────────────────────


# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
import datetime
import os
import json

from utils.discord_utils import safe_send, safe_respond
from utils.supabase_client import supabase


# ────────────────────────────────────────────────────────────────────────────────
# 📦 Tables utilisées
# ────────────────────────────────────────────────────────────────────────────────
TABLES = {
    "reiatsu": {
        "description": "Table principale contenant les informations Reiatsu de chaque joueur : points, classe et compétences actives.",
        "colonnes": {
            "user_id": "BIGINT — Identifiant Discord unique du joueur (clé primaire)",
            "username": "TEXT — Nom d'utilisateur Discord",
            "points": "BIGINT — Montant actuel de Reiatsu du joueur",
            "bonus5": "INT — Compteur de bonus pour la classe Travailleur",
            "classe": "TEXT — Classe actuelle du joueur (Illusionniste, Voleur, Absorbeur, Parieur, etc.)",
            "last_skilled_at": "TIMESTAMPTZ — Dernière utilisation de la compétence",
            "active_skill": "BOOLEAN — Indique si une compétence est actuellement active",
            "fake_spawn_id": "BIGINT — ID du faux Reiatsu généré (Illusionniste)",
        },
    },
    "reiatsu_config": {
        "description": "Table de configuration pour chaque serveur Reiatsu : salons, spawns et vitesses de spawn.",
        "colonnes": {
            "guild_id": "BIGINT — Identifiant du serveur Discord (clé primaire)",
            "channel_id": "BIGINT — ID du salon où spawnent les Reiatsu",
            "is_spawn": "BOOLEAN — Indique si un Reiatsu est actuellement présent",
            "message_id": "BIGINT — ID du message du Reiatsu actif",
            "spawn_speed": "TEXT — Vitesse de spawn ('Lent', 'Normal', 'Rapide', etc.)",
            "last_spawn_at": "TIMESTAMPTZ — Dernier spawn effectué",
            "spawn_delay": "INT — Délai entre deux spawns (en secondes)",
        },
    },
}


# ────────────────────────────────────────────────────────────────────────────────
# 📂 Chargement de la configuration Reiatsu
# ────────────────────────────────────────────────────────────────────────────────
REIATSU_CONFIG_PATH = os.path.join("data", "reiatsu_config.json")

def load_reiatsu_config():
    """Charge la configuration Reiatsu depuis le fichier JSON."""
    try:
        with open(REIATSU_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERREUR JSON] Impossible de charger {REIATSU_CONFIG_PATH} : {e}")
        return {}


# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal : Skill
# ────────────────────────────────────────────────────────────────────────────────
class Skill(commands.Cog):
    """Commande /skill et !skill — Active la compétence active du joueur."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config = load_reiatsu_config()

    # ────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction interne : activation du skill
    # ────────────────────────────────────────────────────────────────────────
    async def _activate_skill(self, user: discord.User, channel: discord.abc.Messageable):
        """Vérifie la classe, le cooldown et active la compétence correspondante."""
        res = supabase.table("reiatsu").select("*").eq("user_id", user.id).execute()
        if not res.data:
            await safe_send(channel, "❌ Tu n'as pas encore de profil Reiatsu. Utilise `!!reiatsu` pour en créer un.")
            return

        player = res.data[0]
        classe = player.get("classe", "Travailleur")
        now = datetime.datetime.utcnow()

        # Cooldown
        cooldown_h = 8 if classe == "Illusionniste" else 12
        last_skill = player.get("last_skilled_at")

        if last_skill:
            try:
                elapsed = (now - datetime.datetime.fromisoformat(last_skill)).total_seconds() / 3600
                if elapsed < cooldown_h:
                    await safe_send(channel, f"⏳ Compétence encore en recharge. Attends **{cooldown_h - elapsed:.1f}h** avant de réessayer.")
                    return
            except Exception:
                pass

        # Préparation de la mise à jour
        update_data = {"last_skilled_at": now.isoformat(), "active_skill": True}
        msg = ""

        # Gestion des classes
        if classe == "Illusionniste":
            update_data["fake_spawn_id"] = None
            msg = "🎭 **Illusion activée !** Un faux Reiatsu apparaîtra bientôt."

        elif classe == "Voleur":
            update_data["vol_garanti"] = True
            msg = "🥷 **Vol garanti activé !** Ton prochain vol réussira à coup sûr."

        elif classe == "Absorbeur":
            msg = "🌀 **Super Absorption !** Le prochain Reiatsu sera forcément un Super Reiatsu."

        elif classe == "Parieur":
            points = player.get("points", 0)
            if points < 10:
                await safe_send(channel, "❌ Tu n'as pas assez de Reiatsu pour parier (10 requis).")
                return

            import random
            gain = 30
            if random.random() < 0.5:
                update_data["points"] = points - 10
                msg = "🎲 **Perdu !** Tu as perdu 10 Reiatsu."
            else:
                update_data["points"] = points - 10 + gain
                msg = f"🎲 **Gagné !** Tu as misé 10 Reiatsu et remporté **{gain}**."

        else:
            msg = "👶 Cette classe n’a pas encore de compétence active."

        # Mise à jour Supabase
        supabase.table("reiatsu").update(update_data).eq("user_id", user.id).execute()
        await safe_send(channel, msg)

    # ────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────
    @app_commands.command(name="skill", description="Active la compétence de ta classe Reiatsu.")
    @app_commands.checks.cooldown(rate=1, per=5.0, key=lambda i: i.user.id)
    async def slash_skill(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self._activate_skill(interaction.user, interaction.channel)
        await interaction.delete_original_response()

    # ────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────
    @commands.command(name="skill", help="Active la compétence de ta classe Reiatsu.")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_skill(self, ctx: commands.Context):
        await self._activate_skill(ctx.author, ctx.channel)


# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Skill(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Reiatsu"
    await bot.add_cog(cog)

