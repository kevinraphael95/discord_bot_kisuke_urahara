# ────────────────────────────────────────────────────────────────────────────────
# 📌 save_tunnel_url.py
# Objectif : Capturer l'URL du tunnel Cloudflare et la stocker en base SQLite
# Catégorie : Système
# Accès : Interne (appelé par start.sh)
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import subprocess
import re
import sys
import time
import os

# S'assurer que la racine du bot est dans le path Python
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.init_db import get_conn

# ────────────────────────────────────────────────────────────────────────────────
# 🗄️ Accès base de données locale
# ────────────────────────────────────────────────────────────────────────────────

def save_tunnel_url(url: str):
    """Stocke ou met à jour l'URL du tunnel dans la table config."""
    conn   = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO config (key, value) VALUES ('tunnel_url', ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
    """, (url,))
    conn.commit()
    conn.close()
    print(f"✅ URL tunnel sauvegardée : {url}")

# ────────────────────────────────────────────────────────────────────────────────
# 🌐 Lancement cloudflared + capture de l'URL
# ────────────────────────────────────────────────────────────────────────────────

def start_tunnel(port: int = 5050):
    """
    Lance cloudflared, capture l'URL trycloudflare.com en temps réel
    et la sauvegarde en base. Reste actif en arrière-plan.
    """
    process = subprocess.Popen(
        ["cloudflared", "tunnel", "--url", f"http://localhost:{port}", "--no-autoupdate"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    url_pattern = re.compile(r"https://[a-zA-Z0-9\-]+\.trycloudflare\.com")
    timeout     = 30
    start_time  = time.time()
    url_found   = False

    print(f"🌐 Démarrage du tunnel Cloudflare sur le port {port}...")

    for line in process.stdout:
        print(line, end="")
        if not url_found:
            match = url_pattern.search(line)
            if match:
                save_tunnel_url(match.group(0))
                url_found = True
        if not url_found and time.time() - start_time > timeout:
            print("⚠️  Timeout : URL du tunnel introuvable.")
            break

    # Garde le processus vivant
    process.wait()


# ────────────────────────────────────────────────────────────────────────────────
# 🔹 Point d'entrée
# ────────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5050
    start_tunnel(port)
