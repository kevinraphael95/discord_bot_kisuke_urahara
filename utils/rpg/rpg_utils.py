# ────────────────────────────────────────────────────────────────────────────────
# 📌 rpg_utils.py — Utilitaires RPG pour le bot
# Objectif : Créer et gérer les profils des joueurs dans la table SQLite
# ────────────────────────────────────────────────────────────────────────────────

import sqlite3
import json
import os
from datetime import datetime, timedelta

DB_PATH = os.path.join("database", "reiatsu.db")

def get_conn():
    return sqlite3.connect(DB_PATH)

# ────────────────────────────────────────────────────────────────────────────────
# 🔹 Helpers JSON
# ────────────────────────────────────────────────────────────────────────────────
def _row_to_dict(cursor, row) -> dict:
    """Convertit une row SQLite en dict avec désérialisation JSON automatique."""
    data = dict(zip([d[0] for d in cursor.description], row))
    for field in ("stats", "cooldowns", "unlocked_zones", "inventory", "effects"):
        if field in data and isinstance(data[field], str):
            try:
                data[field] = json.loads(data[field])
            except Exception:
                data[field] = {} if field != "unlocked_zones" else ["1"]
    return data

# ────────────────────────────────────────────────────────────────────────────────
# 🔹 Création / Vérification de profil
# ────────────────────────────────────────────────────────────────────────────────
async def create_profile_if_not_exists(user_id: int, username: str):
    """
    Crée un profil RPG si le joueur n'existe pas encore.
    Met à jour le pseudo Discord si nécessaire.
    """
    try:
        user_id = int(user_id)
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT username FROM rpg_players WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()

        now = datetime.utcnow()

        if not row:
            stats = {
                "level": 1, "xp": 0, "xp_next": 100,
                "hp": 100, "hp_max": 100, "sp": 50,
                "atk": 10, "def": 5, "dex": 5,
                "crit": 5, "eva": 5,
                "equipment": {}, "effects": {}
            }
            cooldowns = {
                "combat": (now - timedelta(minutes=5)).isoformat(),
                "boss":   (now - timedelta(hours=1)).isoformat()
            }
            cursor.execute("""
                INSERT INTO rpg_players
                    (user_id, username, class, zone, stats, cooldowns, effects, unlocked_zones)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id, username, "Aucun", 1,
                json.dumps(stats),
                json.dumps(cooldowns),
                json.dumps({}),
                json.dumps(["1"])
            ))
            conn.commit()
            print(f"✅ Profil RPG créé pour {user_id} ({username})")
        else:
            if row[0] != username:
                cursor.execute(
                    "UPDATE rpg_players SET username = ? WHERE user_id = ?",
                    (username, user_id)
                )
                conn.commit()
                print(f"ℹ️ Pseudo RPG mis à jour pour {user_id} → {username}")

        conn.close()

    except Exception as e:
        print(f"⚠️ Erreur création/mise à jour profil RPG pour {user_id} : {e}")

# ────────────────────────────────────────────────────────────────────────────────
# 🔹 Mise à jour des stats
# ────────────────────────────────────────────────────────────────────────────────
async def update_player_stats(user_id: int, stats: dict, cooldowns: dict):
    """Met à jour les stats et cooldowns du joueur dans SQLite."""
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE rpg_players SET stats = ?, cooldowns = ? WHERE user_id = ?",
            (json.dumps(stats), json.dumps(cooldowns), user_id)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"⚠️ Impossible de mettre à jour les stats RPG pour {user_id} : {e}")
