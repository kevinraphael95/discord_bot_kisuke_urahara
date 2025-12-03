# ────────────────────────────────────────────────────────────────────────────────
# 📌 rpg_utils.py — Utilitaires RPG pour le bot
# Objectif : Créer et gérer les profils des joueurs dans la table Supabase
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import asyncio
from datetime import datetime, timedelta
from utils.supabase_client import supabase

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
        res = supabase.table("rpg_players").select("*").eq("user_id", user_id).execute()
        now = datetime.utcnow()

        if not res.data:
            stats = {
                "level": 1,
                "xp": 0,
                "xp_next": 100,
                "hp": 100,
                "hp_max": 100,
                "sp": 50,
                "atk": 10,
                "def": 5,
                "dex": 5,
                "crit": 5,
                "eva": 5,
                "equipment": {},
                "effects": {}
            }

            cooldowns = {
                "combat": (now - timedelta(minutes=5)).isoformat(),
                "boss": (now - timedelta(hours=1)).isoformat()
            }

            supabase.table("rpg_players").insert({
                "user_id": user_id,
                "username": username,
                "class": "Aucun",
                "zone": 1,
                "stats": stats,
                "cooldowns": cooldowns,
                "effects": {},
                "unlocked_zones": ["1"]
            }).execute()

            print(f"✅ Profil créé pour {user_id} ({username})")

        else:
            player = res.data[0]
            if player.get("username") != username:
                supabase.table("rpg_players").update({"username": username}).eq("user_id", user_id).execute()
                print(f"ℹ️ Pseudo mis à jour pour {user_id} → {username}")

    except Exception as e:
        print(f"⚠️ Erreur lors de la création ou mise à jour du profil pour {user_id} : {e}")

# ────────────────────────────────────────────────────────────────────────────────
# 🔹 Mise à jour des stats
# ────────────────────────────────────────────────────────────────────────────────
async def update_player_stats(user_id: int, stats: dict, cooldowns: dict):
    """Met à jour les stats et cooldowns du joueur dans Supabase"""
    try:
        supabase.table("rpg_players").update({
            "stats": stats,
            "cooldowns": cooldowns
        }).eq("user_id", user_id).execute()
    except Exception as e:
        print(f"⚠️ Impossible de mettre à jour les stats pour {user_id} : {e}")
