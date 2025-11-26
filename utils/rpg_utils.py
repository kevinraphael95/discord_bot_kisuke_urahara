# utils/rpg_utils.py
import asyncio
from supabase_client import supabase

async def create_profile_if_not_exists(user_id: int):
    """Crée un profil si le joueur n'existe pas encore"""
    data = supabase.table("rpg_players").select("*").eq("user_id", user_id).execute()
    if not data.data:
        supabase.table("rpg_players").insert({
            "user_id": user_id,
        }).execute()
