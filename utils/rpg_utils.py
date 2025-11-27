# ────────────────────────────────────────────────────────────────────────────────
# 📌 rpg_utils.py — Utilitaires RPG pour le bot
# Objectif : Créer et gérer les profils des joueurs dans la table Supabase
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import asyncio
from datetime import datetime, timedelta
from utils.supabase_client import supabase  # ✅ Correct comme dans reiatsuprofil.py

# ────────────────────────────────────────────────────────────────────────────────
# 🔹 Création / Vérification de profil
# ────────────────────────────────────────────────────────────────────────────────
async def create_profile_if_not_exists(user_id: int, username: str = None):
    """
    Crée un profil RPG si le joueur n'existe pas encore avec stats, cooldowns et zones débloquées.
    
    Args:
        user_id (int): ID Discord du joueur
        username (str): pseudo Discord (optionnel)
    """
    try:
        data = supabase.table("rpg_players").select("*").eq("user_id", user_id).execute()
        if not data.data:
            now = datetime.utcnow()
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
                "username": username or str(user_id),  # stocke le pseudo ou fallback sur l'ID
                "zone": "1",
                "stats": stats,
                "cooldowns": cooldowns,
                "unlocked_zones": ["1"]
            }).execute()

            print(f"✅ Profil créé pour l'utilisateur {user_id} ({username})")
        else:
            print(f"ℹ️ Profil déjà existant pour l'utilisateur {user_id} ({username})")
    except Exception as e:
        print(f"⚠️ Erreur lors de la création du profil pour {user_id} : {e}")
