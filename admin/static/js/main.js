// ================================================================================
// 📌 main.js — Script principal du panel admin Kisuke
// Objectif : Logique front (onglets, thème, DB, SQL, logs, actions, backups, .env)
// Accès : Admin uniquement (chargé par templates/main.html)
// ================================================================================

const $ = id => document.getElementById(id);
const CSRF = document.querySelector('meta[name="csrf-token"]')?.content || '';
const esc = s => String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
const fmtSize = kb => kb < 1024 ? `${kb} Ko` : `${(kb / 1024).toFixed(1)} Mo`;

// ================================================================================
// 🌐 API (GET si pas de body, POST sinon — token CSRF inclus)
// ================================================================================
async function api(url, body) {
  const opt = { method: body === undefined ? 'GET' : 'POST', headers: { 'X-CSRFToken': CSRF } };
  if (body instanceof FormData) opt.body = body;
  else if (body !== undefined) {
    opt.headers['Content-Type'] = 'application/json';
    opt.body = JSON.stringify(body);
  }
  let res;
  try { res = await fetch(url, opt); } catch { return { ok: false, error: 'Erreur réseau' }; }
  if (res.status === 401 || (res.redirected && res.url.includes('/login'))) {
    location.href = '/login';
    return { ok: false, error: 'Non connecté' };
  }
  try { return await res.json(); } catch { return { ok: false, error: `Réponse invalide (${res.status})` }; }
}

// ================================================================================
// 🔔 Notifications + confirmation
// ================================================================================
let noticeTimer;
function notify(msg, type = 'ok') {
  const n = $('notice');
  n.className = 'note float' + (type === 'ok' ? ' ok' : type === 'ko' ? ' ko' : '');
  $('noticeIcon').textContent = { ok: '✓', ko: '✕', warn: '⚠' }[type] || '•';
  $('noticeText').textContent = msg;
  n.hidden = false;
  clearTimeout(noticeTimer);
  noticeTimer = setTimeout(() => { n.hidden = true; }, 3800);
}

function confirmAsk(text, label = 'Confirmer') {
  return new Promise(resolve => {
    const box = $('confirmBox');
    $('confirmText').textContent = text;
    $('confirmOk').textContent = label;
    const done = v => { box.hidden = true; resolve(v); };
    $('confirmOk').onclick = () => done(true);
    $('confirmCancel').onclick = () => done(false);
    box.hidden = false;
  });
}

// ================================================================================
// 🕒 Horloge + thème
// ================================================================================
function tick() {
  $('clock').textContent = new Date().toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}
setInterval(tick, 1000); tick();

function setTheme(t) {
  document.documentElement.setAttribute('data-theme', t);
  localStorage.setItem('kisuke-theme', t);
  $('themeToggle').textContent = t === 'dark' ? '☀' : '☾';
}
setTheme(document.documentElement.getAttribute('data-theme') || 'dark');
$('themeToggle').onclick = () => setTheme(document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark');

// ================================================================================
// 📂 Onglets
// ================================================================================
let activeTab = 'db';
const loaders = {
  db: () => loadTableList(),
  logs: () => loadLogs(),
  backup: () => { loadBackups(); loadBackupSettings(); },
  env: () => { if (!envDirtyCount()) loadEnv(); },
};

function showTab(name) {
  if (!$('tab-' + name)) name = 'db';
  activeTab = name;
  document.querySelectorAll('.adm-sec').forEach(s => s.classList.toggle('active', s.id === 'tab-' + name));
  document.querySelectorAll('.adm-side a[data-tab]').forEach(a => a.classList.toggle('active', a.dataset.tab === name));
  history.replaceState(null, '', '#' + name);
  loaders[name]?.();
}
document.querySelectorAll('.adm-side a[data-tab]').forEach(a => a.onclick = () => showTab(a.dataset.tab));

// ================================================================================
// 🗄️ BASE DE DONNÉES
// ================================================================================
const S = { table: '', cols: [], rows: [], pk: '', pkIdx: 0, sortCol: null, sortDir: 1 };
const ROW_LIMIT = 1000;
let edit = null;

async function loadTableList() {
  const data = await api('/api/tables');
  const sel = $('tableSelect');
  const prev = sel.value;
  sel.innerHTML = (data.tables || []).map(t => `<option value="${esc(t)}">${esc(t)}</option>`).join('');
  $('sb-table-count').textContent = (data.tables || []).length;
  if ((data.tables || []).includes(prev)) sel.value = prev;
  loadTable();
}

async function loadTable() {
  const table = $('tableSelect').value;
  closeEdit();
  if (!table) {
    Object.assign(S, { table: '', cols: [], rows: [], pk: '' });
    $('db-sub').textContent = 'Aucune table';
    $('db-kpis').innerHTML = '';
    $('tableHead').innerHTML = $('tableBody').innerHTML = '';
    $('ti-info').textContent = '—';
    return;
  }
  const data = await api('/api/table/' + encodeURIComponent(table));
  if (data.error) return notify(data.error, 'ko');
  Object.assign(S, { table, cols: data.columns, rows: data.rows, pk: data.pk, sortCol: null, sortDir: 1 });
  S.pkIdx = Math.max(0, S.cols.indexOf(S.pk));
  $('db-sub').textContent = `${table} · clé primaire : ${S.pk}`;
  renderKpis();
  renderTable();
}

function renderKpis() {
  const kpi = (label, value, hint = '') =>
    `<div class="kpi"><div class="kpi-label">${esc(label)}</div><div class="kpi-value">${esc(value)}</div><div class="kpi-hint">${esc(hint)}</div></div>`;
  let html = kpi('Entrées', S.rows.length.toLocaleString('fr')) + kpi('Colonnes', S.cols.length);
  S.cols.forEach((name, i) => {
    if (html.split('class="kpi"').length > 5 || !/point|niveau|count|total|nb|score/i.test(name)) return;
    const vals = S.rows.map(r => parseFloat(r[i])).filter(v => !isNaN(v));
    if (vals.length) html += kpi(name, Math.round(vals.reduce((a, b) => a + b, 0)).toLocaleString('fr'), 'somme');
  });
  $('db-kpis').innerHTML = html;
}

function renderTable() {
  const f = $('filterInput').value.toLowerCase();
  let order = S.rows.map((_, i) => i);
  if (f) order = order.filter(i => S.rows[i].some(v => String(v ?? '').toLowerCase().includes(f)));
  if (S.sortCol !== null) {
    const c = S.sortCol, d = S.sortDir;
    order.sort((a, b) => {
      const va = S.rows[a][c] ?? '', vb = S.rows[b][c] ?? '';
      const na = parseFloat(va), nb = parseFloat(vb);
      if (!isNaN(na) && !isNaN(nb)) return (na - nb) * d;
      return String(va).localeCompare(String(vb), 'fr', { sensitivity: 'base' }) * d;
    });
  }
  const shown = order.slice(0, ROW_LIMIT);

  $('tableHead').innerHTML = '<tr>' + S.cols.map((c, i) =>
    `<th class="sortable${S.sortCol === i ? (S.sortDir === 1 ? ' asc' : ' desc') : ''}" data-c="${i}">${esc(c)}</th>`).join('') + '</tr>';

  $('tableBody').innerHTML = shown.map(r => '<tr>' + S.cols.map((col, c) => {
    const v = S.rows[r][c];
    const edit = c === S.pkIdx ? '' : ' editable';
    if (v === null || v === undefined || v === '')
      return `<td class="${edit}" data-r="${r}" data-c="${c}"><span class="mute">null</span></td>`;
    return `<td class="${edit}" data-r="${r}" data-c="${c}" title="${esc(v)}">${esc(v)}</td>`;
  }).join('') + '</tr>').join('');

  let info = `${S.rows.length} entrée${S.rows.length > 1 ? 's' : ''}`;
  if (f) info += ` · ${order.length} correspondante${order.length > 1 ? 's' : ''}`;
  if (order.length > ROW_LIMIT) info += ` · affichage des ${ROW_LIMIT} premières (utilise le filtre ou la console SQL)`;
  $('ti-info').textContent = info;
}

$('tableHead').onclick = e => {
  const th = e.target.closest('th[data-c]');
  if (!th) return;
  const c = +th.dataset.c;
  if (S.sortCol === c) S.sortDir *= -1; else { S.sortCol = c; S.sortDir = 1; }
  renderTable();
};
$('tableBody').onclick = e => {
  const td = e.target.closest('td.editable');
  if (td) openEdit(+td.dataset.r, +td.dataset.c);
};
$('tableSelect').onchange = loadTable;
$('filterInput').oninput = renderTable;
$('reloadTable').onclick = loadTable;

$('deleteTableBtn').onclick = async () => {
  const t = $('tableSelect').value;
  if (!t) return notify('Aucune table sélectionnée', 'ko');
  if (!await confirmAsk(`Supprimer définitivement la table « ${t} » et toutes ses données ? Irréversible.`, 'Supprimer')) return;
  const d = await api('/api/table/' + encodeURIComponent(t) + '/delete', {});
  if (d.ok) { notify(`Table « ${t} » supprimée`); loadTableList(); } else notify(d.error, 'ko');
};

// ── Édition d'une cellule ─────────────────────────────────────────────────────
function openEdit(r, c) {
  edit = { r, c };
  $('editMeta').textContent = `${S.table} · ${S.cols[c]} · ${S.pk} = ${S.rows[r][S.pkIdx]}`;
  $('editValue').value = S.rows[r][c] ?? '';
  $('editPanel').hidden = false;
  $('editPanel').scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  $('editValue').focus();
}
function closeEdit() { edit = null; $('editPanel').hidden = true; }

async function saveEdit() {
  if (!edit) return;
  const d = await api('/api/edit', {
    table: S.table, pk: S.pk, pk_val: String(S.rows[edit.r][S.pkIdx]),
    col: S.cols[edit.c], value: $('editValue').value,
  });
  if (d.ok) { notify('Modifié avec succès'); loadTable(); } else notify(d.error, 'ko');
}
$('editSave').onclick = saveEdit;
$('editCancel').onclick = closeEdit;
$('editValue').onkeydown = e => { if (e.key === 'Enter') saveEdit(); };

// ================================================================================
// ◈ SQL
// ================================================================================
async function runSQL() {
  const q = $('sqlQuery').value.trim();
  if (!q) return;
  const el = $('sqlResult');
  el.innerHTML = '<div class="note"><span>⏳</span><span class="note-body">Exécution…</span></div>';
  const d = await api('/api/sql', { query: q });

  if (d.error) {
    el.innerHTML = `<div class="note ko"><span>✕</span><span class="note-body">${esc(d.error)}</span></div>`;
    return;
  }
  if (d.columns) {
    el.innerHTML = `<div class="panel"><div class="tbl"><table>
      <thead><tr>${d.columns.map(c => `<th>${esc(c)}</th>`).join('')}</tr></thead>
      <tbody>${d.rows.map(r => '<tr>' + r.map(v => v === null ? '<td class="mute">null</td>' : `<td title="${esc(v)}">${esc(v)}</td>`).join('') + '</tr>').join('')}</tbody>
    </table></div><div class="panel-foot">${d.rows.length} résultat(s)${d.truncated ? ' — tronqué, ajoute un LIMIT' : ''}</div></div>`;
  } else {
    el.innerHTML = `<div class="note ok"><span>✓</span><span class="note-body">${esc(d.message)}</span></div>`;
  }
  if (/\b(drop|create|alter)\s+table/i.test(q)) loadTableList();
}
$('sqlRun').onclick = runSQL;
$('sqlClear').onclick = () => { $('sqlQuery').value = ''; $('sqlResult').innerHTML = ''; };
$('sqlQuery').onkeydown = e => { if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') runSQL(); };
document.querySelectorAll('[data-q]').forEach(b => b.onclick = () => { $('sqlQuery').value = b.dataset.q; runSQL(); });

// ================================================================================
// ▤ LOGS
// ================================================================================
let rawLogs = [];
const LOG_REFRESH_MS = 60000;

async function loadLogs() {
  const d = await api('/api/logs');
  if (!d.logs) return;
  rawLogs = d.logs;
  $('log-ts').textContent = new Date().toLocaleTimeString('fr-FR');
  $('log-count').textContent = `${rawLogs.length} ligne${rawLogs.length > 1 ? 's' : ''}`;
  renderLogs();
}

function logLevel(line) {
  if (/❌|error|exception|traceback/i.test(line)) return 'err';
  if (/⚠|warn/i.test(line)) return 'warn';
  return 'info';
}

function renderLogs() {
  const f = $('logFilter').value.toLowerCase();
  const level = $('logLevel').value;
  const box = $('logBox');
  const lines = rawLogs.filter(l => (!f || l.toLowerCase().includes(f)) && (level === 'all' || logLevel(l) === level));

  box.innerHTML = lines.map(line => {
    const lv = logLevel(line);
    const t = line.match(/\d{2}:\d{2}:\d{2}/);
    const msg = line.replace(/\d{2}:\d{2}:\d{2}\s*/, '');
    return `<div class="logline ${lv}"><span class="t">${t ? t[0] : ''}</span><span class="t">${lv === 'info' ? '' : lv === 'err' ? 'ERR' : 'WARN'}</span><span class="m">${esc(msg)}</span></div>`;
  }).join('');
  if ($('autoScroll').checked) box.scrollTop = box.scrollHeight;
}

$('logFilter').oninput = renderLogs;
$('logLevel').onchange = renderLogs;
$('logReload').onclick = loadLogs;
$('logClear').onclick = async () => { await api('/api/logs/clear', {}); rawLogs = []; $('log-count').textContent = '0 ligne'; renderLogs(); };

// Un seul timer : actif uniquement si l'onglet Logs est affiché et la page visible
setInterval(() => {
  if (activeTab === 'logs' && !document.hidden && $('autoRefresh').checked) loadLogs();
}, LOG_REFRESH_MS);

// ================================================================================
// ⚙️ ACTIONS
// ================================================================================
async function doAction(action, btn) {
  const out = $('res-' + action);
  out.hidden = false;
  out.className = 'out';
  out.textContent = '⏳ En cours…';
  if (btn) btn.disabled = true;
  const d = await api('/api/action/' + action, {});
  out.textContent = d.output || d.error || '';
  if (d.ok) notify(`${action} terminé`); else { out.classList.add('err'); notify(`${action} : échec`, 'ko'); }
  if (btn) btn.disabled = false;
}
document.querySelectorAll('[data-action]').forEach(b => b.onclick = () => doAction(b.dataset.action, b));

async function restartBot() {
  if (!await confirmAsk('Redémarrer le process du bot ? Le panel changera d\'URL.', 'Redémarrer')) return false;
  await api('/api/action/restart_bot', {});
  notify('Redémarrage en cours — récupère la nouvelle URL du panel', 'warn');
  return true;
}
$('restartBtn').onclick = restartBot;

// ================================================================================
// ⛁ BACKUPS
// ================================================================================
async function loadBackups() {
  const d = await api('/api/backup/list');
  if (!d.backups) return;
  $('sb-backup-count').textContent = d.backups.length;
  const total = d.backups.reduce((a, b) => a + b.size_kb, 0);
  const kpi = (l, v, h = '') => `<div class="kpi"><div class="kpi-label">${l}</div><div class="kpi-value">${esc(v)}</div><div class="kpi-hint">${esc(h)}</div></div>`;
  $('bk-kpis').innerHTML =
    kpi('Backups', d.backups.length, `max ${d.max}`) +
    kpi('Espace utilisé', fmtSize(Math.round(total * 10) / 10)) +
    kpi('Dernier backup', d.backups[0]?.date || '—') +
    kpi('Automatique', d.auto_hours > 0 ? `${d.auto_hours} h` : 'Désactivé');

  $('bkBody').innerHTML = d.backups.length ? d.backups.map(b => `<tr>
    <td class="mono">${esc(b.name)}</td><td class="mute">${esc(b.date)}</td><td class="num mono">${fmtSize(b.size_kb)}</td>
    <td class="act"><div class="toolbar" style="justify-content:flex-end">
      <a class="btn btn-ghost btn-sm" href="/api/backup/download/${encodeURIComponent(b.name)}">↓</a>
      <button class="btn btn-ghost btn-sm" data-restore="${esc(b.name)}">↺ Restaurer</button>
      <button class="btn btn-danger btn-sm" data-del="${esc(b.name)}">🗑</button>
    </div></td></tr>`).join('') : '<tr><td colspan="4" class="mute">Aucun backup pour le moment.</td></tr>';
}

$('bkBody').onclick = async e => {
  const r = e.target.closest('[data-restore]'), d = e.target.closest('[data-del]');
  if (r) {
    if (!await confirmAsk(`Remplacer la base actuelle par ${r.dataset.restore} ? Une copie de sécurité est créée avant.`, 'Restaurer')) return;
    const res = await api(`/api/backup/${encodeURIComponent(r.dataset.restore)}/restore`, {});
    res.ok ? notify(res.message) : notify(res.error, 'ko');
    loadBackups(); loadTableList();
  } else if (d) {
    if (!await confirmAsk(`Supprimer ${d.dataset.del} ?`, 'Supprimer')) return;
    const res = await api(`/api/backup/${encodeURIComponent(d.dataset.del)}/delete`, {});
    res.ok ? notify('Backup supprimé') : notify(res.error, 'ko');
    loadBackups();
  }
};

$('bkCreate').onclick = async () => {
  const btn = $('bkCreate'), out = $('res-backup');
  btn.disabled = true;
  out.hidden = false; out.className = 'out'; out.textContent = '⏳ Génération du backup…';
  const d = await api('/api/backup', {});
  if (d.ok) {
    out.textContent = `✓ ${d.filename} (${fmtSize(d.size_kb)})` + (d.discord_sent ? ' — envoyé sur Discord ✓' : ` — ⚠ pas envoyé sur Discord (${d.discord_error})`);
    notify(d.discord_sent ? 'Backup créé et envoyé sur Discord' : 'Backup créé (pas envoyé sur Discord)', d.discord_sent ? 'ok' : 'warn');
    loadBackups();
  } else {
    out.textContent = '✕ ' + (d.error || 'Erreur inconnue'); out.classList.add('err');
    notify('Erreur backup', 'ko');
  }
  btn.disabled = false;
};

$('bkImport').onclick = () => $('bkFile').click();
$('bkFile').onchange = async () => {
  const file = $('bkFile').files[0];
  if (!file) return;
  const fd = new FormData(); fd.append('file', file);
  const d = await api('/api/backup/import', fd);
  $('bkFile').value = '';
  d.ok ? notify(`Importé : ${d.filename} — clique sur Restaurer pour l'appliquer`) : notify(d.error, 'ko');
  loadBackups();
};

// ── Réglages backup ───────────────────────────────────────────────────────────
async function loadBackupSettings() {
  const d = await api('/api/backup/settings');
  if (!d.settings) return;
  $('bkSettings').innerHTML = d.settings.map(s => `<div class="row-set">
    <div><div class="name">${esc(s.label)}</div><div class="desc">${esc(s.desc)}</div></div>
    <div class="ctrl"><input class="field" data-key="${esc(s.key)}" type="${s.sensitive ? 'password' : s.type}" ${s.type === 'number' ? 'min="0" step="any"' : ''}
      value="${esc(s.value)}" placeholder="${s.sensitive ? (s.has_value ? '•••••••• (inchangé)' : '(non défini)') : ''}" autocomplete="off"></div></div>`).join('');
}
$('bkSettingsSave').onclick = async () => {
  const values = {};
  $('bkSettings').querySelectorAll('input[data-key]').forEach(i => values[i.dataset.key] = i.value);
  const d = await api('/api/backup/settings', { values });
  d.ok ? notify('Réglages enregistrés') : notify(d.error, 'ko');
  loadBackupSettings(); loadBackups();
};

// ================================================================================
// 🔑 CONFIG .ENV
// ================================================================================
function envInputs() { return [...document.querySelectorAll('#envGroups input[data-key]')]; }
function envDirtyInputs() { return envInputs().filter(i => i.value !== i.dataset.orig); }
function envDirtyCount() { return envDirtyInputs().length; }

function updateEnvDirty() {
  const n = envDirtyCount();
  $('envDirty').textContent = n ? `${n} modification${n > 1 ? 's' : ''} non enregistrée${n > 1 ? 's' : ''}` : 'Aucune modification';
}

async function loadEnv() {
  const d = await api('/api/env');
  if (!d.vars) return notify(d.error || 'Lecture du .env impossible', 'ko');

  const prefixCount = {};
  const prefix = k => k.includes('_') ? k.split('_')[0] : '';
  d.vars.forEach(v => { prefixCount[prefix(v.key)] = (prefixCount[prefix(v.key)] || 0) + 1; });
  const groups = {};
  d.vars.forEach(v => {
    const p = prefix(v.key);
    const g = p && prefixCount[p] > 1 ? p : 'AUTRES';
    (groups[g] ||= []).push(v);
  });

  $('envGroups').innerHTML = Object.entries(groups).map(([g, vars]) => `<div class="panel">
    <div class="panel-head"><div class="panel-title">${esc(g)}</div></div>
    ${vars.map(v => `<div class="row-set">
      <div><div class="name mono">${esc(v.key)}</div>${v.sensitive ? '<div class="desc">Masquée — laisser vide pour ne pas modifier</div>' : ''}</div>
      <div class="ctrl"><input class="field mono" data-key="${esc(v.key)}" data-orig="${esc(v.value)}" type="${v.sensitive ? 'password' : 'text'}"
        value="${esc(v.value)}" placeholder="${v.sensitive ? (v.has_value ? '•••••••• (inchangé)' : '(vide)') : '(vide)'}" autocomplete="off"></div>
    </div>`).join('')}</div>`).join('') || '<div class="note"><span>ℹ️</span><span class="note-body">Aucune variable dans le .env.</span></div>';
  updateEnvDirty();
}

$('envGroups').oninput = updateEnvDirty;
$('envReset').onclick = loadEnv;

async function saveEnv() {
  const dirty = envDirtyInputs();
  if (!dirty.length) { notify('Aucune modification', 'warn'); return false; }
  const values = {};
  dirty.forEach(i => values[i.dataset.key] = i.value);
  const d = await api('/api/env', { values });
  if (!d.ok) { notify(d.error, 'ko'); return false; }
  notify(`${d.changed} variable(s) enregistrée(s)`);
  await loadEnv();
  return true;
}
$('envSave').onclick = saveEnv;
$('envSaveRestart').onclick = async () => { if (await saveEnv()) restartBot(); };

// ================================================================================
// ⌨️ Raccourcis + INIT
// ================================================================================
document.addEventListener('keydown', e => {
  if (e.key !== 'Escape') return;
  closeEdit();
  $('confirmCancel').click();
});

loadBackups();
showTab(location.hash.slice(1) || 'db');
