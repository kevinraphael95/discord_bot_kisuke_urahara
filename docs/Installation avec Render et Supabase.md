# Installer avec Render, Supabase et Self-Ping

# 1️⃣ Discord

1. [Discord Developer Portal](https://discord.com/developers/applications) → **New Application**
2. Note **APPLICATION ID**
3. Bot → **Reset Token** → copie **BOT TOKEN**

> Ces deux infos vont dans le `.env`.

---

# 2️⃣ Supabase

1. Crée un projet sur [Supabase](https://supabase.com/)
2. Crée les tables via [LES SCRIPTS SQL](SQL_des_tables_supabase.md)
3. Note pour le `.env` :

   * `SUPABASE_URL` → `Project Settings → Data API → Project URL`
   * `SUPABASE_KEY` → `Project Settings → API Keys → Publishable Keys ou Secret Keys`

---

# 3️⃣ Webhook de redeploy Render

1. Render → ton service → **Settings → Build & Deploy → Deploy Hooks → Create Deploy Hook**
2. Copie l’URL → ce sera `RENDER_REDEPLOY_WEBHOOK` dans le `.env`

> Permet de redéployer le bot depuis Discord.

---

# 4️⃣ Fichier `.env`

```env
# --- Discord ---
COMMAND_PREFIX=!!
DISCORD_APP_ID=TON_APPLICATION_ID
DISCORD_TOKEN=TON_BOT_TOKEN

# --- Supabase ---
SUPABASE_URL=TON_URL_SUPABASE
SUPABASE_KEY=TA_CLE_API_SUPABASE

# --- Render ---
PING_URL=https://ton-bot.onrender.com/
RENDER_REDEPLOY_WEBHOOK=https://api.render.com/deploy/srv-xxxxxx?key=yyyyyyyy
```

> **Explications** :
>
> * `COMMAND_PREFIX` → préfixe des commandes (`!`, `!!`)
> * `DISCORD_APP_ID` / `DISCORD_TOKEN` → connexion Discord
> * `SUPABASE_URL` / `SUPABASE_KEY` → connexion base de données
> * `PING_URL` → self-ping pour rester actif
> * `RENDER_REDEPLOY_WEBHOOK` → redeploy depuis Discord

---

# 5️⃣ Déployer sur Render

1. Render → **New → Web Service** → dépôt GitHub
2. Plan gratuit
3. Startup command : `python bot.py`
4. Environment Variables → copie **toutes les valeurs du `.env`**
