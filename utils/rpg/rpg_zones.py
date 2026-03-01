# ────────────────────────────────────────────────────────────────────────────────
# 📌 rpg_zones.py — Gestion des zones RPG
# ────────────────────────────────────────────────────────────────────────────────

import sqlite3
import json
import os
import discord

DB_PATH = os.path.join("database", "reiatsu.db")

def get_conn():
    return sqlite3.connect(DB_PATH)

# ────────────────────────────────────────────────────────────────────────────────
# 🔹 Déplacement et affichage des zones
# ────────────────────────────────────────────────────────────────────────────────
async def change_zone(zone_target, unlocked_zones, current_zone, user_id, send):
    if zone_target:
        if zone_target in unlocked_zones:
            conn = get_conn()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE rpg_players SET zone = ? WHERE user_id = ?",
                (zone_target, user_id)
            )
            conn.commit()
            conn.close()
            return await send(f"📍 Vous vous déplacez vers la zone **{zone_target}**.")
        return await send(f"❌ Zone **{zone_target}** non débloquée. Battez les boss de la zone actuelle d'abord.")

    return await _get_zone_info(unlocked_zones, current_zone, send)


async def _get_zone_info(unlocked_zones, current_zone, send):
    embed = discord.Embed(
        title="🗺️ Zones",
        color=discord.Color.orange()
    )
    zones_display = []
    for z in unlocked_zones:
        prefix = "📍 " if z == current_zone else "✅ "
        zones_display.append(f"{prefix}Zone {z}")

    embed.add_field(name="Zones débloquées", value="\n".join(zones_display) or "Aucune", inline=False)
    embed.add_field(name="Zone actuelle", value=f"Zone {current_zone}", inline=False)
    embed.set_footer(text="Utilisez !rpg zone <numéro> pour vous déplacer")
    return await send(embed)
