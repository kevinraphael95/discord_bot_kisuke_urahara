#!/bin/bash
# ────────────────────────────────────────────────────────────────────────────────
# start.sh — Lance le bot Discord + Cloudflare Tunnel
# Usage : bash start.sh
# ────────────────────────────────────────────────────────────────────────────────

ADMIN_PORT=5050

echo "════════════════════════════════════════"
echo "  KISUKE BOT — DÉMARRAGE"
echo "════════════════════════════════════════"

# Vérifier cloudflared
if ! command -v cloudflared &> /dev/null; then
  echo "⚠️  cloudflared non trouvé. Installation..."
  # Termux (ARM)
  pkg install cloudflared -y 2>/dev/null || \
  wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64 -O cloudflared && \
  chmod +x cloudflared && mv cloudflared $PREFIX/bin/
fi

echo "🌐 Lancement de Cloudflare Tunnel sur port $ADMIN_PORT..."
cloudflared tunnel --url http://localhost:$ADMIN_PORT --no-autoupdate 2>&1 | grep -E "https://" &
TUNNEL_PID=$!

# Attendre que le tunnel soit prêt
sleep 3
echo ""
echo "✅ Tunnel actif — cherche l'URL https://*.trycloudflare.com ci-dessus"
echo ""

# Lancer le bot
echo "🤖 Lancement du bot..."
python bot.py

# Cleanup
kill $TUNNEL_PID 2>/dev/null
