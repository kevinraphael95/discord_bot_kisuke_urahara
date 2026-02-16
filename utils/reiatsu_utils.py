# ────────────────────────────────────────────────────────────────────────────────
# 📌 reiatsu_utils.py — Fonctions utilitaires pour les profils Reiatsu
# Objectif : Centraliser la création et vérification des profils joueurs
# Catégorie : Utils
# Accès : Tous
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import sqlite3
import os
import datetime
import json

# ────────────────────────────────────────────────────────────────────────────────
# 🗄️ Configuration SQLite
# ────────────────────────────────────────────────────────────────────────────────
DB_PATH = os.path.join("database", "reiatsu.db")


def get_conn():
    """Retourne une connexion SQLite vers reiatsu.db"""
    return sqlite3.connect(DB_PATH)


# ────────────────────────────────────────────────────────────────────────────────
# 🔹 Création d’un profil joueur si inexistant
# ────────────────────────────────────────────────────────────────────────────────
def ensure_profile(user_id: int, username: str) -> dict:
    """
    Vérifie si un joueur a un profil Reiatsu.
    Si non, le crée automatiquement et renvoie le profil.

    Returns:
        dict : Profil joueur
    """

    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM reiatsu WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()

    # ─── Profil existant ───────────────────────────
    if row:
        columns = [column[0] for column in cursor.description]
        profile = dict(zip(columns, row))

        # Conversion JSON stocké en TEXT
        profile["quetes"] = json.loads(profile.get("quetes") or "[]")
        profile["shop_effets"] = json.loads(profile.get("shop_effets") or "[]")

        conn.close()
        return profile

    # ─── Création automatique ──────────────────────
    cursor.execute("""
        INSERT INTO reiatsu (
            user_id,
            username,
            points,
            bonus5,
            last_steal_attempt,
            steal_cd,
            classe,
            last_skilled_at,
            active_skill,
            fake_spawn_id,
            fake_spawn_guild_id,
            niveau,
            quetes,
            shop_effets
        )
        VALUES (?, ?, 0, 0, NULL, 24, '', NULL, 0, NULL, NULL, 0, '[]', '[]')
    """, (user_id, username))

    conn.commit()
    conn.close()

    return {
        "user_id": user_id,
        "username": username,
        "points": 0,
        "bonus5": 0,
        "classe": "",
        "active_skill": 0,
        "last_skilled_at": None,
        "last_steal_attempt": None,
        "steal_cd": 24,
        "fake_spawn_id": None,
        "fake_spawn_guild_id": None,
        "niveau": 0,
        "quetes": [],
        "shop_effets": []
    }


# ────────────────────────────────────────────────────────────────────────────────
# 🔹 Vérifie si le joueur a choisi une classe
# ────────────────────────────────────────────────────────────────────────────────
def has_class(profile: dict) -> bool:
    """Retourne True si le joueur a choisi une classe Reiatsu."""
    return bool(profile.get("classe"))


# ────────────────────────────────────────────────────────────────────────────────
# 🔹 Récupère le cooldown restant d’un skill
# ────────────────────────────────────────────────────────────────────────────────
def get_skill_cooldown(profile: dict, classe_config: dict) -> float:
    """
    Calcule le cooldown restant en heures pour le skill du joueur.
    Retourne 0 si le skill est prêt.
    """

    cooldown_h = classe_config.get("Cooldown", 12)
    last_skill = profile.get("last_skilled_at")

    if not last_skill:
        return 0

    try:
        now = datetime.datetime.utcnow()
        last_dt = datetime.datetime.fromisoformat(last_skill)
        elapsed = (now - last_dt).total_seconds() / 3600
        remaining = max(0, cooldown_h - elapsed)
        return remaining
    except Exception:
        return cooldown_h
