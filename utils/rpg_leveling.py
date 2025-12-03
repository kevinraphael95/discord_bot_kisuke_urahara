# ────────────────────────────────────────────────────────────────────────────────
# 📌 rpg_leveling.py — Gestion du leveling RPG et progression des stats
# Objectif : Monter les joueurs de niveau selon leur XP et appliquer les bonus
# ────────────────────────────────────────────────────────────────────────────────

from utils.rpg_classes import apply_class_levelup

# Progression de stats de base par level (pour normaliser le scaling)
BASE_STATS = {
    "hp_max": [100, 110, 120, 135, 150, 170, 190, 215, 240, 270],
    "atk": [10, 12, 14, 16, 18, 20, 23, 26, 29, 32],
    "def": [5, 6, 7, 8, 9, 10, 11, 12, 13, 14],
    "dex": [5, 5, 6, 6, 7, 7, 8, 8, 9, 9],
    "eva": [5, 5, 6, 6, 7, 7, 8, 8, 9, 9],
    "crit": [5, 5, 6, 6, 7, 7, 8, 8, 9, 9],
    "sp": [50, 50, 50, 50, 50, 50, 50, 50, 50, 50],
    "xp_next": [100, 150, 225, 340, 510, 760, 1140, 1710, 2570, 3850]
}

def level_up_player(stats: dict, class_name: str) -> dict:
    """Monte le joueur de niveau si XP atteint et applique les bonus de classe."""
    level = stats.get("level", 1)
    xp = stats.get("xp", 0)

    while level < 10 and xp >= BASE_STATS["xp_next"][level-1]:
        xp -= BASE_STATS["xp_next"][level-1]
        level += 1

        # Appliquer stats de base pour le nouveau level
        for stat in ["hp_max", "atk", "def", "dex", "eva", "crit", "sp"]:
            stats[stat] = BASE_STATS[stat][level-1]

        # Appliquer bonus de classe
        stats = apply_class_levelup(stats, class_name)

        stats["level"] = level

    stats["xp"] = xp
    stats["xp_next"] = BASE_STATS["xp_next"][level-1] if level < 10 else None
    stats["hp"] = stats.get("hp_max", stats.get("hp",100))
    return stats
