# ────────────────────────────────────────────────────────────────────────────────
# 📌 rpg_embeds.py — Embeds RPG
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from datetime import datetime, timedelta

# ────────────────────────────────────────────────────────────
# Menu principal
# ────────────────────────────────────────────────────────────
def menu_embed():
    return discord.Embed(
        title="🗡️ RPG Bleach",
        description=(
            "Bienvenue dans le RPG inspiré de Bleach ! Tu es un shinigami rebelle et ton but est de détruire la Soul Society.\n\n"
            "**Commandes disponibles :**\n"
            "`!rpg profil` — Statistiques et équipement\n"
            "`!rpg combat` — Combat contre un shinigami de base\n"
            "`!rpg boss` — Affronter un vice-capitaine puis un capitaine\n"
            "`!rpg zone` — Voir les zones débloquées et se déplacer\n\n"
            "**Comment Jouer :**\n"
            "Affronter les 13 Divisions des 13 armées de la cour, faire des combhat pour monter les stats puis battre les 2 boss de chaque zone pour passer à la suivante avec rpg zone."
        ),
        color=discord.Color.red()
    )

# ────────────────────────────────────────────────────────────
# Profil joueur
# ────────────────────────────────────────────────────────────
def profile_embed(player_data, stats, cooldowns, now):
    CD_DURATIONS = {"combat": 300, "boss": 3600}
    
    embed = discord.Embed(
        title=f"📘 Profil de {player_data.get('username', 'Joueur')}",
        color=discord.Color.blue()
    )

    # 📊 Stats principales
    embed.add_field(
        name="📊 Stats",
        value=(
            f"Niveau: {stats.get('level',1)} (XP: {stats.get('xp',0)}/{stats.get('xp_next',100)})\n"
            f"💖 HP : {stats.get('hp',0)} / {stats.get('hp_max',100)}\n"
            f"🔮 SP : {stats.get('sp',0)}\n"
            f"⚔️ ATK : {stats.get('atk',0)} / 🛡️ DEF: {stats.get('def',0)}\n"
            f"🤺 DEX : {stats.get('dex',0)} / 🏃 EVA: {stats.get('eva',0)}\n"
            f"🎯 Crit: {stats.get('crit',0)}"
        ),
        inline=False
    )

    # 🏷️ Classe
    player_class = player_data.get("class") or "Aucun"
    embed.add_field(name="🏷️ Classe", value=player_class, inline=False)

    # ✨ Effets actifs
    active_effects = ", ".join(stats.get("effects", {}).keys()) or "Aucun"
    embed.add_field(name="✨ Effets actifs", value=active_effects, inline=False)

    # ⏱️ Cooldowns
    cd_text = ""
    for cmd, dt_str in cooldowns.items():
        dt = datetime.fromisoformat(dt_str)
        elapsed = (now - dt).total_seconds()
        remaining = max(0, CD_DURATIONS.get(cmd, 0) - elapsed)
        cd_text += f"{cmd.upper()}: {'✅ ready' if remaining <= 0 else str(timedelta(seconds=int(remaining)))}\n"
    embed.add_field(name="⏱️ Cooldowns", value=cd_text or "Aucun", inline=False)

    # 🗺️ Zones
    embed.add_field(name="🗺️ Zones débloquées", value=", ".join(player_data.get("unlocked_zones", ["1"])), inline=False)
    embed.add_field(name="📍 Zone actuelle", value=str(player_data.get("zone", "1")), inline=False)

    return embed
