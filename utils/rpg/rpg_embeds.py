# ────────────────────────────────────────────────────────────────────────────────
# 📌 rpg_embeds.py — Embeds RPG
# ────────────────────────────────────────────────────────────────────────────────

import discord
from datetime import datetime, timedelta

CD_DURATIONS = {"combat": 300, "boss": 3600}

# ────────────────────────────────────────────────────────────────────────────────
# 🔹 Menu principal
# ────────────────────────────────────────────────────────────────────────────────
def menu_embed() -> discord.Embed:
    return discord.Embed(
        title="🗡️ RPG Bleach — Soul Society",
        description=(
            "Bienvenue dans le RPG inspiré de Bleach ! Tu es un shinigami rebelle et ton but est de détruire la Soul Society.\n\n"
            "**Commandes disponibles :**\n"
            "`!rpg profil` — Statistiques et équipement\n"
            "`!rpg combat` — Combat contre un shinigami de base *(CD : 5 min)*\n"
            "`!rpg boss` — Affronter un vice-capitaine puis un capitaine *(CD : 1h)*\n"
            "`!rpg zone [numéro]` — Voir les zones ou se déplacer\n"
            "`!rpg classe` — Choisir ou consulter sa classe\n\n"
            "**Comment jouer :**\n"
            "Affrontez les 13 Divisions, montez en niveau grâce aux combats, puis battez les 2 boss de chaque zone pour débloquer la suivante."
        ),
        color=discord.Color.red()
    )

# ────────────────────────────────────────────────────────────────────────────────
# 🔹 Profil joueur
# ────────────────────────────────────────────────────────────────────────────────
def profile_embed(player_data: dict, stats: dict, cooldowns: dict, now: datetime) -> discord.Embed:
    embed = discord.Embed(
        title=f"📘 Profil de {player_data.get('username', 'Joueur')}",
        color=discord.Color.blue()
    )

    # Barre de vie visuelle
    hp = stats.get("hp", 0)
    hp_max = stats.get("hp_max", 100)
    hp_pct = int((hp / max(1, hp_max)) * 10)
    hp_bar = "🟥" * hp_pct + "⬛" * (10 - hp_pct)

    # Barre XP visuelle
    xp = stats.get("xp", 0)
    xp_next = stats.get("xp_next", 100)
    xp_pct = int((xp / max(1, xp_next)) * 10)
    xp_bar = "🟨" * xp_pct + "⬛" * (10 - xp_pct)

    embed.add_field(
        name="📊 Stats",
        value=(
            f"**Niveau {stats.get('level', 1)}** — XP : {xp}/{xp_next}\n"
            f"{xp_bar}\n\n"
            f"💖 HP : {hp}/{hp_max}\n"
            f"{hp_bar}\n"
            f"🔮 SP : {stats.get('sp', 0)}\n\n"
            f"⚔️ ATK : **{stats.get('atk', 0)}** │ 🛡️ DEF : **{stats.get('def', 0)}**\n"
            f"🤺 DEX : **{stats.get('dex', 0)}** │ 🏃 EVA : **{stats.get('eva', 0)}**\n"
            f"🎯 Crit : **{stats.get('crit', 0)}**"
        ),
        inline=False
    )

    embed.add_field(
        name="🏷️ Classe",
        value=player_data.get("class") or "Aucune — utilisez `!rpg classe`",
        inline=True
    )

    embed.add_field(
        name="📍 Zone",
        value=f"Zone {player_data.get('zone', '1')}",
        inline=True
    )

    # Effets actifs
    effects = stats.get("effects", {})
    embed.add_field(
        name="✨ Effets actifs",
        value=", ".join(effects.keys()) if effects else "Aucun",
        inline=False
    )

    # Cooldowns
    cd_lines = []
    for cmd, dt_str in cooldowns.items():
        try:
            dt = datetime.fromisoformat(dt_str)
            elapsed = (now - dt).total_seconds()
            remaining = max(0, CD_DURATIONS.get(cmd, 0) - elapsed)
            status = "✅ Prêt" if remaining <= 0 else f"⏳ {str(timedelta(seconds=int(remaining)))}"
        except Exception:
            status = "✅ Prêt"
        cd_lines.append(f"**{cmd.upper()}** : {status}")

    embed.add_field(
        name="⏱️ Cooldowns",
        value="\n".join(cd_lines) if cd_lines else "Aucun",
        inline=False
    )

    embed.add_field(
        name="🗺️ Zones débloquées",
        value=", ".join(player_data.get("unlocked_zones", ["1"])),
        inline=False
    )

    return embed
