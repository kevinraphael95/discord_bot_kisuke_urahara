# ================================================================================
# 📌 admin_panel.py
# Objectif : Interface web d'administration du bot (DB, logs, actions, backups, .env)
# Les templates (HTML) sont dans templates/, le CSS/JS dans static/.
# ================================================================================

# ================================================================================
# 📦 Imports nécessaires
# ================================================================================
import asyncio
import hmac
import logging
import os
import re
import sqlite3
import subprocess
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timedelta
from functools import wraps

import requests
from io import StringIO

from dotenv import load_dotenv, dotenv_values
from flask import (Flask, render_template, request, redirect, session,
                   jsonify, url_for, send_file, abort)
from flask_limiter import Limiter
from flask_wtf.csrf import CSRFProtect, CSRFError

HERE     = os.path.dirname(os.path.abspath(__file__))
ROOT     = os.path.abspath(os.path.join(HERE, ".."))
ENV_PATH = os.path.join(ROOT, ".env")

load_dotenv(ENV_PATH) or load_dotenv()

from utils.logger import get_logs, LOG_BUFFER

logging.getLogger("werkzeug").setLevel(logging.ERROR)

# ================================================================================
# ⚙️ Config
# ================================================================================
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
SECRET_KEY     = os.getenv("ADMIN_SECRET")
if not ADMIN_PASSWORD:
    raise RuntimeError("❌ ADMIN_PASSWORD manquant dans .env — arrêt du panel")
if not SECRET_KEY:
    raise RuntimeError("❌ ADMIN_SECRET manquant dans .env — arrêt du panel")

DB_PATH    = os.path.join(ROOT, "database", "reiatsu.db")
BACKUP_DIR = os.path.join(ROOT, "database", "backups")
ADMIN_HOST = os.getenv("ADMIN_HOST", "0.0.0.0")   # comme avant (Render a besoin de 0.0.0.0)
SQL_MAX_ROWS = 1000


# Réglages modifiables à chaud (relus à chaque usage depuis os.environ)
def auto_hours() -> float:
    try:
        return max(0.0, float(os.getenv("BACKUP_AUTO_HOURS", "0")))
    except ValueError:
        return 0.0


def max_backups() -> int:
    try:
        return max(1, int(os.getenv("MAX_BACKUPS", "10")))
    except ValueError:
        return 10


def webhook_url() -> str:
    return os.getenv("DISCORD_BACKUP_WEBHOOK_URL", "")


BACKUP_SETTINGS = [
    {"key": "BACKUP_AUTO_HOURS", "label": "Backup automatique (heures)",
     "desc": "0 = désactivé. Exemple : 24 = tous les jours.", "type": "number"},
    {"key": "MAX_BACKUPS", "label": "Backups conservés",
     "desc": "Nombre de copies gardées sur le serveur, les plus anciennes sont supprimées.", "type": "number"},
    {"key": "DISCORD_BACKUP_WEBHOOK_URL", "label": "Webhook Discord",
     "desc": "Chaque backup y est envoyé (8 Mo max). Laisser vide pour ne pas modifier.",
     "type": "text", "sensitive": True},
]

# ================================================================================
# 🌐 App Flask + sécurité (cookies, CSRF, rate limiting)
# ================================================================================
app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = SECRET_KEY
app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    PERMANENT_SESSION_LIFETIME=timedelta(hours=12),
    WTF_CSRF_TIME_LIMIT=None,
    MAX_CONTENT_LENGTH=64 * 1024 * 1024,   # import de backup
)
csrf = CSRFProtect(app)


def client_ip():
    # Derrière le tunnel Cloudflare, remote_addr vaut toujours 127.0.0.1
    return request.headers.get("CF-Connecting-IP") or request.remote_addr or "?"


def _is_local_request():
    return not request.headers.get("CF-Connecting-IP") and \
        request.remote_addr in ("127.0.0.1", "::1", "localhost")


limiter = Limiter(
    client_ip,
    app=app,
    default_limits=["500 per day", "100 per hour"],
    storage_uri="memory://",
    default_limits_exempt_when=_is_local_request,
)


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            if request.path.startswith("/api/"):
                return jsonify({"ok": False, "error": "Non connecté"}), 401
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def body() -> dict:
    return request.get_json(silent=True) or {}


# ================================================================================
# 🗄️ Helpers SQLite
# ================================================================================
@contextmanager
def db():
    """Connexion auto-fermée, commit si tout s'est bien passé."""
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def qi(name: str) -> str:
    """Quote un identifiant SQL (table / colonne)."""
    return '"' + str(name).replace('"', '""') + '"'


def get_all_tables():
    with db() as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
    return [r[0] for r in rows]


def table_info(table):
    """[(cid, name, type, notnull, default, pk), ...]"""
    with db() as conn:
        return conn.execute(f"PRAGMA table_info({qi(table)})").fetchall()


def pk_of(info):
    for col in info:
        if col[5] == 1:
            return col[1]
    return info[0][1]


def safe(v):
    """Rend une cellule sérialisable en JSON (et sans perte pour les IDs Discord)."""
    if isinstance(v, bytes):
        return f"<blob {len(v)} o>"
    if isinstance(v, int) and not isinstance(v, bool) and abs(v) > 2 ** 53:
        return str(v)
    return v


# ================================================================================
# 🔑 Pages + auth
# ================================================================================
@app.route("/")
@login_required
def index():
    return render_template("main.html")


@app.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def login():
    error = None
    if request.method == "POST":
        given = request.form.get("password", "")
        if hmac.compare_digest(given.encode(), ADMIN_PASSWORD.encode()):
            session.clear()
            session["logged_in"] = True
            session.permanent = True
            return redirect(url_for("index"))
        error = "Mot de passe incorrect."
    return render_template("login.html", error=error)


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))


# ================================================================================
# 🗄️ API : tables / édition / SQL
# ================================================================================
@app.route("/api/tables")
@login_required
def api_tables():
    return jsonify({"tables": get_all_tables()})


@app.route("/api/table/<table_name>")
@login_required
def api_table(table_name):
    if table_name not in get_all_tables():
        return jsonify({"error": "Table non autorisée"}), 403
    info = table_info(table_name)
    with db() as conn:
        cur = conn.execute(f"SELECT * FROM {qi(table_name)}")
        columns = [d[0] for d in cur.description]
        rows = [[safe(c) for c in row] for row in cur.fetchall()]
    return jsonify({"columns": columns, "rows": rows, "pk": pk_of(info)})


@app.route("/api/table/<table_name>/delete", methods=["POST"])
@login_required
def api_table_delete(table_name):
    if table_name not in get_all_tables():
        return jsonify({"ok": False, "error": "Table non autorisée"}), 403
    try:
        with db() as conn:
            conn.execute(f"DROP TABLE IF EXISTS {qi(table_name)}")
        print(f"🗑️ Table supprimée : {table_name}")
        return jsonify({"ok": True})
    except Exception as e:
        print(f"❌ Échec suppression table {table_name} : {e}")
        return jsonify({"ok": False, "error": str(e)})


@app.route("/api/edit", methods=["POST"])
@login_required
def api_edit():
    data   = body()
    table  = data.get("table")
    pk     = data.get("pk")
    pk_val = data.get("pk_val")
    col    = data.get("col")
    value  = data.get("value")

    if table not in get_all_tables():
        return jsonify({"ok": False, "error": "Table non autorisée"})

    info  = table_info(table)
    types = {c[1]: (c[2] or "").upper() for c in info}
    if col not in types or pk not in types:
        return jsonify({"ok": False, "error": f"Colonne invalide : {col if col not in types else pk}"})
    if col == pk:
        return jsonify({"ok": False, "error": "Impossible de modifier la clé primaire"})

    # Conversion selon le type déclaré de la colonne (évite de casser les colonnes texte)
    t = types[col]
    if any(k in t for k in ("INT", "REAL", "FLOA", "DOUB", "NUM")):
        try:
            value = int(value)
        except (ValueError, TypeError):
            try:
                value = float(value)
            except (ValueError, TypeError):
                pass

    try:
        with db() as conn:
            cur = conn.execute(
                f"UPDATE {qi(table)} SET {qi(col)} = ? WHERE CAST({qi(pk)} AS TEXT) = ?",
                (value, str(pk_val)),
            )
            affected = cur.rowcount
        if affected == 0:
            return jsonify({"ok": False, "error": f"0 ligne modifiée — {pk}={pk_val!r} introuvable"})
        print(f"✏️ Édition : {table}.{col} (ID {pk_val}) = {value!r}")
        return jsonify({"ok": True})
    except Exception as e:
        print(f"❌ Échec édition {table}.{col} : {e}")
        return jsonify({"ok": False, "error": str(e)})


@app.route("/api/sql", methods=["POST"])
@login_required
def api_sql():
    query = str(body().get("query", "")).strip()
    if not query:
        return jsonify({"error": "Requête vide"})
    try:
        with db() as conn:
            cur = conn.execute(query)
            if cur.description:
                columns = [d[0] for d in cur.description]
                rows = cur.fetchmany(SQL_MAX_ROWS + 1)
                truncated = len(rows) > SQL_MAX_ROWS
                rows = [[safe(c) for c in r] for r in rows[:SQL_MAX_ROWS]]
                print(f"🗄️ SQL SELECT ({len(rows)} lignes) : {query[:80]}")
                return jsonify({"columns": columns, "rows": rows, "truncated": truncated})
            n = cur.rowcount
        print(f"🗄️ SQL WRITE ({n} lignes affectées) : {query[:80]}")
        msg = f"{n} ligne(s) affectée(s)" if n >= 0 else "Requête exécutée"
        return jsonify({"ok": True, "message": msg})
    except Exception as e:
        print(f"❌ SQL KO : {e}")
        return jsonify({"error": str(e)})


# ================================================================================
# ▤ API : logs
# ================================================================================
@app.route("/api/logs")
@login_required
def api_logs():
    return jsonify({"logs": get_logs()})


@app.route("/api/logs/clear", methods=["POST"])
@login_required
def api_logs_clear():
    LOG_BUFFER.clear()
    print("🧹 Logs vidés depuis le panel admin")
    return jsonify({"ok": True})


# ================================================================================
# ⛁ BACKUPS
# ================================================================================
def backup_files():
    if not os.path.isdir(BACKUP_DIR):
        return []
    return sorted((f for f in os.listdir(BACKUP_DIR) if f.endswith(".db")), reverse=True)


def backup_path_or_404(name):
    """Whitelist stricte : le nom doit être un fichier existant du dossier."""
    if name not in backup_files():
        abort(404)
    return os.path.join(BACKUP_DIR, name)


def prune_backups():
    for old in backup_files()[max_backups():]:
        try:
            os.remove(os.path.join(BACKUP_DIR, old))
        except OSError:
            pass


def create_backup_file(suffix="", prune=True):
    """Copie cohérente via l'API backup de sqlite3. Retourne (path, filename, size_kb)."""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    filename = f"reiatsu_backup_{datetime.now():%Y%m%d_%H%M%S}{suffix}.db"
    path = os.path.join(BACKUP_DIR, filename)
    src = sqlite3.connect(DB_PATH)
    dst = sqlite3.connect(path)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    if prune:
        prune_backups()
    return path, filename, round(os.path.getsize(path) / 1024, 1)


def send_backup_to_discord(path, filename):
    url = webhook_url()
    if not url:
        return False, "Webhook Discord non configuré"
    try:
        size = os.path.getsize(path)
        if size > 8 * 1024 * 1024:
            return False, f"Fichier trop gros pour Discord ({round(size / 1024 / 1024, 1)} Mo > 8 Mo)"
        with open(path, "rb") as f:
            resp = requests.post(
                url,
                data={"content": f"🗄️ Backup base de données — `{filename}`"},
                files={"file": (filename, f, "application/octet-stream")},
                timeout=20,
            )
        if resp.status_code in (200, 204):
            return True, None
        return False, f"Discord a répondu {resp.status_code} : {resp.text[:200]}"
    except Exception as e:
        return False, str(e)


@app.route("/api/backup", methods=["POST"])
@login_required
def api_backup():
    try:
        path, filename, size_kb = create_backup_file()
    except Exception as e:
        print(f"❌ Échec création backup : {e}")
        return jsonify({"ok": False, "error": f"Échec de la création du backup : {e}"}), 500
    sent, err = send_backup_to_discord(path, filename)
    print(f"⛁ Backup créé : {filename} ({size_kb} Ko) — " + ("envoyé sur Discord" if sent else f"⚠ non envoyé ({err})"))
    return jsonify({"ok": True, "filename": filename, "size_kb": size_kb,
                    "discord_sent": sent, "discord_error": err})


@app.route("/api/backup/list")
@login_required
def api_backup_list():
    result = []
    for f in backup_files():
        p = os.path.join(BACKUP_DIR, f)
        result.append({
            "name": f,
            "size_kb": round(os.path.getsize(p) / 1024, 1),
            "date": datetime.fromtimestamp(os.path.getmtime(p)).strftime("%d/%m/%Y %H:%M"),
        })
    return jsonify({"backups": result, "max": max_backups(), "auto_hours": auto_hours()})


@app.route("/api/backup/download/<filename>")
@login_required
def api_backup_download(filename):
    return send_file(backup_path_or_404(filename), as_attachment=True, download_name=filename)


@app.route("/api/backup/<filename>/delete", methods=["POST"])
@login_required
def api_backup_delete(filename):
    os.remove(backup_path_or_404(filename))
    print(f"🗑️ Backup supprimé : {filename}")
    return jsonify({"ok": True})


@app.route("/api/backup/<filename>/restore", methods=["POST"])
@login_required
def api_backup_restore(filename):
    path = backup_path_or_404(filename)
    try:
        create_backup_file("_avant_restore", prune=False)   # filet de sécurité
        src = sqlite3.connect(path)
        dst = sqlite3.connect(DB_PATH)
        try:
            src.backup(dst)
        finally:
            dst.close()
            src.close()
        print(f"♻️ Base restaurée depuis {filename}")
        return jsonify({"ok": True, "message": f"Base restaurée depuis {filename} (copie de sécurité créée avant)."})
    except Exception as e:
        print(f"❌ Échec restauration : {e}")
        return jsonify({"ok": False, "error": str(e)})


@app.route("/api/backup/import", methods=["POST"])
@login_required
def api_backup_import():
    f = request.files.get("file")
    if not f or not f.filename.lower().endswith(".db"):
        return jsonify({"ok": False, "error": "Fichier .db requis"})
    os.makedirs(BACKUP_DIR, exist_ok=True)
    tmp = os.path.join(BACKUP_DIR, f".import_{int(time.time())}.tmp")
    try:
        f.save(tmp)
        with open(tmp, "rb") as fh:
            if fh.read(16) != b"SQLite format 3\x00":
                raise ValueError("Ce fichier n'est pas une base SQLite")
        conn = sqlite3.connect(tmp)
        try:
            if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("Base corrompue (integrity_check KO)")
        finally:
            conn.close()
        name = f"reiatsu_backup_{datetime.now():%Y%m%d_%H%M%S}_import.db"
        os.replace(tmp, os.path.join(BACKUP_DIR, name))
        prune_backups()
        print(f"⬆️ Backup importé : {name}")
        return jsonify({"ok": True, "filename": name})
    except Exception as e:
        if os.path.exists(tmp):
            os.remove(tmp)
        return jsonify({"ok": False, "error": str(e)})


@app.route("/api/backup/settings", methods=["GET", "POST"])
@login_required
def api_backup_settings():
    if request.method == "GET":
        out = []
        for s in BACKUP_SETTINGS:
            raw = os.getenv(s["key"], "")
            out.append({**s, "value": "" if s.get("sensitive") else raw, "has_value": bool(raw)})
        return jsonify({"settings": out})

    vals, updates = body().get("values", {}), {}
    for s in BACKUP_SETTINGS:
        k = s["key"]
        if k not in vals:
            continue
        v = str(vals[k]).strip()
        if s.get("sensitive") and v == "":
            continue   # vide = inchangé
        try:
            if k == "BACKUP_AUTO_HOURS" and float(v) < 0:
                raise ValueError
            if k == "MAX_BACKUPS" and not 1 <= int(v) <= 200:
                raise ValueError
        except ValueError:
            return jsonify({"ok": False, "error": f"Valeur invalide pour {k}"})
        if k == "DISCORD_BACKUP_WEBHOOK_URL" and not v.startswith("https://"):
            return jsonify({"ok": False, "error": "Le webhook doit commencer par https://"})
        updates[k] = v
    try:
        write_env(updates)
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)})
    prune_backups()
    return jsonify({"ok": True})


def backup_scheduler_loop():
    """Backup automatique : lit BACKUP_AUTO_HOURS à chaque tour (modifiable à chaud)."""
    last = time.time()
    while True:
        time.sleep(60)
        hours = auto_hours()
        if hours <= 0:
            last = time.time()
            continue
        if time.time() - last >= hours * 3600:
            last = time.time()
            try:
                path, filename, _ = create_backup_file()
                send_backup_to_discord(path, filename)
                print(f"✅ Backup automatique créé : {filename}")
            except Exception as e:
                print(f"❌ Erreur backup automatique : {e}")


# ================================================================================
# 🔑 API : config .env
# ================================================================================
ENV_LINE_RE  = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=")


def _fmt_env(v: str) -> str:
    if v == "" or re.search(r"[\s#\"'\\$]", v):
        return '"' + v.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return v


def write_env(updates: dict):
    """Met à jour le .env en place (commentaires et ordre conservés)."""
    for k, v in updates.items():
        if "\n" in v or "\r" in v:
            raise ValueError(f"Retour à la ligne interdit dans {k}")
    lines = []
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, encoding="utf-8") as f:
            lines = f.read().splitlines()
    out, done = [], set()
    for line in lines:
        m = ENV_LINE_RE.match(line)
        if m and m.group(1) in updates:
            k = m.group(1)
            if k not in done:
                out.append(f"{k}={_fmt_env(updates[k])}")
                done.add(k)
        else:
            out.append(line)
    for k, v in updates.items():
        if k not in done:
            out.append(f"{k}={_fmt_env(v)}")
    tmp = ENV_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    os.replace(tmp, ENV_PATH)
    os.environ.update(updates)


@app.route("/api/env", methods=["GET", "POST"])
@login_required
def api_env():
    """Lecture / écriture du .env comme un simple fichier texte."""
    if request.method == "GET":
        text = ""
        if os.path.exists(ENV_PATH):
            with open(ENV_PATH, encoding="utf-8") as f:
                text = f.read()
        return jsonify({"text": text})

    text = str(body().get("text", "")).replace("\r\n", "\n")
    vals = dotenv_values(stream=StringIO(text))
    for k in ("ADMIN_PASSWORD", "ADMIN_SECRET"):
        if not vals.get(k):
            return jsonify({"ok": False, "error": f"{k} doit rester défini (sinon le panel ne redémarre plus)"})
    tmp = ENV_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text if text.endswith("\n") else text + "\n")
    os.replace(tmp, ENV_PATH)
    load_dotenv(ENV_PATH, override=True)   # les réglages de backup s'appliquent tout de suite
    print("🔑 .env modifié depuis le panel")
    return jsonify({"ok": True})


# ================================================================================
# ⚙️ API : actions (git, reload, restart)
# ================================================================================
_bot_ref = None


def set_bot(bot):
    global _bot_ref
    _bot_ref = bot


def run_git_pull():
    try:
        r = subprocess.run(["git", "pull"], cwd=ROOT, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        return False, "❌ git pull : timeout"
    out = (r.stdout + r.stderr).strip()
    print(out)
    return r.returncode == 0, out


def _discover_extensions():
    """Liste les extensions présentes sur le disque (même logique que bot.py)."""
    found = []
    commands_dir = os.path.join(ROOT, "commands")
    if os.path.isdir(commands_dir):
        for category in sorted(os.listdir(commands_dir)):
            cat_path = os.path.join(commands_dir, category)
            if os.path.isdir(cat_path):
                for filename in sorted(os.listdir(cat_path)):
                    if filename.endswith(".py") and filename != "__init__.py":
                        found.append(f"commands.{category}.{filename[:-3]}")
    tasks_dir = os.path.join(ROOT, "tasks")
    if os.path.isdir(tasks_dir):
        for filename in sorted(os.listdir(tasks_dir)):
            if filename.endswith(".py") and filename != "__init__.py":
                found.append(f"tasks.{filename[:-3]}")
    return found


def reload_cogs():
    if _bot_ref is None:
        print("❌ Bot non disponible pour le reload")
        return False, "❌ Bot non disponible"
    lines = []

    async def go():
        on_disk = set(_discover_extensions())
        loaded = list(_bot_ref.extensions.keys())

        # 1. Déjà chargés : recharger, ou décharger si le fichier a disparu
        for ext in loaded:
            try:
                if ext in on_disk:
                    await _bot_ref.reload_extension(ext)
                    lines.append(f"✅ rechargé : {ext}")
                elif ext.startswith(("commands.", "tasks.")):
                    await _bot_ref.unload_extension(ext)
                    lines.append(f"🗑️ déchargé (fichier supprimé) : {ext}")
            except Exception as e:
                lines.append(f"❌ {ext}: {e}")
                print(f"❌ Reload KO : {ext} — {e}")

        # 2. Nouveaux fichiers : les charger
        for ext in sorted(on_disk):
            if ext not in _bot_ref.extensions:
                try:
                    await _bot_ref.load_extension(ext)
                    lines.append(f"🆕 chargé : {ext}")
                except Exception as e:
                    lines.append(f"❌ {ext}: {e}")
                    print(f"❌ Load KO : {ext} — {e}")

        # 3. Slash commands : synchroniser avec Discord
        try:
            synced = await _bot_ref.tree.sync()
            lines.append(f"🔁 {len(synced)} slash command(s) synchronisée(s)")
        except Exception as e:
            lines.append(f"❌ tree.sync : {e}")

    try:
        asyncio.run_coroutine_threadsafe(go(), _bot_ref.loop).result(timeout=90)
    except Exception as e:
        lines.append(f"❌ Reload interrompu : {e}")
    for l in lines:
        print(l)
    return not any(l.startswith("❌") for l in lines), "\n".join(lines)


def restart_bot_process():
    print("🔄 Redémarrage complet via start.sh...")
    subprocess.Popen(
        ["bash", os.path.join(ROOT, "start.sh")],
        stdout=1, stderr=2, stdin=subprocess.DEVNULL, close_fds=True,
    )
    time.sleep(2)
    os.kill(os.getpid(), 9)


@app.route("/api/action/<action>", methods=["POST"])
@login_required
def api_action(action):
    print(f"🔄 Action : {action}")

    if action == "git_pull":
        ok, out = run_git_pull()
        return jsonify({"ok": ok, "output": out})

    if action == "git_pull_restart":
        ok, out = run_git_pull()
        if not ok:
            return jsonify({"ok": False, "output": out})
        ok2, out2 = reload_cogs()
        return jsonify({"ok": ok2, "output": f"{out}\n\n{out2}"})

    if action == "reload_cogs":
        ok, out = reload_cogs()
        return jsonify({"ok": ok, "output": out})

    if action == "restart_bot":
        threading.Timer(1.0, restart_bot_process).start()
        return jsonify({"ok": True, "output": "⏳ Redémarrage en cours…"})

    return jsonify({"ok": False, "output": "Action inconnue"})


# ================================================================================
# 🚨 Gestion des erreurs
# ================================================================================
@app.errorhandler(429)
def ratelimit_handler(e):
    msg = "Trop de tentatives. Réessaie dans une minute."
    if request.path == "/login":
        return render_template("login.html", error=msg), 429
    return jsonify({"ok": False, "error": msg}), 429


@app.errorhandler(CSRFError)
def csrf_error_handler(e):
    msg = "Session expirée ou invalide. Recharge la page."
    if request.path == "/login":
        return render_template("login.html", error=msg), 400
    return jsonify({"ok": False, "error": msg}), 400


# ================================================================================
# 🚀 Lancement Flask (dans un thread)
# ================================================================================
def run_admin(port=5050):
    threading.Thread(target=backup_scheduler_loop, daemon=True).start()
    if auto_hours() > 0:
        print(f"⏰ Backup automatique activé : toutes les {auto_hours():g}h")
    app.run(host=ADMIN_HOST, port=port, debug=False, use_reloader=False)
