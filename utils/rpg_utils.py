async def create_profile_if_not_exists(user_id: int, username: str):
    """
    Crée un profil RPG si le joueur n'existe pas encore.
    Met à jour le pseudo Discord si nécessaire.
    
    Args:
        user_id (int): ID Discord du joueur
        username (str): pseudo Discord
    """
    try:
        res = supabase.table("rpg_players").select("*").eq("user_id", user_id).execute()
        now = datetime.utcnow()

        if not res.data:
            # Profil inexistant → création
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
                "zone": "1",
                "stats": stats,
                "cooldowns": cooldowns,
                "unlocked_zones": ["1"]
            }).execute()

            print(f"✅ Profil créé pour {user_id} ({username})")

        else:
            # Profil existant → mise à jour du pseudo si changé
            player = res.data[0]
            if player.get("username") != username:
                supabase.table("rpg_players").update({"username": username}).eq("user_id", user_id).execute()
                print(f"ℹ️ Pseudo mis à jour pour {user_id} → {username}")

    except Exception as e:
        print(f"⚠️ Erreur lors de la création ou mise à jour du profil pour {user_id} : {e}")
