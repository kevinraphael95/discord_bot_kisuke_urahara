# ────────────────────────────────────────────────────────────────────────────────
# 📌 start.sh
# Objectif : Lancer le bot Discord + Cloudflare Tunnel
# Catégorie : Système
# Accès : Admin / Local
# Cooldown : Aucun
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# ⚙️ Configuration
# ────────────────────────────────────────────────────────────────────────────────
ADMIN_PORT=5050

# ────────────────────────────────────────────────────────────────────────────────
# 🚀 Initialisation
# ────────────────────────────────────────────────────────────────────────────────
echo "════════════════════════════════════════"
echo "  KISUKE BOT — DÉMARRAGE"
echo "════════════════════════════════════════"

# ────────────────────────────────────────────────────────────────────────────────
# 🌐 Vérification / Installation de Cloudflared
# ────────────────────────────────────────────────────────────────────────────────
if ! command -v cloudflared &> /dev/null; then
  echo "⚠️  cloudflared non trouvé. Installation..."

  # Installation via Termux (ARM)
  pkg install cloudflared -y 2>/dev/null || \

  # Installation manuelle (ARM64)
  wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64 -O cloudflared && \
  chmod +x cloudflared && \
  mv cloudflared $PREFIX/bin/
fi

# ────────────────────────────────────────────────────────────────────────────────
# 🗄️ Initialisation de la base de données
# ────────────────────────────────────────────────────────────────────────────────
echo "🗄️  Initialisation de la base de données..."
python -c "from database.init_db import init_db; init_db()"

# ────────────────────────────────────────────────────────────────────────────────
# 🔗 Lancement du Tunnel Cloudflare + sauvegarde URL en base
# ────────────────────────────────────────────────────────────────────────────────
echo "🌐 Lancement de Cloudflare Tunnel sur le port $ADMIN_PORT..."
python save_tunnel_url.py $ADMIN_PORT &
TUNNEL_PID=$!

# Attente que l'URL soit capturée et sauvegardée
sleep 5

echo ""
echo "✅ Tunnel actif — URL sauvegardée en base de données"
echo ""

# ────────────────────────────────────────────────────────────────────────────────
# 🤖 Lancement du Bot Discord
# ────────────────────────────────────────────────────────────────────────────────
echo "🤖 Lancement du bot..."
python bot.py

# ────────────────────────────────────────────────────────────────────────────────
# 🧹 Nettoyage à la fermeture
# ────────────────────────────────────────────────────────────────────────────────
kill $TUNNEL_PID 2>/dev/null
