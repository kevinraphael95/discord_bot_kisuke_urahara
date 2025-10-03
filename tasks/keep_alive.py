# ────────────────────────────────────────────────────────────────────────────────
# 📌 keep_alive.py — Serveur Flask + self-ping
# Objectif : Maintenir le bot en ligne sur Render / Replit
# Catégorie : Task
# Accès : Interne
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────

import os
import asyncio
from threading import Thread
from flask import Flask
import aiohttp

# ────────────────────────────────────────────────────────────────────────────────
# 🌐 Serveur Flask
# ────────────────────────────────────────────────────────────────────────────────

app = Flask("")

@app.route("/")
def home():
    return "Bot en ligne ! 🚀"

def run_flask():
    port = int(os.environ.get("PORT", 8080))  # Render fournit $PORT
    app.run(host="0.0.0.0", port=port)


# ────────────────────────────────────────────────────────────────────────────────
# 🔄 Keep Alive principal
# ────────────────────────────────────────────────────────────────────────────────

def keep_alive():
    """Lance Flask + self-ping périodique."""
    Thread(target=run_flask, daemon=True).start()
    print("[KEEP_ALIVE] Serveur Flask démarré.")

    async def ping_loop():
        ping_url = os.environ.get("PING_URL")  # tu mets ton URL Render dans .env
        if not ping_url:
            print("[KEEP_ALIVE] ⚠️ Pas d'URL définie dans PING_URL → pas de self-ping.")
            return

        async with aiohttp.ClientSession() as session:
            while True:
                try:
                    async with session.get(ping_url) as resp:
                        print(f"[KEEP_ALIVE] Ping {ping_url} → {resp.status}")
                except Exception as e:
                    print(f"[KEEP_ALIVE] Erreur ping : {e}")
                await asyncio.sleep(300)  # 5 minutes

    # lancer le self-ping en arrière-plan
    asyncio.get_event_loop().create_task(ping_loop())
    print("[KEEP_ALIVE] Self-ping activé.")
