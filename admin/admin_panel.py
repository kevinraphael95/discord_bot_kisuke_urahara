# ────────────────────────────────────────────────────────────────────────────────
# 📌 admin_panel.py
# Objectif : Interface web d'administration du bot (DB, logs, git pull, reload)
# Les templates (HTML) sont dans templates/, le CSS/JS dans static/.
# ────────────────────────────────────────────────────────────────────────────────

import os
import sqlite3
import subprocess
import threading
import time
from functools import wraps

from flask import Flask, render_template, request, redirect, session, jsonify, url_for
from dotenv import load_dotenv

load_dotenv()

# ─── Config ────────────────────────────────────────────────────────────────────
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin1234")
SECRET_KEY     = os.getenv("FLASK_SECRET", "bleach_urahara_secret")
DB_PATH        = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "database", "reiatsu.db")

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = SECRET_KEY

# ─── Auth ──────────────────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


# ─── Routes pages ──────────────────────────────────────────────────────────────
@app.route("/", methods=["GET"])
@login_required
def index():
    return render_template("main.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("index"))
        error = "Mot de passe incorrect."
    return render_template("login.html", error=error)


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))


# ─── API : Tables (liste dynamique) ───────────────────────────────────────────
def get_all_tables():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cur.fetchall()]
    conn.close()
    return tables


def get_pk_for_table(table):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    cols = cur.fetchall()
    conn.close()
    for col in cols:
        if col[5] == 1:
            return col[1]
    return cols[0][1]


@app.route("/api/tables")
@login_required
def api_tables():
    return jsonify({"tables": get_all_tables()})


# ─── API : Table ───────────────────────────────────────────────────────────────
@app.route("/api/table/<table_name>")
@login_required
def api_table(table_name):
    if table_name not in get_all_tables():
        return jsonify({"error": "Table non autorisée"}), 403
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM {table_name}")
    raw_rows = cur.fetchall()
    columns = [d[0] for d in cur.description]
    pk_col = get_pk_for_table(table_name)
    pk_idx = columns.index(pk_col) if pk_col in columns else 0
    rows = [
        [str(cell) if i == pk_idx and cell is not None else cell for i, cell in enumerate(row)]
        for row in raw_rows
    ]
    conn.close()
    return jsonify({"columns": columns, "rows": rows, "pk": pk_col})


@app.route("/api/edit", methods=["POST"])
@login_required
def api_edit():
    data = request.json
    table  = data.get("table")
    pk     = data.get("pk")
    pk_val = data.get("pk_val")
    col    = data.get("col")
    value  = data.get("value")

    if table not in get_all_tables():
        return jsonify({"ok": False, "error": "Table non autorisée"})
    if col == pk:
        return jsonify({"ok": False, "error": "Impossible de modifier la clé primaire"})

    try:
        try:
            value = int(value)
        except (ValueError, TypeError):
            pass

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            f"UPDATE {table} SET {col} = ? WHERE CAST({pk} AS TEXT) = CAST(? AS TEXT)",
            (value, str(pk_val))
        )
        rows_affected = cur.rowcount
        conn.commit()
        conn.close()
        if rows_affected == 0:
            return jsonify({"ok": False, "error": f"0 ligne modifiée — {pk}={pk_val!r} introuvable"})
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


# ─── API : SQL ─────────────────────────────────────────────────────────────────
@app.route("/api/sql", methods=["POST"])
@login_required
def api_sql():
    query = request.json.get("query", "").strip()
    if not query:
        return jsonify({"error": "Requête vide"})
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(query)
        if cur.description:
            columns = [d[0] for d in cur.description]
            rows = cur.fetchall()
            conn.close()
            return jsonify({"columns": columns, "rows": rows})
        else:
            conn.commit()
            conn.close()
            return jsonify({"ok": True, "message": f"{cur.rowcount} ligne(s) affectée(s)"})
    except Exception as e:
        return jsonify({"error": str(e)})


# ─── API : Logs ────────────────────────────────────────────────────────────────
@app.route("/api/logs")
@login_required
def api_logs():
    from utils.logger import get_logs
    return jsonify({"logs": get_logs()})


@app.route("/api/logs/clear", methods=["POST"])
@login_required
def api_logs_clear():
    from utils.logger import LOG_BUFFER
    LOG_BUFFER.clear()
    return jsonify({"ok": True})


# ─── API : Actions ─────────────────────────────────────────────────────────────
_bot_ref = None


def set_bot(bot):
    global _bot_ref
    _bot_ref = bot


@app.route("/api/action/<action>", methods=["POST"])
@login_required
def api_action(action):

    if action == "git_pull":
        result = subprocess.run(["git", "pull"], capture_output=True, text=True, timeout=30)
        output = result.stdout + result.stderr
        return jsonify({"ok": result.returncode == 0, "output": output})

    elif action == "git_pull_restart":
        result = subprocess.run(["git", "pull"], capture_output=True, text=True, timeout=30)
        output = result.stdout + result.stderr
        if _bot_ref is None:
            return jsonify({"ok": False, "output": output + "\n❌ Bot non disponible pour le reload"})
        import asyncio
        output_lines = [output]

        async def do_reload():
            extensions = list(_bot_ref.extensions.keys())
            for ext in extensions:
                try:
                    await _bot_ref.reload_extension(ext)
                    output_lines.append(f"✅ {ext}")
                except Exception as e:
                    output_lines.append(f"❌ {ext}: {e}")

        asyncio.run_coroutine_threadsafe(do_reload(), _bot_ref.loop).result(timeout=15)
        return jsonify({"ok": True, "output": "\n".join(output_lines)})

    elif action == "reload_cogs":
        if _bot_ref is None:
            return jsonify({"ok": False, "output": "Bot non disponible"})
        import asyncio
        loop = _bot_ref.loop
        output_lines = []

        async def do_reload():
            extensions = list(_bot_ref.extensions.keys())
            for ext in extensions:
                try:
                    await _bot_ref.reload_extension(ext)
                    output_lines.append(f"✅ {ext}")
                except Exception as e:
                    output_lines.append(f"❌ {ext}: {e}")

        asyncio.run_coroutine_threadsafe(do_reload(), loop).result(timeout=15)
        return jsonify({"ok": True, "output": "\n".join(output_lines)})

    elif action == "restart_bot":
        threading.Timer(1.0, restart_bot_process).start()
        return jsonify({"ok": True, "output": "⏳ Redémarrage en cours…"})

    return jsonify({"ok": False, "output": "Action inconnue"})


def restart_bot_process():
    print("🔄 Redémarrage complet via start.sh...")
    start_sh = os.path.join(os.path.dirname(os.path.abspath(__file__)), "start.sh")
    subprocess.Popen(
        ["bash", start_sh],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        start_new_session=True
    )
    time.sleep(1)
    os.kill(os.getpid(), 9)


# ─── Lancement Flask (dans un thread) ─────────────────────────────────────────
def run_admin(port=5050):
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
