# ────────────────────────────────────────────────────────────────────────────────
# 📌 rpg_classes.py — Gestion des classes RPG, bonus et effets
# Objectif : Fournir les bonus de classe et talents pour le leveling et le combat
# ────────────────────────────────────────────────────────────────────────────────

CLASSES = {
    "TANK": {
        "base": {"hp": 30, "def": 5, "atk": 0, "dex": 0, "eva": 0, "crit": 0, "sp": 0},
        "level_up": {"hp": 8, "def": 2, "atk": 1, "dex": 0, "eva": 0, "crit": 0, "sp": 0},
        "talent": "peau_d_acier",
        "effects": {"reduce_damage_percent": 10}  # Réduit tous les dégâts subis de 10%
    },
    "BERSERKER": {
        "base": {"hp": 0, "def": 0, "atk": 5, "dex": 0, "eva": 0, "crit": 5, "sp": 0},
        "level_up": {"hp": 3, "def": 0, "atk": 3, "dex": 0, "eva": 0, "crit": 1, "sp": 0},
        "talent": "rage_sanglante",
        "effects": {"atk_bonus_below_50": 10}  # +10% ATK si HP <50%
    },
    "ASSASSIN": {
        "base": {"hp": 0, "def": 0, "atk": 1, "dex": 5, "eva": 5, "crit": 0, "sp": 0},
        "level_up": {"hp": 1, "def": 0, "atk": 1, "dex": 2, "eva": 2, "crit": 0, "sp": 0},
        "talent": "frappe_eclair",
        "effects": {"double_attack_chance": 15}  # +15% chance de double attaque
    },
    "STRATEGIST": {
        "base": {"hp": 0, "def": 0, "atk": 1, "dex": 2, "eva": 0, "crit": 10, "sp": 0},
        "level_up": {"hp": 1, "def": 0, "atk": 1, "dex": 1, "eva": 0, "crit": 2, "sp": 0},
        "talent": "coup_precis",
        "effects": {"crit_multiplier": 1.4}  # coups critiques infligent +40% de dégâts
    },
    "SPIRITUALIST": {
        "base": {"hp": 0, "def": 0, "atk": 0, "dex": 0, "eva": 0, "crit": 3, "sp": 20},
        "level_up": {"hp": 0, "def": 0, "atk": 1, "dex": 1, "eva": 0, "crit": 1, "sp": 10},
        "talent": "reiatsu_instable",
        "effects": {"chance_block_damage": 10}  # 10% chance d'annuler les dégâts
    },
    "HYBRID": {
        "base": {"hp": 10, "def": 0, "atk": 2, "dex": 0, "eva": 2, "crit": 0, "sp": 0},
        "level_up": {"hp": 2, "def": 0, "atk": 1, "dex": 0, "eva": 1, "crit": 1, "sp": 0},
        "talent": "instinct_hollow",
        "effects": {"lifesteal_percent": 5}  # soigne 5% des dégâts infligés
    }
}

# ────────────────────────────────────────────────────────────────────────────────
# Fonctions d'application des bonus et talents
# ────────────────────────────────────────────────────────────────────────────────

def apply_class_base(stats: dict, class_name: str) -> dict:
    """Applique les bonus de base de la classe au joueur."""
    cls = CLASSES.get(class_name.upper())
    if not cls:
        return stats
    for k, v in cls["base"].items():
        stats[k] = stats.get(k, 0) + v
    # Ajouter les effets au stats
    stats["effects"] = cls.get("effects", {})
    return stats

def apply_class_levelup(stats: dict, class_name: str) -> dict:
    """Applique les bonus de level-up de la classe au joueur."""
    cls = CLASSES.get(class_name.upper())
    if not cls:
        return stats
    for k, v in cls["level_up"].items():
        stats[k] = stats.get(k, 0) + v
    return stats

def get_class_effects(class_name: str) -> dict:
    """Retourne les effets de la classe pour le combat."""
    cls = CLASSES.get(class_name.upper())
    return cls.get("effects", {}) if cls else {}
