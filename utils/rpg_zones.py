# ────────────────────────────────────────────────────────────────────────────────
# 📌 rpg_zones.py — Gestion des zones RPG
# ────────────────────────────────────────────────────────────────────────────────
from utils.supabase_client import supabase
import discord

# ────────────────────────────────────────────────────────────
# Déplacement et affichage zones
# ────────────────────────────────────────────────────────────
async def change_zone(zone_target, unlocked_zones, current_zone, user_id, send):
    if zone_target:
        if zone_target in unlocked_zones:
            current_zone = zone_target
            supabase.table("rpg_players").update({"zone": current_zone}).eq("user_id", user_id).execute()
            return await send(f"📍 Vous vous déplacez vers la zone {current_zone}.")
        return await send(f"❌ Vous ne pouvez pas accéder à la zone {zone_target}, elle n'est pas débloquée.")
    return await get_zone_info(unlocked_zones, current_zone, send)

async def get_zone_info(unlocked_zones, current_zone, send):
    embed = discord.Embed(
        title="🗺️ Zones débloquées",
        description=", ".join(unlocked_zones),
        color=discord.Color.orange()
    )
    embed.add_field(name="Zone actuelle", value=current_zone)
    return await send(embed)
