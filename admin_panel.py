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
import time

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


# ─── HTML Templates ────────────────────────────────────────────────────────────

HTML_LOGIN = """
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Kisuke Admin — Auth</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Syne+Mono&family=Syne:wght@700;800&family=DM+Mono:wght@300;400;500&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --void: #05050a;
    --surface: #0c0c14;
    --raised: #12121f;
    --line: #1e1e30;
    --line2: #2a2a42;
    --gold: #d4a843;
    --gold-dim: rgba(212,168,67,.12);
    --red: #e05555;
    --cyan: #4db8c8;
    --text: #b8b8d0;
    --dim: #484860;
  }

  body {
    background: var(--void);
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: 'DM Mono', monospace;
    overflow: hidden;
    position: relative;
  }

  /* Grid de fond */
  body::before {
    content: '';
    position: fixed; inset: 0;
    background-image:
      linear-gradient(rgba(212,168,67,.03) 1px, transparent 1px),
      linear-gradient(90deg, rgba(212,168,67,.03) 1px, transparent 1px);
    background-size: 48px 48px;
    pointer-events: none;
  }

  /* Vignette */
  body::after {
    content: '';
    position: fixed; inset: 0;
    background: radial-gradient(ellipse 60% 60% at 50% 50%, transparent 40%, var(--void) 100%);
    pointer-events: none;
  }

  .wrap {
    position: relative;
    z-index: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0;
    animation: fadeUp .5s ease both;
  }

  @keyframes fadeUp {
    from { opacity: 0; transform: translateY(20px); }
    to   { opacity: 1; transform: translateY(0); }
  }

  /* Glyphe décoratif */
  .glyph {
    font-family: 'Syne', sans-serif;
    font-weight: 800;
    font-size: 11px;
    letter-spacing: 8px;
    color: var(--dim);
    text-transform: uppercase;
    margin-bottom: 32px;
    display: flex;
    align-items: center;
    gap: 16px;
  }
  .glyph::before, .glyph::after {
    content: '';
    width: 40px; height: 1px;
    background: var(--line2);
  }

  .box {
    background: var(--surface);
    border: 1px solid var(--line);
    border-top: 2px solid var(--gold);
    width: 380px;
    padding: 40px;
    position: relative;
  }

  /* Coin décoratif */
  .box::after {
    content: '';
    position: absolute;
    bottom: -1px; right: -1px;
    width: 20px; height: 20px;
    border-bottom: 2px solid var(--gold);
    border-right: 2px solid var(--gold);
  }

  .box-title {
    font-family: 'Syne', sans-serif;
    font-weight: 800;
    font-size: 26px;
    letter-spacing: 4px;
    color: var(--gold);
    text-transform: uppercase;
    margin-bottom: 4px;
  }

  .box-sub {
    font-size: 10px;
    letter-spacing: 3px;
    color: var(--dim);
    text-transform: uppercase;
    margin-bottom: 36px;
    font-family: 'Syne Mono', monospace;
  }

  .field-label {
    font-size: 9px;
    letter-spacing: 3px;
    color: var(--dim);
    text-transform: uppercase;
    margin-bottom: 8px;
    display: block;
  }

  input[type=password] {
    width: 100%;
    background: var(--void);
    border: 1px solid var(--line2);
    color: var(--text);
    font-family: 'Syne Mono', monospace;
    font-size: 14px;
    padding: 12px 16px;
    outline: none;
    letter-spacing: 3px;
    transition: border-color .2s, box-shadow .2s;
    margin-bottom: 20px;
    border-radius: 0;
    -webkit-appearance: none;
  }

  input[type=password]:focus {
    border-color: var(--gold);
    box-shadow: 0 0 0 3px var(--gold-dim);
  }

  .btn-submit {
    width: 100%;
    background: var(--gold);
    color: var(--void);
    border: none;
    font-family: 'Syne', sans-serif;
    font-weight: 800;
    font-size: 13px;
    letter-spacing: 5px;
    text-transform: uppercase;
    padding: 14px;
    cursor: pointer;
    transition: opacity .2s, transform .1s;
    border-radius: 0;
  }

  .btn-submit:hover { opacity: .88; }
  .btn-submit:active { transform: scale(.99); }

  .error {
    background: rgba(224,85,85,.08);
    border: 1px solid rgba(224,85,85,.3);
    border-left: 3px solid var(--red);
    color: var(--red);
    font-size: 11px;
    padding: 10px 14px;
    margin-bottom: 20px;
    letter-spacing: .5px;
  }

  .footer-line {
    margin-top: 28px;
    font-size: 10px;
    color: var(--dim);
    letter-spacing: 2px;
    font-family: 'Syne Mono', monospace;
  }
</style>
</head>
<body>
<div class="wrap">
  <div class="glyph">Kisuke Admin</div>
  <div class="box">
    <div class="box-title">Accès</div>
    <div class="box-sub">Panneau d'administration</div>
    {% if error %}<div class="error">⚠ {{ error }}</div>{% endif %}
    <form method="POST">
      <label class="field-label">Mot de passe</label>
      <input type="password" name="password" placeholder="••••••••••••" autofocus>
      <button type="submit" class="btn-submit">Connexion</button>
    </form>
  </div>
  <div class="footer-line">v2.0 · Système réservé</div>
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
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Syne+Mono&family=Syne:wght@700;800&family=DM+Mono:ital,wght@0,300;0,400;0,500;1,300&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --void:    #05050a;
    --bg:      #080810;
    --surface: #0c0c17;
    --raised:  #101020;
    --hover:   #13132a;
    --line:    #1a1a2e;
    --line2:   #252540;
    --line3:   #303055;

    --gold:     #d4a843;
    --gold2:    #e8c060;
    --gold-dim: rgba(212,168,67,.1);
    --gold-glow:rgba(212,168,67,.2);

    --cyan:     #4ab4c4;
    --cyan-dim: rgba(74,180,196,.1);

    --green:    #3dba7a;
    --green-dim:rgba(61,186,122,.1);

    --red:      #e05555;
    --red-dim:  rgba(224,85,85,.1);

    --purple:   #9066d4;

    --text:     #c0c0d8;
    --text2:    #8888a8;
    --dim:      #3d3d5a;
    --dim2:     #5a5a7a;
  }

  html, body { height: 100%; }

  body {
    background: var(--bg);
    color: var(--text);
    font-family: 'DM Mono', monospace;
    font-size: 12px;
    display: flex;
    flex-direction: column;
    min-height: 100vh;
    overflow: hidden;
  }

  /* ──── SCROLLBAR ──────────────────────────────────────────────────────────── */
  ::-webkit-scrollbar { width: 4px; height: 4px; }
  ::-webkit-scrollbar-track { background: var(--surface); }
  ::-webkit-scrollbar-thumb { background: var(--line3); border-radius: 2px; }
  ::-webkit-scrollbar-thumb:hover { background: var(--dim2); }

  /* ──── HEADER ─────────────────────────────────────────────────────────────── */
  header {
    background: var(--surface);
    border-bottom: 1px solid var(--line);
    height: 52px;
    display: flex;
    align-items: center;
    padding: 0 20px;
    gap: 0;
    flex-shrink: 0;
    position: relative;
    z-index: 50;
  }

  /* barre top gold */
  header::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, var(--gold) 0%, transparent 60%);
  }

  .logo {
    font-family: 'Syne', sans-serif;
    font-weight: 800;
    font-size: 16px;
    letter-spacing: 5px;
    color: var(--gold2);
    text-transform: uppercase;
    margin-right: 32px;
    flex-shrink: 0;
  }

  .logo-tag {
    font-family: 'Syne Mono', monospace;
    font-size: 9px;
    letter-spacing: 2px;
    color: var(--dim2);
    margin-left: 10px;
    vertical-align: middle;
    text-transform: uppercase;
  }

  /* ──── NAV TABS ───────────────────────────────────────────────────────────── */
  nav {
    display: flex;
    gap: 2px;
    flex: 1;
    height: 100%;
    align-items: stretch;
  }

  .tab {
    padding: 0 22px;
    background: none;
    border: none;
    border-bottom: 2px solid transparent;
    color: var(--dim2);
    font-family: 'Syne Mono', monospace;
    font-size: 10px;
    letter-spacing: 3px;
    text-transform: uppercase;
    cursor: pointer;
    transition: color .15s, border-color .15s, background .15s;
    display: flex;
    align-items: center;
    gap: 8px;
    white-space: nowrap;
  }

  .tab .tab-ico { font-size: 13px; opacity: .6; }
  .tab:hover { color: var(--text); background: var(--hover); }
  .tab.active { color: var(--gold2); border-bottom-color: var(--gold); background: var(--gold-dim); }
  .tab.active .tab-ico { opacity: 1; }

  /* ──── HEADER RIGHT ───────────────────────────────────────────────────────── */
  .hdr-right {
    margin-left: auto;
    display: flex;
    align-items: center;
    gap: 16px;
    padding-left: 20px;
    border-left: 1px solid var(--line);
  }

  .status-pill {
    display: flex;
    align-items: center;
    gap: 7px;
    font-size: 10px;
    letter-spacing: 1.5px;
    color: var(--green);
    font-family: 'Syne Mono', monospace;
    text-transform: uppercase;
  }

  .status-dot {
    width: 6px; height: 6px;
    border-radius: 50%;
    background: var(--green);
    box-shadow: 0 0 8px var(--green);
    animation: pulse 2.5s ease-in-out infinite;
  }

  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.3} }

  .time-display {
    font-family: 'Syne Mono', monospace;
    font-size: 11px;
    color: var(--dim2);
    letter-spacing: 1px;
  }

  .btn-logout {
    background: none;
    border: 1px solid var(--line2);
    color: var(--dim2);
    font-family: 'Syne Mono', monospace;
    font-size: 9px;
    letter-spacing: 2.5px;
    text-transform: uppercase;
    padding: 5px 14px;
    cursor: pointer;
    transition: all .15s;
    border-radius: 0;
  }

  .btn-logout:hover { border-color: var(--red); color: var(--red); }

  /* ──── MAIN LAYOUT ────────────────────────────────────────────────────────── */
  .app-body {
    flex: 1;
    display: flex;
    overflow: hidden;
  }

  /* ──── SIDEBAR ────────────────────────────────────────────────────────────── */
  .sidebar {
    width: 220px;
    flex-shrink: 0;
    background: var(--surface);
    border-right: 1px solid var(--line);
    display: flex;
    flex-direction: column;
    overflow-y: auto;
    padding: 16px 0;
  }

  .sidebar-section-title {
    font-size: 9px;
    letter-spacing: 3px;
    color: var(--dim);
    text-transform: uppercase;
    padding: 12px 20px 6px;
    font-family: 'Syne Mono', monospace;
  }

  .sidebar-section-title:first-child { padding-top: 4px; }

  .sidebar-link {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 9px 20px;
    color: var(--text2);
    font-size: 11px;
    letter-spacing: 1px;
    cursor: pointer;
    transition: all .12s;
    border-left: 2px solid transparent;
    position: relative;
  }

  .sidebar-link .ico { font-size: 14px; flex-shrink: 0; width: 18px; text-align: center; }
  .sidebar-link:hover { color: var(--text); background: var(--hover); }
  .sidebar-link.active {
    color: var(--gold2);
    background: var(--gold-dim);
    border-left-color: var(--gold);
  }

  .sidebar-link .badge-count {
    margin-left: auto;
    background: var(--gold-dim);
    border: 1px solid rgba(212,168,67,.2);
    color: var(--gold);
    font-size: 9px;
    letter-spacing: 1px;
    padding: 1px 7px;
    border-radius: 20px;
  }

  .sidebar-divider {
    height: 1px;
    background: var(--line);
    margin: 12px 16px;
  }

  /* ──── CONTENT ────────────────────────────────────────────────────────────── */
  .content {
    flex: 1;
    overflow-y: auto;
    padding: 24px;
    display: flex;
    flex-direction: column;
    gap: 20px;
    min-width: 0;
  }

  /* ──── SECTIONS ───────────────────────────────────────────────────────────── */
  .section { display: none; flex-direction: column; gap: 20px; }
  .section.active { display: flex; }

  /* ──── CARDS ──────────────────────────────────────────────────────────────── */
  .card {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 2px;
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }

  .card-header {
    padding: 12px 20px;
    border-bottom: 1px solid var(--line);
    display: flex;
    align-items: center;
    gap: 12px;
    background: rgba(0,0,0,.2);
    flex-shrink: 0;
    min-height: 46px;
  }

  .card-title {
    font-family: 'Syne', sans-serif;
    font-weight: 700;
    font-size: 11px;
    letter-spacing: 4px;
    color: var(--text2);
    text-transform: uppercase;
  }

  .card-body { padding: 20px; flex: 1; }
  .card-body-flush { flex: 1; overflow: hidden; display: flex; flex-direction: column; }

  /* ──── TOOLBAR ────────────────────────────────────────────────────────────── */
  .toolbar {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
  }

  .toolbar { margin-left: auto; }

  /* ──── SELECT ─────────────────────────────────────────────────────────────── */
  select {
    background: var(--raised);
    border: 1px solid var(--line2);
    color: var(--text);
    font-family: 'Syne Mono', monospace;
    font-size: 11px;
    padding: 6px 10px;
    outline: none;
    cursor: pointer;
    transition: border-color .15s;
    border-radius: 0;
    -webkit-appearance: none;
    padding-right: 28px;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6'%3E%3Cpath d='M0 0l5 6 5-6z' fill='%233d3d5a'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 10px center;
  }

  select:focus { border-color: var(--gold); }

  /* ──── INPUTS ─────────────────────────────────────────────────────────────── */
  .input {
    background: var(--raised);
    border: 1px solid var(--line2);
    color: var(--text);
    font-family: 'DM Mono', monospace;
    font-size: 12px;
    padding: 7px 12px;
    outline: none;
    transition: border-color .15s;
    border-radius: 0;
  }

  .input:focus { border-color: var(--gold); }
  .input::placeholder { color: var(--dim); }

  textarea.input {
    resize: vertical;
    min-height: 120px;
    line-height: 1.7;
  }

  /* ──── BOUTONS ────────────────────────────────────────────────────────────── */
  .btn {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    padding: 7px 18px;
    font-family: 'Syne Mono', monospace;
    font-size: 10px;
    letter-spacing: 2px;
    text-transform: uppercase;
    border: none;
    cursor: pointer;
    transition: opacity .15s, transform .1s;
    white-space: nowrap;
    border-radius: 0;
    font-weight: 500;
  }

  .btn:hover { opacity: .82; }
  .btn:active { transform: scale(.98); }
  .btn:disabled { opacity: .35; cursor: not-allowed; transform: none; }

  .btn-gold    { background: var(--gold); color: var(--void); }
  .btn-cyan    { background: var(--cyan); color: var(--void); }
  .btn-green   { background: var(--green); color: var(--void); }
  .btn-red     { background: var(--red); color: #fff; }
  .btn-ghost   {
    background: transparent;
    border: 1px solid var(--line2);
    color: var(--text2);
    font-family: 'Syne Mono', monospace;
    font-size: 10px;
  }
  .btn-ghost:hover { border-color: var(--line3); color: var(--text); }

  /* ──── TABLE ──────────────────────────────────────────────────────────────── */
  .table-wrap { overflow: auto; flex: 1; }

  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 11.5px;
  }

  thead { position: sticky; top: 0; z-index: 10; }

  th {
    background: var(--raised);
    text-align: left;
    padding: 9px 14px;
    color: var(--dim2);
    font-size: 9px;
    letter-spacing: 2.5px;
    text-transform: uppercase;
    border-bottom: 1px solid var(--line2);
    white-space: nowrap;
    cursor: pointer;
    user-select: none;
    font-family: 'Syne Mono', monospace;
    transition: color .12s;
  }

  th:hover { color: var(--text2); }
  th.sort-asc::after { content: ' ↑'; color: var(--gold); font-size: 11px; }
  th.sort-desc::after { content: ' ↓'; color: var(--gold); font-size: 11px; }

  td {
    padding: 9px 14px;
    border-bottom: 1px solid var(--line);
    max-width: 220px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: var(--text);
    vertical-align: middle;
    line-height: 1;
    transition: background .08s;
  }

  tr:last-child td { border-bottom: none; }
  tr:hover td { background: var(--hover); }

  td.editable { cursor: pointer; }
  td.editable:hover { color: var(--gold2); }

  /* Colonne PK */
  td:first-child {
    color: var(--dim2);
    font-size: 11px;
  }

  /* ──── NULL / badges ──────────────────────────────────────────────────────── */
  .cell-null {
    color: var(--dim);
    font-style: italic;
    font-size: 10px;
  }

  .badge {
    display: inline-block;
    padding: 1px 8px;
    font-size: 9px;
    letter-spacing: 1px;
    text-transform: uppercase;
    font-family: 'Syne Mono', monospace;
    border-radius: 1px;
  }

  .badge-gold   { background: var(--gold-dim);  color: var(--gold);  border: 1px solid rgba(212,168,67,.25); }
  .badge-cyan   { background: var(--cyan-dim);  color: var(--cyan);  border: 1px solid rgba(74,180,196,.25); }
  .badge-green  { background: var(--green-dim); color: var(--green); border: 1px solid rgba(61,186,122,.25); }
  .badge-red    { background: var(--red-dim);   color: var(--red);   border: 1px solid rgba(224,85,85,.25); }

  /* ──── STAT CARDS (dashboard) ─────────────────────────────────────────────── */
  .stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
    gap: 14px;
  }

  .stat-card {
    background: var(--surface);
    border: 1px solid var(--line);
    padding: 18px 20px;
    position: relative;
    overflow: hidden;
  }

  .stat-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
  }

  .stat-card.gold::before { background: var(--gold); }
  .stat-card.cyan::before { background: var(--cyan); }
  .stat-card.green::before { background: var(--green); }
  .stat-card.purple::before { background: var(--purple); }
  .stat-card.red::before { background: var(--red); }

  .stat-label {
    font-family: 'Syne Mono', monospace;
    font-size: 9px;
    letter-spacing: 2.5px;
    color: var(--dim2);
    text-transform: uppercase;
    margin-bottom: 8px;
  }

  .stat-value {
    font-family: 'Syne', sans-serif;
    font-weight: 800;
    font-size: 28px;
    color: var(--text);
    line-height: 1;
    letter-spacing: -1px;
  }

  .stat-sub {
    font-size: 10px;
    color: var(--dim2);
    margin-top: 6px;
  }

  .stat-icon {
    position: absolute;
    bottom: 14px;
    right: 16px;
    font-size: 28px;
    opacity: .08;
  }

  /* ──── LOGS ───────────────────────────────────────────────────────────────── */
  .log-wrap {
    flex: 1;
    overflow-y: auto;
    padding: 16px 20px;
    font-size: 11.5px;
    line-height: 1.9;
    background: var(--void);
    font-family: 'DM Mono', monospace;
  }

  .log-line { color: var(--text2); display: flex; gap: 10px; align-items: baseline; }
  .log-line .log-ts { color: var(--dim); font-size: 10px; flex-shrink: 0; font-family: 'Syne Mono', monospace; }
  .log-line.err  .log-msg { color: var(--red); }
  .log-line.ok   .log-msg { color: var(--green); }
  .log-line.warn .log-msg { color: var(--gold); }
  .log-line.info .log-msg { color: var(--cyan); }

  .log-controls {
    padding: 10px 20px;
    border-top: 1px solid var(--line);
    display: flex;
    gap: 10px;
    align-items: center;
    background: var(--surface);
    flex-shrink: 0;
  }

  .log-filter {
    width: 200px;
  }

  .log-toggle {
    display: flex;
    align-items: center;
    gap: 8px;
    cursor: pointer;
    font-family: 'Syne Mono', monospace;
    font-size: 9px;
    letter-spacing: 2px;
    color: var(--dim2);
    text-transform: uppercase;
    user-select: none;
  }

  /* ──── ACTIONS ────────────────────────────────────────────────────────────── */
  .actions-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 16px;
  }

  .action-card {
    background: var(--surface);
    border: 1px solid var(--line);
    padding: 24px;
    display: flex;
    flex-direction: column;
    gap: 14px;
    position: relative;
    transition: border-color .2s;
  }

  .action-card:hover { border-color: var(--line2); }

  .action-header { display: flex; align-items: center; gap: 12px; }
  .action-icon { font-size: 20px; }
  .action-title {
    font-family: 'Syne', sans-serif;
    font-weight: 700;
    font-size: 13px;
    letter-spacing: 2px;
    color: var(--text);
    text-transform: uppercase;
  }

  .action-desc {
    font-size: 11px;
    color: var(--text2);
    line-height: 1.7;
    border-left: 2px solid var(--line2);
    padding-left: 12px;
  }

  .action-result {
    background: var(--void);
    border: 1px solid var(--line);
    padding: 12px 14px;
    font-size: 11px;
    line-height: 1.7;
    max-height: 180px;
    overflow-y: auto;
    display: none;
    color: var(--green);
    font-family: 'DM Mono', monospace;
  }

  .action-result.err { color: var(--red); }

  /* ──── SQL ────────────────────────────────────────────────────────────────── */
  .quick-queries {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }

  /* ──── MODAL ──────────────────────────────────────────────────────────────── */
  #modal-overlay {
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,.75);
    z-index: 500;
    align-items: center;
    justify-content: center;
    backdrop-filter: blur(2px);
  }

  #modal-overlay.open { display: flex; }

  .modal {
    background: var(--surface);
    border: 1px solid var(--line2);
    border-top: 2px solid var(--gold);
    padding: 32px;
    min-width: 380px;
    max-width: 580px;
    width: 90%;
    animation: modalIn .2s ease;
  }

  @keyframes modalIn {
    from { opacity: 0; transform: scale(.96) translateY(8px); }
    to   { opacity: 1; transform: none; }
  }

  .modal-title {
    font-family: 'Syne', sans-serif;
    font-weight: 800;
    font-size: 14px;
    letter-spacing: 4px;
    color: var(--gold2);
    text-transform: uppercase;
    margin-bottom: 6px;
  }

  .modal-meta {
    font-size: 10px;
    color: var(--dim2);
    letter-spacing: 1px;
    margin-bottom: 20px;
    font-family: 'Syne Mono', monospace;
  }

  .modal-input {
    width: 100%;
    margin-bottom: 20px;
    padding: 10px 14px;
    font-size: 13px;
  }

  .modal-footer { display: flex; gap: 10px; }

  /* ──── TOAST ──────────────────────────────────────────────────────────────── */
  #toast-container {
    position: fixed;
    bottom: 24px;
    right: 24px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    z-index: 999;
    pointer-events: none;
  }

  .toast-item {
    background: var(--raised);
    border: 1px solid var(--line2);
    border-left: 3px solid var(--gold);
    padding: 11px 18px;
    font-size: 11px;
    font-family: 'Syne Mono', monospace;
    letter-spacing: .5px;
    min-width: 220px;
    max-width: 320px;
    animation: toastIn .25s ease both, toastOut .3s ease 2.7s both;
    color: var(--text);
  }

  .toast-item.err { border-left-color: var(--red); }
  .toast-item.ok  { border-left-color: var(--green); }

  @keyframes toastIn  { from { opacity:0; transform: translateX(20px); } to { opacity:1; } }
  @keyframes toastOut { to   { opacity:0; transform: translateX(20px); } }

  /* ──── BREADCRUMB ─────────────────────────────────────────────────────────── */
  .breadcrumb {
    display: flex;
    align-items: center;
    gap: 8px;
    font-family: 'Syne Mono', monospace;
    font-size: 10px;
    color: var(--dim2);
    letter-spacing: 1.5px;
    padding: 0 0 16px;
    border-bottom: 1px solid var(--line);
    margin-bottom: 4px;
  }

  .breadcrumb span { color: var(--text2); }
  .breadcrumb .sep { color: var(--dim); }

  /* ──── TABLE INFO BAR ─────────────────────────────────────────────────────── */
  .table-info {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 8px 14px;
    background: var(--raised);
    border-bottom: 1px solid var(--line);
    font-size: 10px;
    color: var(--dim2);
    font-family: 'Syne Mono', monospace;
    flex-shrink: 0;
  }

  .table-info .ti-count { color: var(--text2); }

  /* ──── MISC ───────────────────────────────────────────────────────────────── */
  .row { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
  .ml-auto { margin-left: auto; }

  .section-title {
    font-family: 'Syne', sans-serif;
    font-weight: 800;
    font-size: 18px;
    letter-spacing: 3px;
    color: var(--text);
    text-transform: uppercase;
    margin-bottom: 4px;
  }

  .section-sub {
    font-size: 10px;
    color: var(--dim2);
    letter-spacing: 2px;
    font-family: 'Syne Mono', monospace;
    text-transform: uppercase;
    margin-bottom: 20px;
  }

  /* toggle switch */
  .switch {
    position: relative;
    display: inline-block;
    width: 30px;
    height: 16px;
  }
  .switch input { display: none; }
  .slider {
    position: absolute;
    inset: 0;
    background: var(--line2);
    cursor: pointer;
    transition: .2s;
    border-radius: 16px;
  }
  .slider::before {
    content: '';
    position: absolute;
    width: 10px; height: 10px;
    left: 3px; top: 3px;
    background: var(--dim2);
    transition: .2s;
    border-radius: 50%;
  }
  input:checked + .slider { background: var(--green-dim); border: 1px solid var(--green); }
  input:checked + .slider::before { transform: translateX(14px); background: var(--green); }
</style>
</head>
<body>

<!-- ─── HEADER ─────────────────────────────────────────────────────────────── -->
<header>
  <div class="logo">Kisuke <span class="logo-tag">Admin</span></div>

  <nav>
    <button class="tab active" data-tab="db" onclick="showTab('db', this)">
      <span class="tab-ico">⬡</span> Base de données
    </button>
    <button class="tab" data-tab="sql" onclick="showTab('sql', this)">
      <span class="tab-ico">◈</span> SQL
    </button>
    <button class="tab" data-tab="logs" onclick="showTab('logs', this)">
      <span class="tab-ico">▤</span> Logs
    </button>
    <button class="tab" data-tab="actions" onclick="showTab('actions', this)">
      <span class="tab-ico">⚙</span> Actions
    </button>
  </nav>

  <div class="hdr-right">
    <div class="status-pill">
      <div class="status-dot"></div>
      <span>En ligne</span>
    </div>
    <div class="time-display" id="clock">--:--:--</div>
    <form method="POST" action="/logout">
      <button class="btn-logout">Déconnexion</button>
    </form>
  </div>
</header>

<!-- ─── BODY ───────────────────────────────────────────────────────────────── -->
<div class="app-body">

  <!-- Sidebar -->
  <aside class="sidebar" id="sidebar">
    <div class="sidebar-section-title">Navigation</div>

    <div class="sidebar-link active" onclick="showTab('db', document.querySelector('[data-tab=db]'))">
      <span class="ico">⬡</span> Base de données
    </div>
    <div class="sidebar-link" onclick="showTab('sql', document.querySelector('[data-tab=sql]'))">
      <span class="ico">◈</span> Requête SQL
    </div>
    <div class="sidebar-link" onclick="showTab('logs', document.querySelector('[data-tab=logs]'))">
      <span class="ico">▤</span> Logs en direct
    </div>
    <div class="sidebar-link" onclick="showTab('actions', document.querySelector('[data-tab=actions]'))">
      <span class="ico">⚙</span> Actions bot
    </div>

    <div class="sidebar-divider"></div>
    <div class="sidebar-section-title">Requêtes rapides</div>

    <div class="sidebar-link" onclick="quickSQL('SELECT user_id, username, points, classe, niveau FROM reiatsu ORDER BY points DESC LIMIT 20')">
      <span class="ico">↑</span> Top 20 points
    </div>
    <div class="sidebar-link" onclick="quickSQL('SELECT * FROM reiatsu_config')">
      <span class="ico">⚙</span> Config guildes
    </div>
    <div class="sidebar-link" onclick="quickSQL('SELECT user_id, username, last_found_at FROM mots_trouves ORDER BY last_found_at DESC LIMIT 20')">
      <span class="ico">◷</span> Derniers mots
    </div>
    <div class="sidebar-link" onclick="quickSQL('SELECT COUNT(*) as total, SUM(points) as total_points FROM reiatsu')">
      <span class="ico">∑</span> Stats globales
    </div>
    <div class="sidebar-link" onclick="quickSQL('SELECT classe, COUNT(*) as nb FROM reiatsu GROUP BY classe ORDER BY nb DESC')">
      <span class="ico">≡</span> Par classe
    </div>
    <div class="sidebar-link" onclick="quickSQL('SELECT * FROM steam_keys ORDER BY won ASC')">
      <span class="ico">🔑</span> Clés Steam
    </div>

    <div class="sidebar-divider"></div>
    <div class="sidebar-section-title">Système</div>
    <div class="sidebar-link" id="sidebar-db-path" title="">
      <span class="ico">◉</span> <span id="sb-db-name">reiatsu.db</span>
      <span class="badge-count" id="sb-table-count">—</span>
    </div>
  </aside>

  <!-- Content -->
  <div class="content">

    <!-- ══ TAB : BASE DE DONNÉES ══════════════════════════════════════════════ -->
    <section class="section active" id="tab-db">
      <div class="breadcrumb">Admin <span class="sep">/</span> <span id="bc-table">Base de données</span></div>

      <!-- Stats rapides -->
      <div class="stats-grid" id="db-stats-grid"></div>

      <div class="card" style="flex:1;min-height:400px;overflow:hidden;display:flex;flex-direction:column;">
        <div class="card-header">
          <span class="card-title">Contenu</span>
          <div class="toolbar">
            <select id="tableSelect" onchange="loadTable()"></select>
            <input type="text" class="input" style="width:200px" id="filterInput" placeholder="Filtrer les lignes…" oninput="filterRows()">
            <button class="btn btn-ghost" onclick="loadTable()">↻</button>
          </div>
        </div>
        <div class="table-info">
          <span>Table : <strong class="ti-count" id="ti-table">—</strong></span>
          <span id="ti-pk" style="color:var(--dim)"></span>
          <span class="ml-auto" id="ti-count">—</span>
        </div>
        <div class="card-body-flush">
          <div class="table-wrap">
            <table id="mainTable">
              <thead id="tableHead"></thead>
              <tbody id="tableBody"></tbody>
            </table>
          </div>
        </div>
      </div>
    </section>

    <!-- ══ TAB : SQL ══════════════════════════════════════════════════════════ -->
    <section class="section" id="tab-sql">
      <div class="breadcrumb">Admin <span class="sep">/</span> <span>SQL Console</span></div>

      <div class="card">
        <div class="card-header">
          <span class="card-title">Requête SQL</span>
          <div class="toolbar">
            <button class="btn btn-ghost" onclick="document.getElementById('sqlQuery').value=''">Effacer</button>
            <button class="btn btn-gold" onclick="runSQL()">▶ Exécuter</button>
          </div>
        </div>
        <div class="card-body" style="display:flex;flex-direction:column;gap:16px">
          <textarea id="sqlQuery" class="input" rows="6" placeholder="SELECT * FROM reiatsu LIMIT 10;
-- Ctrl+Enter pour exécuter"></textarea>
          <div id="sqlResult"></div>
        </div>
      </div>
    </section>

    <!-- ══ TAB : LOGS ═════════════════════════════════════════════════════════ -->
    <section class="section" id="tab-logs" style="flex:1">
      <div class="breadcrumb">Admin <span class="sep">/</span> <span>Logs en direct</span></div>

      <div class="card" style="flex:1;min-height:500px;overflow:hidden;display:flex;flex-direction:column;">
        <div class="card-header">
          <span class="card-title">Sortie du bot</span>
          <div class="toolbar" style="margin-left:auto;gap:14px">
            <label class="log-toggle">
              <label class="switch"><input type="checkbox" id="autoRefresh" checked onchange="toggleAutoRefresh()"><span class="slider"></span></label>
              Auto-refresh
            </label>
            <input type="text" class="input log-filter" id="logFilter" placeholder="Filtrer les logs…" oninput="filterLogs()">
            <button class="btn btn-ghost" onclick="loadLogs()">↻ Refresh</button>
            <button class="btn btn-ghost" onclick="clearLogs()">✕ Vider</button>
          </div>
        </div>
        <div class="log-wrap" id="logBox"></div>
        <div class="log-controls">
          <span class="badge badge-cyan" id="log-count">0 lignes</span>
          <span style="font-size:10px;color:var(--dim2);font-family:'Syne Mono',monospace">Dernière mise à jour : <span id="log-ts">—</span></span>
          <label class="log-toggle ml-auto">
            <label class="switch"><input type="checkbox" id="autoScroll" checked><span class="slider"></span></label>
            Auto-scroll
          </label>
        </div>
      </div>
    </section>

    <!-- ══ TAB : ACTIONS ══════════════════════════════════════════════════════ -->
    <section class="section" id="tab-actions">
      <div class="breadcrumb">Admin <span class="sep">/</span> <span>Actions</span></div>

      <div class="actions-grid">

        <div class="action-card">
          <div class="action-header">
            <span class="action-icon">↓</span>
            <span class="action-title">Git Pull</span>
          </div>
          <div class="action-desc">Récupère les dernières modifications depuis GitHub sans redémarrer le bot.</div>
          <button class="btn btn-cyan" onclick="doAction('git_pull', this)">Lancer git pull</button>
          <div class="action-result" id="res-git_pull"></div>
        </div>

        <div class="action-card">
          <div class="action-header">
            <span class="action-icon">↓↻</span>
            <span class="action-title">Pull + Reload</span>
          </div>
          <div class="action-desc">Pull les mises à jour puis recharge tous les cogs sans interruption.</div>
          <button class="btn btn-cyan" onclick="doAction('git_pull_restart', this)">Pull + reload cogs</button>
          <div class="action-result" id="res-git_pull_restart"></div>
        </div>

        <div class="action-card">
          <div class="action-header">
            <span class="action-icon">↻</span>
            <span class="action-title">Reload Cogs</span>
          </div>
          <div class="action-desc">Recharge tous les cogs/commandes sans redémarrer le bot. Idéal pour tester des changements rapides.</div>
          <button class="btn btn-green" onclick="doAction('reload_cogs', this)">Reload cogs</button>
          <div class="action-result" id="res-reload_cogs"></div>
        </div>

        <div class="action-card">
          <div class="action-header">
            <span class="action-icon">⏻</span>
            <span class="action-title">Restart Bot</span>
          </div>
          <div class="action-desc">Redémarre le bot via start.sh. Le panel admin reste disponible pendant le redémarrage.</div>
          <button class="btn btn-red" onclick="confirmRestart()">Redémarrer</button>
          <div class="action-result" id="res-restart_bot"></div>
        </div>

      </div>
    </section>

  </div><!-- /content -->
</div><!-- /app-body -->

<!-- ─── MODAL EDIT ──────────────────────────────────────────────────────────── -->
<div id="modal-overlay">
  <div class="modal">
    <div class="modal-title">Modifier la valeur</div>
    <div class="modal-meta" id="modal-meta"></div>
    <input type="text" class="input modal-input" id="editValue">
    <input type="hidden" id="editTable">
    <input type="hidden" id="editPk">
    <input type="hidden" id="editPkVal">
    <input type="hidden" id="editCol">
    <div class="modal-footer">
      <button class="btn btn-gold" onclick="saveEdit()">Sauvegarder</button>
      <button class="btn btn-ghost" onclick="closeModal()">Annuler</button>
    </div>
  </div>
</div>

<!-- ─── MODAL CONFIRM ──────────────────────────────────────────────────────── -->
<div id="modal-confirm" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.8);z-index:600;align-items:center;justify-content:center;backdrop-filter:blur(2px)">
  <div class="modal" style="border-top-color:var(--red);">
    <div class="modal-title" style="color:var(--red)">Confirmation</div>
    <div class="modal-meta">Cette action va redémarrer le process du bot. Continuer ?</div>
    <div class="modal-footer" style="margin-top:20px">
      <button class="btn btn-red" onclick="doAction('restart_bot',this);document.getElementById('modal-confirm').style.display='none'">Redémarrer</button>
      <button class="btn btn-ghost" onclick="document.getElementById('modal-confirm').style.display='none'">Annuler</button>
    </div>
  </div>
</div>

<!-- ─── TOASTS ──────────────────────────────────────────────────────────────── -->
<div id="toast-container"></div>

<script>
// ══════════════════════════════════════════════════════════════════════════════
// UTILS
// ══════════════════════════════════════════════════════════════════════════════

function esc(s) {
  return String(s ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function toast(msg, type='') {
  const c = document.getElementById('toast-container');
  const el = document.createElement('div');
  el.className = 'toast-item' + (type ? ' ' + type : '');
  el.textContent = msg;
  c.appendChild(el);
  setTimeout(() => el.remove(), 3200);
}

function clock() {
  const d = new Date();
  document.getElementById('clock').textContent =
    d.toLocaleTimeString('fr-FR', {hour:'2-digit',minute:'2-digit',second:'2-digit'});
}
setInterval(clock, 1000); clock();

// ══════════════════════════════════════════════════════════════════════════════
// TABS
// ══════════════════════════════════════════════════════════════════════════════
function showTab(name, btn) {
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.sidebar-link').forEach(l => l.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
  if (btn) btn.classList.add('active');
  // sync sidebar
  const sideIdx = {'db':0,'sql':1,'logs':2,'actions':3};
  const links = document.querySelectorAll('.sidebar-link');
  if (sideIdx[name] !== undefined) links[sideIdx[name]]?.classList.add('active');
  if (name === 'db') loadTable();
  if (name === 'logs') loadLogs();
}

// ══════════════════════════════════════════════════════════════════════════════
// DATABASE
// ══════════════════════════════════════════════════════════════════════════════
let currentData = [], currentCols = [], currentTableName = '', currentPk = '';
let sortCol = null, sortDir = 1;
let rawLogs = [];

async function loadTableList() {
  const res = await fetch('/api/tables');
  const data = await res.json();
  const sel = document.getElementById('tableSelect');
  sel.innerHTML = data.tables.map(t => `<option value="${t}">${t}</option>`).join('');
  document.getElementById('sb-table-count').textContent = data.tables.length;
  loadTable();
}

async function loadTable() {
  const table = document.getElementById('tableSelect').value;
  if (!table) return;
  document.getElementById('ti-table').textContent = table;
  document.getElementById('bc-table').textContent = table;
  const res = await fetch('/api/table/' + table);
  const data = await res.json();
  currentData = data.rows;
  currentCols = data.columns;
  currentTableName = table;
  currentPk = data.pk;
  sortCol = null;
  renderTable(data.columns, data.rows);
  document.getElementById('ti-pk').textContent = 'PK: ' + data.pk;
  document.getElementById('ti-count').textContent = data.rows.length + ' entrée' + (data.rows.length > 1 ? 's' : '');
  updateStatCards(data);
}

function updateStatCards(data) {
  const grid = document.getElementById('db-stats-grid');
  const colors = ['gold','cyan','green','purple','red'];
  const icons = ['◈','∑','↑','⚙','★'];
  // Quelques colonnes numériques
  const numCols = data.columns
    .map((c,i) => ({name:c, idx:i}))
    .filter(({name}) => /point|niveau|count|total|nb|score/i.test(name))
    .slice(0, 4);

  const cards = [
    { label:'Total entrées', value: data.rows.length, icon:'⬡', color:'gold' },
    { label:'Colonnes', value: data.columns.length, icon:'◈', color:'cyan' },
  ];

  numCols.forEach(({name, idx}, i) => {
    const vals = data.rows.map(r => parseFloat(r[idx])).filter(v => !isNaN(v));
    if (vals.length) {
      const sum = vals.reduce((a,b)=>a+b,0);
      cards.push({ label: name.toUpperCase(), value: Math.round(sum).toLocaleString('fr'), icon: icons[i+2], color: colors[i+2] });
    }
  });

  grid.innerHTML = cards.map(c => `
    <div class="stat-card ${c.color}">
      <div class="stat-label">${esc(c.label)}</div>
      <div class="stat-value">${esc(c.value)}</div>
      <div class="stat-icon">${c.icon}</div>
    </div>
  `).join('');
}

function sortBy(colIndex) {
  if (sortCol === colIndex) sortDir *= -1; else { sortCol = colIndex; sortDir = 1; }
  const sorted = [...currentData].sort((a, b) => {
    const va = a[colIndex] ?? '', vb = b[colIndex] ?? '';
    const na = parseFloat(va), nb = parseFloat(vb);
    if (!isNaN(na) && !isNaN(nb)) return (na - nb) * sortDir;
    return String(va).localeCompare(String(vb), 'fr', {sensitivity:'base'}) * sortDir;
  });
  renderTable(currentCols, sorted);
}

function renderTable(cols, rows) {
  const head = document.getElementById('tableHead');
  const body = document.getElementById('tableBody');
  const htr = document.createElement('tr');
  cols.forEach((c, i) => {
    const th = document.createElement('th');
    th.textContent = c;
    if (sortCol === i) th.className = sortDir === 1 ? 'sort-asc' : 'sort-desc';
    th.onclick = () => sortBy(i);
    htr.appendChild(th);
  });
  head.innerHTML = ''; head.appendChild(htr);
  body.innerHTML = '';
  rows.forEach(row => {
    const tr = document.createElement('tr');
    cols.forEach((col, i) => {
      const val = row[i];
      const td = document.createElement('td');
      const isPk = col === currentPk;
      if (val === null || val === undefined || val === '') {
        td.innerHTML = '<span class="cell-null">null</span>';
      } else {
        td.textContent = val;
        td.title = String(val);
      }
      if (!isPk) {
        td.className = 'editable';
        td.onclick = () => openEdit(currentTableName, currentPk, String(row[0]), col, String(val ?? ''));
      }
      tr.appendChild(td);
    });
    body.appendChild(tr);
  });
  filterRows();
}

function filterRows() {
  const f = document.getElementById('filterInput').value.toLowerCase();
  document.querySelectorAll('#tableBody tr').forEach(r => {
    r.style.display = f === '' || r.textContent.toLowerCase().includes(f) ? '' : 'none';
  });
}

// ══════════════════════════════════════════════════════════════════════════════
// MODAL EDIT
// ══════════════════════════════════════════════════════════════════════════════
function openEdit(table, pk, pkVal, col, val) {
  document.getElementById('editTable').value = table;
  document.getElementById('editPk').value = pk;
  document.getElementById('editPkVal').value = pkVal;
  document.getElementById('editCol').value = col;
  document.getElementById('editValue').value = val;
  document.getElementById('modal-meta').textContent = `${table} · ${col} · ID ${pkVal}`;
  document.getElementById('modal-overlay').classList.add('open');
  setTimeout(() => document.getElementById('editValue').focus(), 50);
}

function closeModal() {
  document.getElementById('modal-overlay').classList.remove('open');
}

async function saveEdit() {
  const payload = {
    table: document.getElementById('editTable').value,
    pk:    document.getElementById('editPk').value,
    pk_val:document.getElementById('editPkVal').value,
    col:   document.getElementById('editCol').value,
    value: document.getElementById('editValue').value,
  };
  const res = await fetch('/api/edit', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
  const data = await res.json();
  closeModal();
  if (data.ok) { toast('✓ Modifié avec succès', 'ok'); loadTable(); }
  else toast('✕ ' + data.error, 'err');
}

document.getElementById('modal-overlay').onclick = e => {
  if (e.target === document.getElementById('modal-overlay')) closeModal();
};

document.addEventListener('keydown', e => {
  if (e.key === 'Escape') closeModal();
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
    if (document.getElementById('modal-overlay').classList.contains('open')) saveEdit();
    else if (document.getElementById('tab-sql').classList.contains('active')) runSQL();
  }
});

// ══════════════════════════════════════════════════════════════════════════════
// SQL
// ══════════════════════════════════════════════════════════════════════════════
function quickSQL(q) {
  showTab('sql', document.querySelector('[data-tab=sql]'));
  document.getElementById('sqlQuery').value = q;
  runSQL();
}

async function runSQL() {
  const q = document.getElementById('sqlQuery').value.trim();
  if (!q) return;
  const el = document.getElementById('sqlResult');
  el.innerHTML = '<span style="color:var(--dim2);font-size:11px">⏳ Exécution…</span>';
  const res = await fetch('/api/sql', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query:q})});
  const data = await res.json();

  if (data.error) {
    el.innerHTML = `<div style="background:var(--void);border:1px solid var(--red);border-left:3px solid var(--red);padding:12px 16px;color:var(--red);font-size:11px;margin-top:4px">✕ ${esc(data.error)}</div>`;
    return;
  }

  if (data.columns) {
    let html = `<div class="table-wrap" style="margin-top:8px;border:1px solid var(--line);max-height:400px;overflow:auto"><table>`;
    html += `<thead><tr>${data.columns.map(c=>`<th>${esc(c)}</th>`).join('')}</tr></thead><tbody>`;
    html += data.rows.map(r=>`<tr>${r.map(v=>`<td>${v===null?'<span class="cell-null">null</span>':esc(v)}</td>`).join('')}</tr>`).join('');
    html += `</tbody></table></div>`;
    html += `<div style="margin-top:8px;font-size:10px;color:var(--dim2);font-family:'Syne Mono',monospace">${data.rows.length} résultat(s)</div>`;
    el.innerHTML = html;
  } else {
    el.innerHTML = `<div style="background:var(--void);border:1px solid var(--green);border-left:3px solid var(--green);padding:12px 16px;color:var(--green);font-size:11px;margin-top:4px">✓ ${esc(data.message)}</div>`;
  }
}

// ══════════════════════════════════════════════════════════════════════════════
// LOGS
// ══════════════════════════════════════════════════════════════════════════════
let autoRefreshTimer = null;

async function loadLogs() {
  const res = await fetch('/api/logs');
  const data = await res.json();
  rawLogs = data.logs;
  const ts = new Date().toLocaleTimeString('fr-FR');
  document.getElementById('log-ts').textContent = ts;
  document.getElementById('log-count').textContent = rawLogs.length + ' ligne' + (rawLogs.length > 1 ? 's' : '');
  renderLogs();
}

function renderLogs() {
  const filter = document.getElementById('logFilter').value.toLowerCase();
  const box = document.getElementById('logBox');
  const wasAtBottom = box.scrollHeight - box.clientHeight <= box.scrollTop + 30;

  const lines = filter ? rawLogs.filter(l => l.toLowerCase().includes(filter)) : rawLogs;

  box.innerHTML = lines.map(line => {
    let cls = 'log-line';
    if (/❌|ERROR|error|Exception/i.test(line)) cls += ' err';
    else if (/✅|Loaded|Connecté|OK|success/i.test(line)) cls += ' ok';
    else if (/⚠|WARNING|warn/i.test(line)) cls += ' warn';
    else if (/INFO|→|←/i.test(line)) cls += ' info';

    // Essaye d'extraire timestamp
    const tsMatch = line.match(/\d{2}:\d{2}:\d{2}/);
    const ts = tsMatch ? `<span class="log-ts">${tsMatch[0]}</span>` : '';
    const msg = line.replace(/\d{2}:\d{2}:\d{2}\s*/, '');

    return `<div class="${cls}">${ts}<span class="log-msg">${esc(msg)}</span></div>`;
  }).join('');

  const autoScroll = document.getElementById('autoScroll').checked;
  if ((wasAtBottom || autoScroll) && !filter) box.scrollTop = box.scrollHeight;
}

function filterLogs() { renderLogs(); }

function clearLogs() {
  rawLogs = [];
  renderLogs();
  fetch('/api/logs/clear', {method:'POST'});
}

function toggleAutoRefresh() {
  const on = document.getElementById('autoRefresh').checked;
  clearInterval(autoRefreshTimer);
  if (on) autoRefreshTimer = setInterval(loadLogs, 2000);
}

// ══════════════════════════════════════════════════════════════════════════════
// ACTIONS
// ══════════════════════════════════════════════════════════════════════════════
function confirmRestart() {
  document.getElementById('modal-confirm').style.display = 'flex';
}

async function doAction(action, btn) {
  const resBox = document.getElementById('res-' + action);
  resBox.style.display = 'block';
  resBox.className = 'action-result';
  resBox.textContent = '⏳ En cours…';
  if (btn) btn.disabled = true;
  try {
    const res = await fetch('/api/action/' + action, {method:'POST'});
    const data = await res.json();
    resBox.textContent = data.output || data.message || '';
    if (!data.ok) resBox.classList.add('err');
    else toast('✓ ' + action + ' terminé', 'ok');
  } catch(e) {
    resBox.textContent = '✕ Erreur réseau';
    resBox.classList.add('err');
    toast('✕ Erreur réseau', 'err');
  }
  if (btn) btn.disabled = false;
}

// ══════════════════════════════════════════════════════════════════════════════
// INIT
// ══════════════════════════════════════════════════════════════════════════════
loadTableList();
autoRefreshTimer = setInterval(loadLogs, 2000);
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
