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

from utils.reiatsu_utils import ensure_profile
from utils.supabase_client import supabase
from utils.discord_utils import safe_send, safe_respond

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class ReiatsuVol(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Logique principale
    # ────────────────────────────────────────────────────────────────────────────
    async def _volreiatsu_logic(self, voleur: discord.Member, cible: discord.Member, channel):

        voleur_id = int(voleur.id)
        cible_id = int(cible.id)

        # ✅ Création ou récupération des profils via Supabase
        profile_voleur = ensure_profile(voleur_id, voleur.name)
        profile_cible = ensure_profile(cible_id, cible.name)

        voleur_points = profile_voleur.get("points", 0)
        voleur_classe = profile_voleur.get("classe")
        voleur_cd = profile_voleur.get("steal_cd", 24)
        last_attempt = profile_voleur.get("last_steal_attempt")
        active_skill = profile_voleur.get("active_skill", False)

        cible_points = profile_cible.get("points", 0)
        cible_classe = profile_cible.get("classe")

        now = datetime.now(timezone.utc)

        # 🔹 Cooldown
        if last_attempt:
            last_dt = datetime.fromisoformat(last_attempt)
            next_attempt = last_dt + timedelta(hours=voleur_cd)
            if now < next_attempt:
                restant = next_attempt - now
                j, h_rem = divmod(restant.seconds, 86400)
                h, rem = divmod(h_rem, 3600)
                m, _ = divmod(rem, 60)
                await safe_send(channel, f"⏳ Tu dois encore attendre **{j}j {h}h {m}m** avant de retenter.")
                return

        # 🔹 Vérifications de base
        if cible_points <= 0:
            await safe_send(channel, f"⚠️ {cible.mention} n’a pas de Reiatsu à voler.")
            return
        if voleur_points <= 0:
            await safe_send(channel, "⚠️ Tu dois avoir au moins 1 point de Reiatsu pour voler.")
            return

        montant = max(1, cible_points // 10)

        # 🔹 Skill actif
        if voleur_classe == "Voleur" and active_skill:
            succes = True
            montant *= 2
            supabase.table("reiatsu").update({"active_skill": False}).eq("user_id", voleur_id).execute()
        else:
            succes = random.random() < (0.67 if voleur_classe == "Voleur" else 0.25)

        # 🔹 Enregistrement de la tentative
        supabase.table("reiatsu").update({"last_steal_attempt": now.isoformat()}).eq("user_id", voleur_id).execute()

        # 🔹 Résultat
        if succes:
            # Ajout au voleur
            supabase.table("reiatsu").update({"points": voleur_points + montant}).eq("user_id", voleur_id).execute()

            # Illusionniste
            if cible_classe == "Illusionniste" and random.random() < 0.5:
                await safe_send(channel, f"🩸 {voleur.mention} a volé **{montant}**... mais c’était une illusion !")
            else:
                supabase.table("reiatsu").update({"points": max(0, cible_points - montant)}).eq("user_id", cible_id).execute()
                await safe_send(channel, f"🩸 {voleur.mention} a volé **{montant}** points à {cible.mention} !")
        else:
            await safe_send(channel, f"😵 {voleur.mention} a échoué à voler {cible.mention}.")

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Slash
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(name="reiatsuvol", description="💠 Vole 10% du Reiatsu d’un joueur.")
    async def slash_volreiatsu(self, interaction: discord.Interaction, cible: discord.Member):

        if interaction.user.id == cible.id:
            await safe_respond(interaction, "❌ Tu ne peux pas te voler toi-même.", ephemeral=True)
            return

        await interaction.response.defer()
        await self._volreiatsu_logic(interaction.user, cible, interaction.channel)
        await interaction.delete_original_response()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Prefix
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="reiatsuvol", aliases=["vrts"])
    async def prefix_volreiatsu(self, ctx: commands.Context, cible: discord.Member = None):

        if not cible:
            await safe_send(ctx.channel, "ℹ️ Utilisation : !reiatsuvol @membre")
            return

        if ctx.author.id == cible.id:
            await safe_send(ctx.channel, "❌ Tu ne peux pas te voler toi-même.")
            return

        await self._volreiatsu_logic(ctx.author, cible, ctx.channel)


# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = ReiatsuVol(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Reiatsu"
    await bot.add_cog(cog)
