# ────────────────────────────────────────────────────────────────────────────────
# 📌 volreiatsu.py — Commande interactive /volreiatsu et !volreiatsu
# Objectif : Permet de voler 10% du Reiatsu d’un autre joueur avec probabilité de réussite
# Catégorie : Reiatsu
# Accès : Public
# Cooldown : 1 utilisation / 24h / utilisateur (persistant via Supabase)
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta, timezone
import random
import sqlite3

from utils.reiatsu_utils import ensure_profile
from utils.discord_utils import safe_send, safe_respond

DB_PATH = "database/reiatsu.db"

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class ReiatsuVol(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Connexion DB locale
    # ────────────────────────────────────────────────────────────────────────────
    def _get_db(self):
        return sqlite3.connect(DB_PATH)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Logique principale
    # ────────────────────────────────────────────────────────────────────────────
    async def _volreiatsu_logic(self, voleur: discord.Member, cible: discord.Member, channel):

        voleur_id = int(voleur.id)
        cible_id = int(cible.id)

        ensure_profile(voleur_id, voleur.name)
        ensure_profile(cible_id, cible.name)

        conn = self._get_db()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT points, classe, steal_cd, last_steal_attempt, active_skill
            FROM reiatsu WHERE user_id = ?
        """, (voleur_id,))
        voleur_data = cursor.fetchone()

        cursor.execute("""
            SELECT points, classe
            FROM reiatsu WHERE user_id = ?
        """, (cible_id,))
        cible_data = cursor.fetchone()

        voleur_points, voleur_classe, voleur_cd, last_attempt, active_skill = voleur_data
        cible_points, cible_classe = cible_data

        now = datetime.now(timezone.utc)

        # 🔹 Cooldown
        if last_attempt:
            last_dt = datetime.fromisoformat(last_attempt)
            next_attempt = last_dt + timedelta(hours=voleur_cd)

            if now < next_attempt:
                restant = next_attempt - now
                total_sec = int(restant.total_seconds())
                h, rem = divmod(total_sec, 3600)
                m, _ = divmod(rem, 60)

                await safe_send(
                    channel,
                    f"⏳ Tu dois encore attendre **{h}h {m}m** avant de retenter."
                )
                conn.close()
                return

        # 🔹 Vérifications
        if cible_points <= 0:
            await safe_send(channel, f"⚠️ {cible.mention} n’a pas de Reiatsu à voler.")
            conn.close()
            return

        if voleur_points <= 0:
            await safe_send(channel, "⚠️ Tu dois avoir au moins 1 point de Reiatsu pour voler.")
            conn.close()
            return

        montant = max(1, cible_points // 10)

        # 🔹 Skill actif
        if voleur_classe == "Voleur" and active_skill:
            succes = True
            montant *= 2
            cursor.execute(
                "UPDATE reiatsu SET active_skill = 0 WHERE user_id = ?",
                (voleur_id,)
            )
        else:
            succes = random.random() < (0.67 if voleur_classe == "Voleur" else 0.25)

        # 🔹 Enregistrement tentative
        cursor.execute(
            "UPDATE reiatsu SET last_steal_attempt = ? WHERE user_id = ?",
            (now.isoformat(), voleur_id)
        )

        # 🔹 Résultat
        if succes:

            # Ajout au voleur
            cursor.execute(
                "UPDATE reiatsu SET points = points + ? WHERE user_id = ?",
                (montant, voleur_id)
            )

            # Illusionniste
            if cible_classe == "Illusionniste" and random.random() < 0.5:
                await safe_send(
                    channel,
                    f"🩸 {voleur.mention} a volé **{montant}**... mais c’était une illusion !"
                )
            else:
                cursor.execute(
                    "UPDATE reiatsu SET points = MAX(points - ?, 0) WHERE user_id = ?",
                    (montant, cible_id)
                )
                await safe_send(
                    channel,
                    f"🩸 {voleur.mention} a volé **{montant}** points à {cible.mention} !"
                )

        else:
            await safe_send(
                channel,
                f"😵 {voleur.mention} a échoué à voler {cible.mention}."
            )

        conn.commit()
        conn.close()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Slash
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="reiatsuvol",
        description="💠 Vole 10% du Reiatsu d’un joueur."
    )
    async def slash_volreiatsu(
        self,
        interaction: discord.Interaction,
        cible: discord.Member
    ):

        if interaction.user.id == cible.id:
            await safe_respond(
                interaction,
                "❌ Tu ne peux pas te voler toi-même.",
                ephemeral=True
            )
            return

        await interaction.response.defer()
        await self._volreiatsu_logic(
            interaction.user,
            cible,
            interaction.channel
        )
        await interaction.delete_original_response()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Prefix
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="reiatsuvol", aliases=["rtsv", "volreiatsu", "vrts"])
    async def prefix_volreiatsu(
        self,
        ctx: commands.Context,
        cible: discord.Member = None
    ):

        if not cible:
            await safe_send(ctx.channel, "ℹ️ Utilisation : !reiatsuvol @membre")
            return

        if ctx.author.id == cible.id:
            await safe_send(ctx.channel, "❌ Tu ne peux pas te voler toi-même.")
            return

        await self._volreiatsu_logic(
            ctx.author,
            cible,
            ctx.channel
        )

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = ReiatsuVol(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Reiatsu"
    await bot.add_cog(cog)
