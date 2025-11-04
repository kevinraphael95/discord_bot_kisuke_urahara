# ────────────────────────────────────────────────────────────────────────────────#
# 📌 kisukevol.py — Commande admin /kisukevol et !kisukevol
# Objectif : Kisuke vole aléatoirement 10% du Reiatsu d’un membre du serveur
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
from datetime import datetime, timedelta, timezone
from dateutil import parser
from utils.supabase_client import supabase
from utils.discord_utils import safe_send
from utils.reiatsu_utils import ensure_profile
import random

# ────────────────────────────────────────────────────────────────────────────────#
# ⚙️ Paramètres de configuration
# ────────────────────────────────────────────────────────────────────────────────#
VOL_COOLDOWN_HOURS = 24      # Cooldown interne pour Kisuke
VOL_PROBA_VOLEUR = 0.67      # Chance de réussite si Kisuke est Voleur
VOL_PROBA_AUTRE = 0.25       # Chance de réussite pour les autres classes

# ────────────────────────────────────────────────────────────────────────────────#
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────#
class KisukeVol(commands.Cog):
    """
    Commande /kisukevol et !kisukevol — Kisuke vole un joueur comme un joueur normal
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction interne commune
    # ────────────────────────────────────────────────────────────────────────────
    async def _kisukevol_logic(self, channel: discord.abc.Messageable, guild: discord.Guild):
        try:
            # ✅ Récupère tous les membres du serveur ayant du Reiatsu > 0
            data = supabase.table("reiatsu").select("*").gt("points", 0).execute()
            membres_db = [entry for entry in data.data if guild.get_member(int(entry["user_id"]))]
            if not membres_db:
                await safe_send(channel, "⚠️ Aucun membre valide trouvé avec du Reiatsu.")
                return

            # 🎯 Choisit une cible aléatoire
            cible_data = random.choice(membres_db)
            cible_id = int(cible_data["user_id"])
            cible = guild.get_member(cible_id)

            # ✅ Kisuke = le bot
            kisuke_member = self.bot.user
            kisuke_id = int(kisuke_member.id)
            ensure_profile(kisuke_id, "Kisuke")

            # 📥 Récupération des données Kisuke
            kisuke_res = supabase.table("reiatsu").select("*").eq("user_id", kisuke_id).execute()
            if not kisuke_res.data:
                await safe_send(channel, "⚠️ Impossible de charger le profil de Kisuke.")
                return
            kisuke_data = kisuke_res.data[0]
            kisuke_points = kisuke_data.get("points", 0) or 0
            kisuke_classe = kisuke_data.get("classe")
            kisuke_active_skill = bool(kisuke_data.get("active_skill", False))
            dernier_vol_str = kisuke_data.get("last_steal_attempt")

            # ⏱ Gestion du cooldown
            now = datetime.now(tz=timezone.utc)
            if dernier_vol_str:
                try:
                    dernier_vol = parser.parse(dernier_vol_str)
                    if not dernier_vol.tzinfo:
                        dernier_vol = dernier_vol.replace(tzinfo=timezone.utc)
                    prochain_vol = dernier_vol + timedelta(hours=VOL_COOLDOWN_HOURS)
                    if now < prochain_vol:
                        restant = prochain_vol - now
                        j = restant.days
                        h, rem = divmod(restant.seconds, 3600)
                        m, _ = divmod(rem, 60)
                        await safe_send(channel, f"⏳ Kisuke doit encore attendre **{j}j {h}h{m}m** avant de retenter.")
                        return
                except Exception as e:
                    print(f"[WARN] Impossible de parser last_steal_attempt pour Kisuke : {e}")

            # 📥 Récupération des données cible
            cible_points = cible_data.get("points", 0) or 0
            cible_classe = cible_data.get("classe")
            if cible_points == 0:
                await safe_send(channel, f"⚠️ {cible.mention} n’a pas de Reiatsu à voler.")
                return

            if kisuke_points == 0:
                await safe_send(channel, "⚠️ Kisuke doit avoir au moins **1 point** de Reiatsu pour tenter un vol.")
                return

            # 🎲 Calcul du vol : 2% du Reiatsu de la cible (min 1)
            montant = max(1, cible_points // 50)

            # 🔹 Gestion du skill actif
            if kisuke_classe == "Voleur" and kisuke_active_skill:
                succes = True
                montant *= 2
                try:
                    supabase.table("reiatsu").update({"active_skill": False}).eq("user_id", kisuke_id).execute()
                except Exception as e:
                    print(f"[WARN] Impossible de désactiver active_skill pour Kisuke : {e}")
            else:
                succes = random.random() < (VOL_PROBA_VOLEUR if kisuke_classe == "Voleur" else VOL_PROBA_AUTRE)

            # 📝 Enregistre la tentative
            supabase.table("reiatsu").update({"last_steal_attempt": now.isoformat()}).eq("user_id", kisuke_id).execute()

            if succes:
                # Mise à jour des points
                supabase.table("reiatsu").update({"points": kisuke_points + montant}).eq("user_id", kisuke_id).execute()

                if cible_classe == "Illusionniste" and random.random() < 0.5:
                    await safe_send(channel, f"🩸 Kisuke a volé **{montant}** points à {cible.mention}... mais c'était une illusion, {cible.mention} n'a rien perdu !")
                else:
                    supabase.table("reiatsu").update({"points": max(0, cible_points - montant)}).eq("user_id", cible_id).execute()
                    await safe_send(channel, f"🩸 Kisuke a réussi à voler **{montant}** points de Reiatsu à {cible.mention} !")
            else:
                await safe_send(channel, f"😵 Kisuke a tenté de voler {cible.mention}... mais a échoué !")

        except Exception as e:
            await safe_send(channel, f"❌ Une erreur est survenue lors du vol de Kisuke : `{e}`")

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="kisukevol",
        description="🌀 Kisuke vole 10% du Reiatsu d’un membre comme un joueur normal."
    )
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.checks.cooldown(1, 10.0, key=lambda i: i.user.id)
    async def slash_kisukevol(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self._kisukevol_logic(interaction.channel, interaction.guild)
        await interaction.delete_original_response()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(
        name="kisukevol",
        aliases=["kvol"],
        help="🌀 Kisuke vole 10% du Reiatsu d’un membre comme un joueur normal."
    )
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 10.0, commands.BucketType.user)
    async def prefix_kisukevol(self, ctx: commands.Context):
        await self._kisukevol_logic(ctx.channel, ctx.guild)

# ────────────────────────────────────────────────────────────────────────────────#
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────#
async def setup(bot: commands.Bot):
    cog = KisukeVol(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Admin"
    await bot.add_cog(cog)
