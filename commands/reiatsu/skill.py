# ────────────────────────────────────────────────────────────────────────────────
# 📌 skill.py — Commande interactive /skill et !skill
# Objectif : Afficher et activer la compétence active du joueur
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
import asyncio
from utils.discord_utils import safe_send, safe_respond
from utils.supabase_client import supabase
from utils.reiatsu_utils import ensure_profile, has_class, get_skill_cooldown

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
        self.skill_locks = {}  # Lock pour chaque utilisateur

    # ────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction interne : activation du skill
    # ────────────────────────────────────────────────────────────────────────
    async def _activate_skill(self, user: discord.User, channel: discord.abc.Messageable):
        """Vérifie la classe, calcule le cooldown et active la compétence correspondante."""
        if user.id not in self.skill_locks:
            self.skill_locks[user.id] = asyncio.Lock()

        async with self.skill_locks[user.id]:
            # ✅ Création automatique du profil
            player = ensure_profile(user.id, user.name)

            # ❌ Si pas de classe choisie
            if not has_class(player):
                await safe_send(channel, "❌ Tu n’as pas encore choisi de classe Reiatsu. Utilise `/choisir_classe` pour débloquer ton skill.")
                return

            classe = player["classe"]
            now = datetime.datetime.utcnow()
            classe_data = self.config["CLASSES"].get(classe, {})

            # 🔹 Cooldown
            remaining = get_skill_cooldown(player, classe_data)
            if remaining > 0:
                remaining_seconds = remaining * 3600
                days = int(remaining_seconds // 86400)
                hours = int((remaining_seconds % 86400) // 3600)
                minutes = int((remaining_seconds % 3600) // 60)
                next_ready = now + datetime.timedelta(seconds=remaining_seconds)
                next_ready_str = next_ready.strftime("%d/%m %H:%M")
                cd_text = f"⏳ {days}j {hours}h{minutes}m" if days > 0 else f"⏳ {hours}h{minutes}m"
                await safe_send(channel, f"{cd_text} — Ton skill sera de nouveau disponible vers **{next_ready_str}**.")
                return

            # 🔹 Activation
            update_data = {"last_skilled_at": now.isoformat()}
            msg = ""
            if classe == "Illusionniste":
                update_data["active_skill"] = True
                msg = "🎭 **Illusion activée !** Un faux Reiatsu apparaîtra bientôt."
            elif classe == "Voleur":
                update_data["active_skill"] = True
                msg = "🥷 **Vol garanti activé !** Ton prochain vol réussira à coup sûr."
            elif classe == "Absorbeur":
                update_data["active_skill"] = True
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

            # Mise à jour Supabase
            supabase.table("reiatsu").update(update_data).eq("user_id", user.id).execute()
            next_cd = now + datetime.timedelta(hours=classe_data.get("Cooldown", 12))
            next_ready_str = next_cd.strftime("%d/%m %H:%M")

            # Message embed
            embed = discord.Embed(
                title=f"🎭 Compétence de {classe} ({player.get('username', user.name)})",
                description=f"{msg}\n\n✅ Prêt à utiliser !\n> Prochaine disponibilité : **{next_ready_str}**",
                color=discord.Color.green()
            )
            await safe_send(channel, embed=embed)

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



