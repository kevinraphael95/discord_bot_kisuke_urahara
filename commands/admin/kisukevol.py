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
from utils.discord_utils import safe_send
from utils.reiatsu_utils import ensure_profile
import sqlite3
import random
import os

# ────────────────────────────────────────────────────────────────────────────────#
# ⚙️ Paramètres de configuration
# ────────────────────────────────────────────────────────────────────────────────#
VOL_COOLDOWN_HOURS = 24
VOL_PROBA_VOLEUR = 0.67
VOL_PROBA_AUTRE = 0.25

DB_PATH = os.path.join("database", "reiatsu.db")

def get_conn():
    return sqlite3.connect(DB_PATH)

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
            conn = get_conn()
            cursor = conn.cursor()

            # ✅ Récupère tous les membres du serveur ayant du Reiatsu > 0
            cursor.execute("SELECT * FROM reiatsu WHERE points > 0")
            rows = cursor.fetchall()

            # ✅ Kisuke = le bot (défini avant le filtre pour l'exclure des cibles)
            kisuke_member = self.bot.user
            kisuke_id = int(kisuke_member.id)
            
            membres_db = [
                row for row in rows
                if guild.get_member(int(row[0])) and int(row[0]) != kisuke_id
            ]
            
            if not membres_db:
                await safe_send(channel, "⚠️ Aucun membre valide trouvé avec du Reiatsu.")
                conn.close()
                return
            
            # 🎯 Choisit une cible aléatoire
            cible_row = random.choice(membres_db)
            cible_id = int(cible_row[0])
            cible = guild.get_member(cible_id)

            # 📥 Récupération des données Kisuke
            cursor.execute("SELECT * FROM reiatsu WHERE user_id = ?", (kisuke_id,))
            kisuke_data = cursor.fetchone()

            if not kisuke_data:
                await safe_send(channel, "⚠️ Impossible de charger le profil de Kisuke.")
                conn.close()
                return

            kisuke_points = kisuke_data[2] or 0
            kisuke_classe = kisuke_data[6]
            kisuke_active_skill = bool(kisuke_data[8])
            dernier_vol_str = kisuke_data[4]

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

                        await safe_send(
                            channel,
                            f"⏳ Kisuke doit encore attendre **{j}j {h}h{m}m** avant de retenter."
                        )
                        conn.close()
                        return

                except Exception as e:
                    print(f"[WARN] Impossible de parser last_steal_attempt pour Kisuke : {e}")

            # 📥 Récupération des données cible
            cible_points = cible_row[2] or 0
            cible_classe = cible_row[6]

            if cible_points == 0:
                await safe_send(channel, f"⚠️ {cible.mention} n’a pas de Reiatsu à voler.")
                conn.close()
                return

            if kisuke_points == 0:
                await safe_send(channel, "⚠️ Kisuke doit avoir au moins **1 point** de Reiatsu pour tenter un vol.")
                conn.close()
                return

            # 🎲 Calcul du vol : 2% du Reiatsu de la cible (min 1)
            montant = max(1, cible_points // 50)

            # 🔹 Gestion du skill actif
            if kisuke_classe == "Voleur" and kisuke_active_skill:
                succes = True
                montant *= 2
                cursor.execute(
                    "UPDATE reiatsu SET active_skill = 0 WHERE user_id = ?",
                    (kisuke_id,)
                )
            else:
                succes = random.random() < (
                    VOL_PROBA_VOLEUR if kisuke_classe == "Voleur" else VOL_PROBA_AUTRE
                )

            # 📝 Enregistre la tentative
            cursor.execute(
                "UPDATE reiatsu SET last_steal_attempt = ? WHERE user_id = ?",
                (now.isoformat(), kisuke_id)
            )

            if succes:
                # Mise à jour des points Kisuke
                cursor.execute(
                    "UPDATE reiatsu SET points = points + ? WHERE user_id = ?",
                    (montant, kisuke_id)
                )

                if cible_classe == "Illusionniste" and random.random() < 0.5:
                    await safe_send(
                        channel,
                        f"🩸 Kisuke a volé **{montant}** points à {cible.mention}... "
                        f"mais c'était une illusion, {cible.mention} n'a rien perdu !"
                    )
                else:
                    cursor.execute(
                        "UPDATE reiatsu SET points = MAX(points - ?, 0) WHERE user_id = ?",
                        (montant, cible_id)
                    )

                    await safe_send(
                        channel,
                        f"🩸 Kisuke a réussi à voler **{montant}** points de Reiatsu à {cible.mention} !"
                    )
            else:
                await safe_send(
                    channel,
                    f"😵 Kisuke a tenté de voler {cible.mention}... mais a échoué !"
                )

            conn.commit()
            conn.close()

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
