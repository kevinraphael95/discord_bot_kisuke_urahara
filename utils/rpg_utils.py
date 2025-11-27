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
async def create_profile_if_not_exists(user_id: int):
    """
    Crée un profil RPG si le joueur n'existe pas encore avec stats et cooldowns.
    
    Args:
        user_id (int): ID Discord du joueur
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
                "hp_max": 100,  # 🆕 Valeur max des PV
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
                "combat": (now - timedelta(minutes=5)).isoformat(),  # prêt immédiatement
                "boss": (now - timedelta(hours=1)).isoformat()       # prêt immédiatement
            }
            supabase.table("rpg_players").insert({
                "user_id": user_id,
                "zone": "1",
                "stats": stats,
                "cooldowns": cooldowns,
                "defeated_bosses": []
            }).execute()
            print(f"✅ Profil créé pour l'utilisateur {user_id}")
        else:
            print(f"ℹ️ Profil déjà existant pour l'utilisateur {user_id}")
    except Exception as e:
        print(f"⚠️ Erreur lors de la création du profil pour {user_id} : {e}")
