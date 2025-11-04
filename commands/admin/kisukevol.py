# ────────────────────────────────────────────────────────────────────────────────#
# 📌 kisukevol.py — Commande admin /kisukevol et !kisukevol
# Objectif : Kisuke vole aléatoirement ~2% du Reiatsu d’un membre du serveur et le multiplie ×10
# Catégorie : Admin
# Accès : Admin uniquement
# Cooldown : 1 utilisation / 10 secondes / administrateur
# ────────────────────────────────────────────────────────────────────────────────#

# ────────────────────────────────────────────────────────────────────────────────#
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────#
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone
import random
from utils.supabase_client import supabase
from utils.discord_utils import safe_send, safe_respond
from utils.reiatsu_utils import ensure_profile

# ────────────────────────────────────────────────────────────────────────────────#
# ⚙️ Paramètres de configuration
# ────────────────────────────────────────────────────────────────────────────────#
KISUKE_MULTIPLIER = 10   # Multiplie le gain de Kisuke (×10 du montant volé)
ADMIN_LOG_CHANNEL_ID = None  # Optionnel : ID d’un salon pour les logs admin
VOL_COOLDOWN_HOURS = 6       # Cooldown interne (6h) pour Kisuke lui-même
VOL_PROBA_VOLEUR = 0.67      # Chance de succès si Kisuke est Voleur
VOL_PROBA_AUTRE = 0.25       # Chance de succès pour les autres classes

# ────────────────────────────────────────────────────────────────────────────────#
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────#
class KisukeVol(commands.Cog):
    """
    Commande /kisukevol et !kisukevol — Kisuke vole un peu de Reiatsu à un membre aléatoire
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction interne commune
    # ────────────────────────────────────────────────────────────────────────────
    async def _kisukevol_logic(self, admin: discord.Member, channel: discord.abc.Messageable, guild: discord.Guild):
        # Récupère tous les utilisateurs du serveur avec Reiatsu > 0 dans la base
        try:
            data = supabase.table("reiatsu").select("*").gt("points", 0).execute()
            if not data.data:
                await safe_send(channel, "⚠️ Aucun utilisateur n’a de Reiatsu dans la base.")
                return

            # Filtrer uniquement ceux qui sont encore sur le serveur
            membres_db = [entry for entry in data.data if guild.get_member(int(entry["user_id"]))]

            if not membres_db:
                await safe_send(channel, "⚠️ Aucun membre valide trouvé dans la base et sur le serveur.")
                return

            # Choisit une cible aléatoire parmi eux
            cible_data = random.choice(membres_db)
            cible_id = int(cible_data["user_id"])
            cible = guild.get_member(cible_id)

        except Exception as e:
            await safe_send(channel, f"❌ Erreur en accédant à la base Supabase : `{e}`")
            return

        # Kisuke = le bot lui-même
        kisuke_member = self.bot.user
        kisuke_id = int(kisuke_member.id)

        # Vérifie et crée les profils si nécessaires
        ensure_profile(kisuke_id, "Kisuke")

        # Récupération des données Kisuke
        kisuke_res = supabase.table("reiatsu").select("*").eq("user_id", kisuke_id).execute()
        if not kisuke_res.data:
            await safe_send(channel, "⚠️ Impossible de charger le profil de Kisuke.")
            return

        kisuke_data = kisuke_res.data[0]
        kisuke_points = kisuke_data.get("points", 0) or 0
        kisuke_classe = kisuke_data.get("classe")
        kisuke_active_skill = bool(kisuke_data.get("active_skill", False))
        dernier_vol = kisuke_data.get("last_steal_attempt")

        # Cooldown interne
        now = datetime.now(tz=timezone.utc)
        if dernier_vol:
            try:
                dernier_vol_dt = datetime.fromisoformat(dernier_vol)
                if dernier_vol_dt.tzinfo is None:
                    dernier_vol_dt = dernier_vol_dt.replace(tzinfo=timezone.utc)
                if (now - dernier_vol_dt).total_seconds() < VOL_COOLDOWN_HOURS * 3600:
                    await safe_send(channel, "🕒 Kisuke se repose encore de sa dernière expérience...")
                    return
            except Exception:
                pass

        # Récupère les infos de la cible
        cible_points = cible_data.get("points", 0) or 0
        cible_classe = cible_data.get("classe")

        if cible_points <= 0:
            await safe_send(channel, f"💨 Kisuke a tenté de voler {cible.mention}, mais il n’avait **aucun Reiatsu** !")
            return

        # 💰 Calcule 2% du Reiatsu (minimum 1)
        montant = max(1, int(cible_points * 0.02))

        # 🎲 Calcul du succès
        if kisuke_classe == "Voleur" and kisuke_active_skill:
            succes = True
            supabase.table("reiatsu").update({"active_skill": False}).eq("user_id", kisuke_id).execute()
        else:
            succes = random.random() < (VOL_PROBA_VOLEUR if kisuke_classe == "Voleur" else VOL_PROBA_AUTRE)

        # Mise à jour du timestamp (tentative)
        supabase.table("reiatsu").update({"last_steal_attempt": now.isoformat()}).eq("user_id", kisuke_id).execute()

        # ✅ Succès du vol
        if succes:
            nouveau_cible_points = max(0, cible_points - montant)
            gain_kisuke = montant * KISUKE_MULTIPLIER

            # Mise à jour en base
            supabase.table("reiatsu").update({"points": nouveau_cible_points}).eq("user_id", cible_id).execute()
            supabase.table("reiatsu").update({"points": kisuke_points + gain_kisuke}).eq("user_id", kisuke_id).execute()

            embed = discord.Embed(
                title="🌀 Kisuke a frappé !",
                description=(
                    f"Kisuke a volé **{montant} Reiatsu** à {cible.mention} 😏\n"
                    f"→ Grâce à son laboratoire, il en tire **{gain_kisuke} Reiatsu** !"
                ),
                color=discord.Color.orange()
            )
            embed.set_footer(text="Le laboratoire de Kisuke ne manque jamais d’énergie…")
            await safe_send(channel, embed=embed)

            # Log optionnel
            if ADMIN_LOG_CHANNEL_ID:
                log_channel = guild.get_channel(ADMIN_LOG_CHANNEL_ID)
                if log_channel:
                    await safe_send(
                        log_channel,
                        f"🧪 Kisuke a volé **{montant} Reiatsu** à {cible.mention} (→ +{gain_kisuke} Reiatsu)."
                    )

        # ❌ Échec du vol
        else:
            await safe_send(channel, f"😵 Kisuke a tenté de voler {cible.mention}... mais a échoué !")

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="kisukevol",
        description="🌀 Kisuke vole un peu de Reiatsu (2%) à un membre au hasard et le récupère ×10."
    )
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.checks.cooldown(1, 10.0, key=lambda i: i.user.id)
    async def slash_kisukevol(self, interaction: discord.Interaction):
        """Commande slash admin"""
        await interaction.response.defer()
        await self._kisukevol_logic(interaction.user, interaction.channel, interaction.guild)
        await interaction.delete_original_response()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(
        name="kisukevol",
        aliases=["kvol"],
        help="🌀 Kisuke vole un peu de Reiatsu à un membre aléatoire du serveur."
    )
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 10.0, commands.BucketType.user)
    async def prefix_kisukevol(self, ctx: commands.Context):
        """Commande préfixe admin"""
        await self._kisukevol_logic(ctx.author, ctx.channel, ctx.guild)

# ────────────────────────────────────────────────────────────────────────────────#
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────#
async def setup(bot: commands.Bot):
    cog = KisukeVol(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Admin"
    await bot.add_cog(cog)




