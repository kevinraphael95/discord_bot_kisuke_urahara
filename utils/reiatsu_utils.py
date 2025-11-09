# ────────────────────────────────────────────────────────────────────────────────
# 📌 reiatsu_utils.py — Fonctions utilitaires pour les profils Reiatsu
# Objectif : Centraliser la création et vérification des profils joueurs
# Catégorie : Utils
# Accès : Tous
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
from utils.supabase_client import supabase
import datetime

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
    res = supabase.table("reiatsu").select("*").eq("user_id", user_id).execute()

    if res.data:
        return res.data[0]

    # Création automatique
    now_iso = datetime.datetime.utcnow().isoformat()
    profile = {
        "user_id": user_id,
        "username": username,
        "points": 0,
        "classe": None,
        "active_skill": False,
        "last_skilled_at": None,
        "last_steal_attempt": None,
        "steal_cd": 24,
        "niveau": 0,
        "quetes": []
    }
    supabase.table("reiatsu").insert(profile).execute()
    return profile

# ────────────────────────────────────────────────────────────────────────────────
# 🔹 Vérifie si le joueur a choisi une classe
# ────────────────────────────────────────────────────────────────────────────────
def has_class(profile: dict) -> bool:
    """Retourne True si le joueur a choisi une classe Reiatsu."""
    return profile.get("classe") is not None

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

    import datetime
    now = datetime.datetime.utcnow()
    try:
        last_dt = datetime.datetime.fromisoformat(last_skill)
        elapsed = (now - last_dt).total_seconds() / 3600
        remaining = max(0, cooldown_h - elapsed)
        return remaining
    except Exception:
        return cooldown_h
