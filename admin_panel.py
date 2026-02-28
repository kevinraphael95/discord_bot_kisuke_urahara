# ────────────────────────────────────────────────────────────────────────────────
# 📌 admin_panel.py
# Objectif : Interface web d'administration du bot (DB, logs, git pull, reload)
# ────────────────────────────────────────────────────────────────────────────────

import os
import json
import sqlite3
import subprocess
import threading
import sys
from functools import wraps
from datetime import datetime

from flask import Flask, render_template_string, request, redirect, session, jsonify, url_for
from dotenv import load_dotenv

load_dotenv()

# ─── Config ────────────────────────────────────────────────────────────────────
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin1234")
SECRET_KEY     = os.getenv("FLASK_SECRET", "bleach_urahara_secret")
DB_PATH        = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database", "reiatsu.db")

app = Flask(__name__)
app.secret_key = SECRET_KEY

# ─── Auth ──────────────────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


# ─── HTML Template ─────────────────────────────────────────────────────────────
HTML_LOGIN = """
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Kisuke Admin — Login</title>
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=IBM+Plex+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #0a0a0f;
    --card: #12121a;
    --border: #2a2a3a;
    --accent: #e8c840;
    --accent2: #ff4444;
    --text: #d0d0e0;
    --muted: #555570;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: var(--bg);
    color: var(--text);
    font-family: 'IBM Plex Mono', monospace;
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    background-image: repeating-linear-gradient(
      0deg, transparent, transparent 39px,
      rgba(255,255,255,0.015) 39px, rgba(255,255,255,0.015) 40px
    );
  }
  .login-box {
    background: var(--card);
    border: 1px solid var(--border);
    border-top: 3px solid var(--accent);
    padding: 48px 40px;
    width: 100%;
    max-width: 400px;
    position: relative;
  }
  .login-box::before {
    content: 'KISUKE ADMIN';
    font-family: 'Bebas Neue', sans-serif;
    font-size: 28px;
    letter-spacing: 6px;
    color: var(--accent);
    display: block;
    margin-bottom: 8px;
  }
  .login-box::after {
    content: 'PANNEAU D\\'ADMINISTRATION';
    font-size: 10px;
    letter-spacing: 3px;
    color: var(--muted);
    display: block;
    margin-bottom: 36px;
  }
  input[type=password] {
    width: 100%;
    background: #0a0a0f;
    border: 1px solid var(--border);
    border-radius: 2px;
    color: var(--text);
    font-family: 'IBM Plex Mono', monospace;
    font-size: 14px;
    padding: 12px 16px;
    outline: none;
    transition: border-color .2s;
    margin-bottom: 16px;
  }
  input[type=password]:focus { border-color: var(--accent); }
  button {
    width: 100%;
    background: var(--accent);
    color: #0a0a0f;
    border: none;
    font-family: 'Bebas Neue', sans-serif;
    font-size: 18px;
    letter-spacing: 3px;
    padding: 13px;
    cursor: pointer;
    transition: opacity .2s;
  }
  button:hover { opacity: .85; }
  .error {
    background: rgba(255,68,68,.1);
    border: 1px solid var(--accent2);
    color: var(--accent2);
    font-size: 12px;
    padding: 10px 14px;
    margin-bottom: 16px;
  }
</style>
</head>
<body>
<div class="login-box">
  {% if error %}<div class="error">⚠ {{ error }}</div>{% endif %}
  <form method="POST">
    <input type="password" name="password" placeholder="Mot de passe admin" autofocus>
    <button type="submit">ENTRER</button>
  </form>
</div>
</body>
</html>
"""

HTML_MAIN = """
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Kisuke Admin</title>
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=IBM+Plex+Mono:wght@300;400;600&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #0a0a0f;
    --panel: #0f0f18;
    --card: #13131e;
    --border: #22223a;
    --border2: #2e2e4a;
    --accent: #e8c840;
    --accent2: #ff5555;
    --accent3: #44aaff;
    --green: #44dd88;
    --text: #cccce0;
    --muted: #44445a;
    --muted2: #66667a;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: var(--bg);
    color: var(--text);
    font-family: 'IBM Plex Mono', monospace;
    font-size: 13px;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
  }

  /* ─── Header ─── */
  header {
    background: var(--panel);
    border-bottom: 1px solid var(--border);
    padding: 0 24px;
    height: 56px;
    display: flex;
    align-items: center;
    gap: 24px;
    position: sticky;
    top: 0;
    z-index: 100;
  }
  .logo {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 22px;
    letter-spacing: 5px;
    color: var(--accent);
    flex-shrink: 0;
  }
  .logo span { color: var(--muted2); font-size: 11px; letter-spacing: 2px; margin-left: 8px; vertical-align: middle; }
  nav { display: flex; gap: 4px; flex: 1; }
  .tab {
    padding: 6px 18px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    letter-spacing: 2px;
    text-transform: uppercase;
    background: none;
    border: 1px solid transparent;
    color: var(--muted2);
    cursor: pointer;
    transition: all .15s;
    border-radius: 2px;
  }
  .tab:hover { color: var(--text); border-color: var(--border2); }
  .tab.active { color: var(--accent); border-color: var(--accent); background: rgba(232,200,64,.07); }
  .header-right { margin-left: auto; display: flex; gap: 12px; align-items: center; }
  .status-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--green); box-shadow: 0 0 8px var(--green); animation: pulse 2s infinite; }
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.4} }
  .btn-logout {
    font-size: 10px; letter-spacing: 2px; color: var(--muted2); background: none;
    border: 1px solid var(--border); padding: 5px 12px; cursor: pointer; border-radius: 2px;
    transition: all .15s;
  }
  .btn-logout:hover { color: var(--accent2); border-color: var(--accent2); }

  /* ─── Layout ─── */
  main { flex: 1; padding: 24px; display: flex; flex-direction: column; gap: 20px; }
  .section { display: none; }
  .section.active { display: flex; flex-direction: column; gap: 16px; }

  /* ─── Cards ─── */
  .card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 3px;
    overflow: hidden;
  }
  .card-header {
    padding: 12px 20px;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    gap: 12px;
    background: var(--panel);
  }
  .card-title {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 15px;
    letter-spacing: 3px;
    color: var(--accent);
  }
  .card-body { padding: 20px; }

  /* ─── Table ─── */
  .table-wrap { overflow-x: auto; }
  table { width: 100%; border-collapse: collapse; font-size: 12px; }
  th {
    text-align: left;
    padding: 8px 12px;
    color: var(--muted2);
    font-size: 10px;
    letter-spacing: 2px;
    text-transform: uppercase;
    border-bottom: 1px solid var(--border2);
    white-space: nowrap;
  }
  td {
    padding: 9px 12px;
    border-bottom: 1px solid var(--border);
    max-width: 200px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  tr:last-child td { border-bottom: none; }
  tr:hover td { background: rgba(255,255,255,.02); }
  .edit-cell { cursor: pointer; }
  .edit-cell:hover { color: var(--accent); }

  /* ─── Forms ─── */
  .form-row { display: flex; gap: 12px; flex-wrap: wrap; align-items: flex-end; }
  .form-group { display: flex; flex-direction: column; gap: 6px; }
  label { font-size: 10px; letter-spacing: 2px; color: var(--muted2); text-transform: uppercase; }
  input[type=text], input[type=number], select, textarea {
    background: #0a0a0f;
    border: 1px solid var(--border2);
    border-radius: 2px;
    color: var(--text);
    font-family: 'IBM Plex Mono', monospace;
    font-size: 13px;
    padding: 8px 12px;
    outline: none;
    transition: border-color .15s;
  }
  input:focus, select:focus, textarea:focus { border-color: var(--accent); }
  textarea { resize: vertical; min-height: 80px; }

  /* ─── Buttons ─── */
  .btn {
    padding: 8px 20px;
    font-family: 'Bebas Neue', sans-serif;
    font-size: 14px;
    letter-spacing: 2px;
    border: none;
    border-radius: 2px;
    cursor: pointer;
    transition: opacity .15s;
    white-space: nowrap;
  }
  .btn:hover { opacity: .8; }
  .btn-primary { background: var(--accent); color: #0a0a0f; }
  .btn-danger { background: var(--accent2); color: #fff; }
  .btn-info { background: var(--accent3); color: #0a0a0f; }
  .btn-success { background: var(--green); color: #0a0a0f; }
  .btn-ghost { background: transparent; border: 1px solid var(--border2); color: var(--text); font-family: 'IBM Plex Mono', monospace; font-size: 12px; letter-spacing: 1px; }

  /* ─── Logs ─── */
  .log-box {
    background: #060609;
    border: 1px solid var(--border);
    border-radius: 2px;
    padding: 16px;
    height: 480px;
    overflow-y: auto;
    font-size: 12px;
    line-height: 1.7;
  }
  .log-line { color: var(--text); }
  .log-line.err { color: var(--accent2); }
  .log-line.ok { color: var(--green); }
  .log-line.warn { color: var(--accent); }

  /* ─── Actions ─── */
  .actions-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; }
  .action-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 3px;
    padding: 20px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .action-title { font-family: 'Bebas Neue', sans-serif; font-size: 16px; letter-spacing: 3px; color: var(--text); }
  .action-desc { font-size: 11px; color: var(--muted2); line-height: 1.6; }
  .result-box {
    background: #060609;
    border: 1px solid var(--border);
    border-radius: 2px;
    padding: 12px;
    font-size: 11px;
    color: var(--green);
    max-height: 200px;
    overflow-y: auto;
    display: none;
  }
  .result-box.err { color: var(--accent2); }

  /* ─── SQL ─── */
  .sql-result { margin-top: 16px; }
  
  /* ─── Toast ─── */
  #toast {
    position: fixed; bottom: 24px; right: 24px;
    background: var(--card); border: 1px solid var(--border);
    border-left: 3px solid var(--accent);
    padding: 12px 20px; font-size: 12px;
    opacity: 0; transition: opacity .3s;
    z-index: 999; pointer-events: none;
    max-width: 300px;
  }
  #toast.show { opacity: 1; }
  #toast.err { border-left-color: var(--accent2); }

  /* ─── Misc ─── */
  .badge {
    display: inline-block; padding: 2px 8px; border-radius: 2px;
    font-size: 10px; letter-spacing: 1px; text-transform: uppercase;
  }
  .badge-yellow { background: rgba(232,200,64,.15); color: var(--accent); border: 1px solid rgba(232,200,64,.3); }
  .badge-blue { background: rgba(68,170,255,.15); color: var(--accent3); border: 1px solid rgba(68,170,255,.3); }
  .badge-green { background: rgba(68,221,136,.15); color: var(--green); border: 1px solid rgba(68,221,136,.3); }
  .sep { width: 1px; background: var(--border); align-self: stretch; }
  .row { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
  .filter-input { width: 240px; }
  .table-meta { font-size: 11px; color: var(--muted2); }
</style>
</head>
<body>

<!-- Header -->
<header>
  <div class="logo">KISUKE <span>ADMIN</span></div>
  <nav>
    <button class="tab active" onclick="showTab('db', this)">BASE DE DONNÉES</button>
    <button class="tab" onclick="showTab('sql', this)">SQL</button>
    <button class="tab" onclick="showTab('logs', this)">LOGS</button>
    <button class="tab" onclick="showTab('actions', this)">ACTIONS</button>
  </nav>
  <div class="header-right">
    <div class="status-dot" title="Bot en ligne"></div>
    <form method="POST" action="/logout" style="display:inline">
      <button class="btn-logout">DÉCONNEXION</button>
    </form>
  </div>
</header>

<main>

  <!-- ══════════════════════════════════════════════════════════════
       TAB : BASE DE DONNÉES
  ══════════════════════════════════════════════════════════════ -->
  <section class="section active" id="tab-db">
    <div class="card">
      <div class="card-header">
        <span class="card-title">TABLES</span>
        <div class="row" style="margin-left: auto; gap: 12px;">
          <select id="tableSelect" onchange="loadTable()">
            <option value="reiatsu">reiatsu</option>
            <option value="reiatsu_config">reiatsu_config</option>
            <option value="mots_trouves">mots_trouves</option>
          </select>
          <input type="text" class="filter-input" id="filterInput" placeholder="Filtrer..." oninput="filterTable()">
          <span class="table-meta" id="tableCount"></span>
        </div>
      </div>
      <div class="card-body">
        <div class="table-wrap">
          <table id="mainTable">
            <thead id="tableHead"></thead>
            <tbody id="tableBody"></tbody>
          </table>
        </div>
      </div>
    </div>
  </section>

  <!-- ══════════════════════════════════════════════════════════════
       TAB : SQL CUSTOM
  ══════════════════════════════════════════════════════════════ -->
  <section class="section" id="tab-sql">
    <div class="card">
      <div class="card-header"><span class="card-title">REQUÊTE SQL</span></div>
      <div class="card-body" style="display:flex;flex-direction:column;gap:16px">
        <textarea id="sqlQuery" rows="5" placeholder="SELECT * FROM reiatsu LIMIT 10;"></textarea>
        <div class="row">
          <button class="btn btn-primary" onclick="runSQL()">EXÉCUTER</button>
          <button class="btn btn-ghost" onclick="document.getElementById('sqlQuery').value=''">EFFACER</button>
        </div>
        <div id="sqlResult" class="sql-result"></div>
      </div>
    </div>
    <div class="card">
      <div class="card-header"><span class="card-title">REQUÊTES RAPIDES</span></div>
      <div class="card-body" style="display:flex;gap:10px;flex-wrap:wrap">
        <button class="btn btn-ghost" onclick="setSQL('SELECT user_id, username, points, classe, niveau FROM reiatsu ORDER BY points DESC LIMIT 20')">Top 20 points</button>
        <button class="btn btn-ghost" onclick="setSQL('SELECT * FROM reiatsu_config')">Config guilds</button>
        <button class="btn btn-ghost" onclick="setSQL('SELECT user_id, username, last_found_at FROM mots_trouves ORDER BY last_found_at DESC LIMIT 20')">Derniers mots</button>
        <button class="btn btn-ghost" onclick="setSQL('SELECT COUNT(*) as total, SUM(points) as total_points FROM reiatsu')">Stats globales</button>
        <button class="btn btn-ghost" onclick="setSQL('SELECT classe, COUNT(*) as nb FROM reiatsu GROUP BY classe ORDER BY nb DESC')">Par classe</button>
      </div>
    </div>
  </section>

  <!-- ══════════════════════════════════════════════════════════════
       TAB : LOGS
  ══════════════════════════════════════════════════════════════ -->
  <section class="section" id="tab-logs">
    <div class="card">
      <div class="card-header">
        <span class="card-title">LOGS EN DIRECT</span>
        <div class="row" style="margin-left:auto;gap:10px">
          <label style="display:flex;align-items:center;gap:8px;cursor:pointer">
            <input type="checkbox" id="autoRefresh" checked onchange="toggleAutoRefresh()">
            <span style="font-size:11px;letter-spacing:1px;color:var(--muted2)">AUTO-REFRESH</span>
          </label>
          <button class="btn btn-ghost" onclick="loadLogs()">↻ RAFRAÎCHIR</button>
          <button class="btn btn-ghost" onclick="clearLogs()">VIDER</button>
        </div>
      </div>
      <div class="card-body">
        <div class="log-box" id="logBox"></div>
      </div>
    </div>
  </section>

  <!-- ══════════════════════════════════════════════════════════════
       TAB : ACTIONS
  ══════════════════════════════════════════════════════════════ -->
  <section class="section" id="tab-actions">
    <div class="actions-grid">

      <div class="action-card">
        <div class="action-title">🔄 GIT PULL</div>
        <div class="action-desc">Récupère les dernières modifications depuis GitHub sans redémarrer le bot.</div>
        <button class="btn btn-info" onclick="doAction('git_pull', this)">LANCER GIT PULL</button>
        <div class="result-box" id="res-git_pull"></div>
      </div>

      <div class="action-card">
        <div class="action-title">♻️ GIT PULL + RESTART</div>
        <div class="action-desc">Pull les mises à jour puis redémarre complètement le bot. ~5 secondes d'interruption.</div>
        <button class="btn btn-danger" onclick="doAction('git_pull_restart', this)">PULL + REDÉMARRER</button>
        <div class="result-box" id="res-git_pull_restart"></div>
      </div>

      <div class="action-card">
        <div class="action-title">🔁 RELOAD COGS</div>
        <div class="action-desc">Recharge tous les cogs/commandes sans redémarrer le bot. Idéal pour tester des changements rapides.</div>
        <button class="btn btn-success" onclick="doAction('reload_cogs', this)">RELOAD COGS</button>
        <div class="result-box" id="res-reload_cogs"></div>
      </div>

      <div class="action-card">
        <div class="action-title">🛑 RESTART BOT</div>
        <div class="action-desc">Redémarre uniquement le bot sans git pull. Le panel admin reste disponible.</div>
        <button class="btn btn-danger" onclick="doAction('restart_bot', this)">REDÉMARRER</button>
        <div class="result-box" id="res-restart_bot"></div>
      </div>

    </div>
  </section>

</main>

<!-- Toast -->
<div id="toast"></div>

<!-- Edit Modal -->
<div id="editModal" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:200;align-items:center;justify-content:center">
  <div style="background:var(--card);border:1px solid var(--border);border-top:2px solid var(--accent);padding:32px;min-width:360px;max-width:600px;width:90%">
    <div style="font-family:'Bebas Neue';font-size:18px;letter-spacing:3px;color:var(--accent);margin-bottom:20px">MODIFIER LA CELLULE</div>
    <div style="font-size:11px;color:var(--muted2);margin-bottom:6px" id="editMeta"></div>
    <input type="text" id="editValue" style="width:100%;margin-bottom:16px">
    <input type="hidden" id="editTable">
    <input type="hidden" id="editPk">
    <input type="hidden" id="editPkVal">
    <input type="hidden" id="editCol">
    <div class="row">
      <button class="btn btn-primary" onclick="saveEdit()">SAUVEGARDER</button>
      <button class="btn btn-ghost" onclick="closeModal()">ANNULER</button>
    </div>
  </div>
</div>

<script>
// ─── Tab switching ──────────────────────────────────────────────────────────
function showTab(name, btn) {
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
  btn.classList.add('active');
  if (name === 'db') loadTable();
  if (name === 'logs') loadLogs();
}

// ─── Toast ──────────────────────────────────────────────────────────────────
function toast(msg, isErr=false) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = 'show' + (isErr ? ' err' : '');
  setTimeout(() => t.className = '', 3000);
}

// ─── DB Table ───────────────────────────────────────────────────────────────
let currentData = [];

async function loadTable() {
  const table = document.getElementById('tableSelect').value;
  const res = await fetch('/api/table/' + table);
  const data = await res.json();
  currentData = data.rows;
  renderTable(data.columns, data.rows, table, data.pk);
  document.getElementById('tableCount').textContent = data.rows.length + ' entrées';
}

function renderTable(cols, rows, tableName, pk) {
  const head = document.getElementById('tableHead');
  const body = document.getElementById('tableBody');
  head.innerHTML = '<tr>' + cols.map(c => `<th>${c}</th>`).join('') + '</tr>';
  body.innerHTML = rows.map(row => {
    return '<tr>' + cols.map((col, i) => {
      const val = row[i] ?? '';
      const isPk = col === pk;
      return `<td class="${isPk ? '' : 'edit-cell'}" title="${val}" 
        ${isPk ? '' : `onclick="openEdit('${tableName}','${pk}','${row[0]}','${col}','${String(val).replace(/'/g,"\\'")}')"`}
        >${val}</td>`;
    }).join('') + '</tr>';
  }).join('');
}

function filterTable() {
  const filter = document.getElementById('filterInput').value.toLowerCase();
  const rows = document.getElementById('tableBody').querySelectorAll('tr');
  rows.forEach(r => {
    r.style.display = r.textContent.toLowerCase().includes(filter) ? '' : 'none';
  });
}

// ─── Edit Modal ─────────────────────────────────────────────────────────────
function openEdit(table, pk, pkVal, col, val) {
  document.getElementById('editTable').value = table;
  document.getElementById('editPk').value = pk;
  document.getElementById('editPkVal').value = pkVal;
  document.getElementById('editCol').value = col;
  document.getElementById('editValue').value = val;
  document.getElementById('editMeta').textContent = `Table: ${table} | Colonne: ${col} | ID: ${pkVal}`;
  document.getElementById('editModal').style.display = 'flex';
  document.getElementById('editValue').focus();
}

function closeModal() {
  document.getElementById('editModal').style.display = 'none';
}

async function saveEdit() {
  const payload = {
    table: document.getElementById('editTable').value,
    pk: document.getElementById('editPk').value,
    pk_val: document.getElementById('editPkVal').value,
    col: document.getElementById('editCol').value,
    value: document.getElementById('editValue').value,
  };
  const res = await fetch('/api/edit', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(payload) });
  const data = await res.json();
  closeModal();
  if (data.ok) { toast('✅ Modifié avec succès'); loadTable(); }
  else toast('❌ ' + data.error, true);
}

document.getElementById('editModal').addEventListener('click', e => {
  if (e.target === document.getElementById('editModal')) closeModal();
});

// ─── SQL ────────────────────────────────────────────────────────────────────
function setSQL(q) {
  document.getElementById('sqlQuery').value = q;
  document.querySelectorAll('.tab')[1].click();
}

async function runSQL() {
  const q = document.getElementById('sqlQuery').value;
  const res = await fetch('/api/sql', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({query: q}) });
  const data = await res.json();
  const el = document.getElementById('sqlResult');
  if (data.error) {
    el.innerHTML = `<div style="color:var(--accent2);font-size:12px;padding:12px;background:#060609;border:1px solid var(--border)">❌ ${data.error}</div>`;
  } else if (data.columns) {
    let html = `<div class="table-wrap"><table><thead><tr>${data.columns.map(c=>`<th>${c}</th>`).join('')}</tr></thead><tbody>`;
    html += data.rows.map(r => `<tr>${r.map(v=>`<td>${v??''}</td>`).join('')}</tr>`).join('');
    html += `</tbody></table></div><div class="table-meta" style="margin-top:8px">${data.rows.length} résultat(s)</div>`;
    el.innerHTML = html;
  } else {
    el.innerHTML = `<div style="color:var(--green);font-size:12px;padding:12px;background:#060609;border:1px solid var(--border)">✅ ${data.message}</div>`;
  }
}

// ─── Logs ───────────────────────────────────────────────────────────────────
let autoRefreshInterval = null;

async function loadLogs() {
  const res = await fetch('/api/logs');
  const data = await res.json();
  const box = document.getElementById('logBox');
  const wasAtBottom = box.scrollHeight - box.clientHeight <= box.scrollTop + 10;
  box.innerHTML = data.logs.map(line => {
    let cls = 'log-line';
    if (line.includes('❌') || line.includes('ERROR') || line.includes('error')) cls += ' err';
    else if (line.includes('✅') || line.includes('Loaded') || line.includes('Connecté')) cls += ' ok';
    else if (line.includes('⚠') || line.includes('WARNING')) cls += ' warn';
    return `<div class="${cls}">${escHtml(line)}</div>`;
  }).join('');
  if (wasAtBottom) box.scrollTop = box.scrollHeight;
}

function clearLogs() {
  document.getElementById('logBox').innerHTML = '';
  fetch('/api/logs/clear', {method:'POST'});
}

function toggleAutoRefresh() {
  const checked = document.getElementById('autoRefresh').checked;
  if (checked) { autoRefreshInterval = setInterval(loadLogs, 2000); }
  else { clearInterval(autoRefreshInterval); }
}

// ─── Actions ────────────────────────────────────────────────────────────────
async function doAction(action, btn) {
  const resBox = document.getElementById('res-' + action);
  resBox.style.display = 'block';
  resBox.className = 'result-box';
  resBox.textContent = '⏳ En cours...';
  btn.disabled = true;
  try {
    const res = await fetch('/api/action/' + action, {method: 'POST'});
    const data = await res.json();
    resBox.textContent = data.output || data.message;
    if (!data.ok) resBox.classList.add('err');
    else toast('✅ ' + action + ' terminé');
  } catch(e) {
    resBox.textContent = '❌ Erreur réseau';
    resBox.classList.add('err');
  }
  btn.disabled = false;
}

// ─── Utils ──────────────────────────────────────────────────────────────────
function escHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// ─── Init ───────────────────────────────────────────────────────────────────
loadTable();
autoRefreshInterval = setInterval(loadLogs, 2000);
</script>
</body>
</html>
"""

# ─── Routes ────────────────────────────────────────────────────────────────────

@app.route("/", methods=["GET"])
@login_required
def index():
    return render_template_string(HTML_MAIN)


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("index"))
        error = "Mot de passe incorrect."
    return render_template_string(HTML_LOGIN, error=error)


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))


# ─── API : Table ───────────────────────────────────────────────────────────────
ALLOWED_TABLES = {"reiatsu", "reiatsu_config", "mots_trouves"}
PK_MAP = {"reiatsu": "user_id", "reiatsu_config": "guild_id", "mots_trouves": "user_id"}

@app.route("/api/table/<table_name>")
@login_required
def api_table(table_name):
    if table_name not in ALLOWED_TABLES:
        return jsonify({"error": "Table non autorisée"}), 403
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM {table_name}")
    rows = cur.fetchall()
    columns = [d[0] for d in cur.description]
    conn.close()
    return jsonify({"columns": columns, "rows": rows, "pk": PK_MAP.get(table_name, columns[0])})


@app.route("/api/edit", methods=["POST"])
@login_required
def api_edit():
    data = request.json
    table = data.get("table")
    pk    = data.get("pk")
    pk_val= data.get("pk_val")
    col   = data.get("col")
    value = data.get("value")

    if table not in ALLOWED_TABLES:
        return jsonify({"ok": False, "error": "Table non autorisée"})
    if col == pk:
        return jsonify({"ok": False, "error": "Impossible de modifier la clé primaire"})

    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(f"UPDATE {table} SET {col} = ? WHERE {pk} = ?", (value, pk_val))
        conn.commit()
        conn.close()
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
# Référence vers le bot (injectée depuis bot.py)
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
        threading.Timer(1.5, restart_bot_process).start()
        return jsonify({"ok": True, "output": output + "\n⏳ Redémarrage dans 2s..."})

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
        return jsonify({"ok": True, "output": "⏳ Redémarrage en cours..."})

    return jsonify({"ok": False, "output": "Action inconnue"})


def restart_bot_process():
    """Relance le processus bot.py en remplaçant le processus actuel."""
    print("🔄 Redémarrage du bot via admin panel...")
    os.execv(sys.executable, [sys.executable, "bot.py"])


# ─── Lancement Flask (dans un thread) ─────────────────────────────────────────
def run_admin(port=5050):
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
