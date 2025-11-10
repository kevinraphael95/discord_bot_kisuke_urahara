# ────────────────────────────────────────────────────────────────────────────────
# 📦 shop_utils.py — Gestion des objets du ReiatsuShop et persistance des effets
# ────────────────────────────────────────────────────────────────────────────────

import json
import os
from datetime import datetime, timedelta
from utils.supabase_client import supabase

SHOP_DATA_PATH = os.path.join("data", "shop_items.json")

# ────────────────────────────────────────────────────────────────────────────────
# 📂 Chargement du shop
# ────────────────────────────────────────────────────────────────────────────────
def load_shop_items():
    with open(SHOP_DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

# ────────────────────────────────────────────────────────────────────────────────
# 🧩 Gestion des effets en base Supabase
# ────────────────────────────────────────────────────────────────────────────────
def add_shop_effect(guild_id, user_id, effect_key, applied_by, duration):
    start = datetime.utcnow()
    end = start + timedelta(seconds=duration)
    data = {
        "guild_id": str(guild_id),
        "user_id": str(user_id),
        "effect_key": effect_key,
        "applied_by": str(applied_by),
        "start_time": start.isoformat(),
        "end_time": end.isoformat(),
        "active": True
    }
    supabase.table("shop_effects").insert(data).execute()

def get_active_effects(user_id):
    result = supabase.table("shop_effects").select("*").eq("user_id", str(user_id)).eq("active", True).execute()
    return result.data or []

def clean_expired_effects():
    now = datetime.utcnow().isoformat()
    supabase.table("shop_effects").update({"active": False}).lt("end_time", now).execute()
