# ────────────────────────────────────────────────────────────────────────────────
# 📌 init_db.py
# Objectif : Initialiser la base SQLite locale Reiatsu (Bleach)
# Catégorie : 🧠 Utils
# Accès : Tous
# Cooldown : /
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import os
import sqlite3

# ────────────────────────────────────────────────────────────────────────────────
# 🗄️ Configuration SQLite
# ────────────────────────────────────────────────────────────────────────────────
DB_DIR = "database"
REIATSU_DB_PATH = os.path.join(DB_DIR, "reiatsu.db")

os.makedirs(DB_DIR, exist_ok=True)


def get_conn():
    """Retourne une connexion SQLite vers reiatsu.db"""
    return sqlite3.connect(REIATSU_DB_PATH)


# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Initialisation des tables
# ────────────────────────────────────────────────────────────────────────────────
def init_db():
    """Crée les tables Reiatsu si elles n'existent pas."""

    conn = get_conn()
    cursor = conn.cursor()

    # ─── Table reiatsu ─────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reiatsu (
        user_id INTEGER PRIMARY KEY,
        username TEXT NOT NULL,
        points INTEGER DEFAULT 0,
        bonus5 INTEGER DEFAULT 0,
        last_steal_attempt TEXT,
        steal_cd INTEGER,
        classe TEXT DEFAULT '',
        last_skilled_at TEXT,
        active_skill INTEGER DEFAULT 0,
        fake_spawn_id INTEGER,
        fake_spawn_guild_id INTEGER,
        niveau INTEGER DEFAULT 0,
        quetes TEXT DEFAULT '[]',
        shop_effets TEXT DEFAULT '[]'
    )
    """)

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_reiatsu_user_id
    ON reiatsu(user_id)
    """)


    # ─── Table reiatsu_config ──────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reiatsu_config (
        guild_id INTEGER PRIMARY KEY,
        channel_id INTEGER,
        is_spawn INTEGER DEFAULT 0,
        message_id INTEGER,
        spawn_speed TEXT,
        last_spawn_at TEXT,
        spawn_delay INTEGER
    )
    """)

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_reiatsu_config_guild
    ON reiatsu_config(guild_id)
    """)


    # ─── Table mots_trouves ────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS mots_trouves (
        user_id INTEGER PRIMARY KEY,
        username TEXT NOT NULL,
        mots TEXT DEFAULT '[]',
        last_found_at TEXT
    )
    """)

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_mots_user_id
    ON mots_trouves(user_id)
    """)

    # ─── Table steam_keys ────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS steam_keys (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        game_name TEXT NOT NULL,
        steam_url TEXT NOT NULL,
        steam_key TEXT NOT NULL,
        won INTEGER NOT NULL DEFAULT 0,
        winner TEXT
    )
    """)
    
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_steam_keys_won
    ON steam_keys(won)
    """)    



    # ─── Table rpg_players ────────────────────────────────────────────────────
    # Équivalent SQLite du schéma Supabase :
    #   user_id BIGINT PK, zone INT default 13, stats JSONB, cooldowns JSONB,
    #   effects JSONB, unlocked_zones JSONB default '["1"]',
    #   username TEXT default 'Inconnu', class TEXT
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS rpg_players (
        user_id         INTEGER PRIMARY KEY,
        username        TEXT    NOT NULL DEFAULT 'Inconnu',
        class           TEXT,
        zone            INTEGER NOT NULL DEFAULT 13,
        stats           TEXT    NOT NULL DEFAULT '{}',
        cooldowns       TEXT    NOT NULL DEFAULT '{}',
        effects         TEXT    NOT NULL DEFAULT '{}',
        unlocked_zones  TEXT    NOT NULL DEFAULT '["1"]'
    )
    """)
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_rpg_players_user_id
    ON rpg_players(user_id)
    """)

    # ─── Table gardens ────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS gardens (
        user_id         INTEGER PRIMARY KEY,
        username        TEXT    NOT NULL,
        garden_grid     TEXT    NOT NULL DEFAULT '[]',
        inventory       TEXT    NOT NULL DEFAULT '{}',
        argent          INTEGER NOT NULL DEFAULT 0,
        last_fertilize  TEXT
    )
    """)

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_gardens_user_id
    ON gardens(user_id)
    """)


    # ─── Table config ─────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS config (
        key   TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    """)    
    
    

    conn.commit()
    conn.close()


# ────────────────────────────────────────────────────────────────────────────────
# 🔹 Si lancé directement
# ────────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    print(f"✅ Base Reiatsu initialisée : {REIATSU_DB_PATH}")
