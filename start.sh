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

# Se placer dans le dossier du script (racine du bot)
cd "$(dirname "$0")"

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
  pkg install cloudflared -y 2>/dev/null || \
  wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64 -O cloudflared && \
  chmod +x cloudflared && \
  mv cloudflared $PREFIX/bin/
fi

# ────────────────────────────────────────────────────────────────────────────────
# 🗄️ Initialisation de la base de données
# ────────────────────────────────────────────────────────────────────────────────
echo "🗄️  Initialisation de la base de données..."
PYTHONPATH=. python -c "from utils.init_db import init_db; init_db(); print('✅ Base initialisée')"

# ────────────────────────────────────────────────────────────────────────────────
# 🔗 Lancement du Tunnel Cloudflare + sauvegarde URL en base
# ────────────────────────────────────────────────────────────────────────────────
echo "🌐 Lancement de Cloudflare Tunnel sur le port $ADMIN_PORT..."
PYTHONPATH=. python admin/save_tunnel_url.py $ADMIN_PORT &
TUNNEL_PID=$!

# Attente que l'URL soit capturée et sauvegardée
sleep 5

echo ""
echo "✅ Tunnel actif — URL sauvegardée en base de données"
echo ""

# ────────────────────────────────────────────────────────────────────────────────
# 🤖 Lancement du Bot Discord
# ────────────────────────────────────────────────────────────────────────────────
# setsid + nohup détachent complètement le bot de ce terminal : fermer
# Termux (ou cette session bash) ne tue plus le bot, que tu aies lancé
# start.sh toi-même à la main ou via le bouton /bot_control.
# Les logs partent dans bot.log au lieu de s'afficher directement ici —
# utilise `tail -f bot.log` pour les voir en direct depuis n'importe
# quelle session Termux.
echo "🤖 Lancement du bot (détaché, logs dans bot.log)..."
setsid nohup python bot.py > bot.log 2>&1 < /dev/null &
disown
BOT_PID=$!

echo ""
echo "✅ Bot lancé en arrière-plan (PID $BOT_PID)"
echo "📄 Logs : tail -f bot.log"
echo ""

# ────────────────────────────────────────────────────────────────────────────────
# 🧹 Note
# ────────────────────────────────────────────────────────────────────────────────
# Le bot et le tunnel tournent maintenant indépendamment de ce script :
# start.sh peut se terminer (ou le terminal se fermer) sans les couper.
