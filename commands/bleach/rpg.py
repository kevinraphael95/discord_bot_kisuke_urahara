# ────────────────────────────────────────────────────────────────────────────────
# 📌 rpg.py — Commande /rpg et !rpg
# Objectif : RPG Soul Society (profil, combat et boss)
# Catégorie : Bleach
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime

from utils.rpg_utils import create_profile_if_not_exists
from utils.rpg_zones import change_zone
from utils.rpg_embeds import menu_embed, profile_embed
from utils.supabase_client import supabase
from utils.discord_utils import safe_send, safe_respond
from utils.rpg_combat import run_combat

import json

# ────────────────────────────────────────────────────────────
# Chargement ennemis
# ────────────────────────────────────────────────────────────
with open("data/enemies.json", "r", encoding="utf-8") as f:
    ENEMIES = json.load(f)

# ────────────────────────────────────────────────────────────
# Cog principal
# ────────────────────────────────────────────────────────────
class RPG(commands.Cog):
    """Commande /rpg et !rpg — RPG Soul Society"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────
    # Commande SLASH
    # ────────────────────────────────────────────────────────────
    @app_commands.command(name="rpg", description="Affiche le RPG Soul Society, profil, combat et boss")
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_rpg(self, interaction: discord.Interaction, action: str = None, zone_target: str = None):
        await self.process_rpg(interaction.user.id, interaction, action, zone_target, is_slash=True)

    # ────────────────────────────────────────────────────────────
    # Commande PREFIX
    # ────────────────────────────────────────────────────────────
    @commands.command(name="rpg")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_rpg(self, ctx: commands.Context, action: str = None, zone_target: str = None):
        await self.process_rpg(ctx.author.id, ctx, action, zone_target, is_slash=False)

    # ────────────────────────────────────────────────────────────
    # Fonction principale
    # ────────────────────────────────────────────────────────────
    async def process_rpg(self, user_id, ctx, action, zone_target=None, is_slash=False):
        username = ctx.user.name if is_slash else ctx.author.name
        await create_profile_if_not_exists(user_id, username)

        res = supabase.table("rpg_players").select("*").eq("user_id", user_id).execute()
        if not res.data:
            msg = "❌ Impossible de charger ton profil."
            return await (safe_respond(ctx, msg) if is_slash else safe_send(ctx.channel, msg))
        player_data = res.data[0]

        stats = player_data.get("stats", {})
        cooldowns = player_data.get("cooldowns", {})
        zone = str(player_data.get("zone", "1"))
        unlocked_zones = player_data.get("unlocked_zones", ["1"])
        now = datetime.utcnow()

        # ────────────────────────────────────────────────────────────
        # Fonction send simplifiée
        # ────────────────────────────────────────────────────────────
        async def send(content, view=None):
            if isinstance(content, discord.Embed):
                if is_slash:
                    return await ctx.followup.send(embed=content, view=view)
                return await ctx.send(embed=content, view=view)
            if is_slash:
                return await safe_respond(ctx, content)
            return await safe_send(ctx.channel, content)

        # ────────────────────────────────────────────────────────────
        # Aucune action → menu
        # ────────────────────────────────────────────────────────────
        if not action:
            return await send(menu_embed())

        action = action.lower()

        # ────────────────────────────────────────────────────────────
        # Cooldowns combat / boss
        # ────────────────────────────────────────────────────────────
        CD_DURATIONS = {"combat": 300, "boss": 3600}
        if action in ["combat", "boss"]:
            last = datetime.fromisoformat(cooldowns.get(action, "1970-01-01T00:00:00"))
            remaining = CD_DURATIONS[action] - (now - last).total_seconds()
            if remaining > 0:
                return await send(f"⏳ **{action.upper()}** en cooldown — reviens dans `{str(timedelta(seconds=int(remaining)))}`.")
            cooldowns[action] = now.isoformat()
            supabase.table("rpg_players").update({"cooldowns": cooldowns}).eq("user_id", user_id).execute()

        # ────────────────────────────────────────────────────────────
        # Profil
        # ────────────────────────────────────────────────────────────
        if action == "profil":
            return await send(profile_embed(player_data, stats, cooldowns, now))

        # ────────────────────────────────────────────────────────────
        # Zones / map
        # ────────────────────────────────────────────────────────────
        if action in ["zone", "map"]:
            return await change_zone(zone_target, unlocked_zones, zone, user_id, send)

        # ────────────────────────────────────────────────────────────
        # Combat / boss
        # ────────────────────────────────────────────────────────────
        is_boss = action == "boss"
        await run_combat(user_id, is_boss, zone, stats, cooldowns, ctx, is_slash, ENEMIES)

# ────────────────────────────────────────────────────────────
# Setup Cog
# ────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = RPG(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Bleach"
    await bot.add_cog(cog)
