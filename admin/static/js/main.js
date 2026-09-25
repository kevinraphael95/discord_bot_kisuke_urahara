// ================================================================================
// 📌 main.js — Script principal du panel admin Kisuke
// Objectif : Logique front (onglets, thème, base de données, SQL, logs, actions)
// Catégorie : Admin
// Accès : Admin uniquement (chargé par templates/main.html)
// ================================================================================

// ================================================================================
// 🛠️ UTILS
// ================================================================================

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

// ================================================================================
// 🌗 THÈME CLAIR / SOMBRE
// ================================================================================
function initTheme() {
  const saved = localStorage.getItem('kisuke-theme') || 'dark';
  document.documentElement.setAttribute('data-theme', saved);
  updateThemeIcon(saved);
}

function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme') || 'dark';
  const next = current === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  localStorage.setItem('kisuke-theme', next);
  updateThemeIcon(next);
}

function updateThemeIcon(theme) {
  const btn = document.getElementById('themeToggle');
  if (btn) btn.textContent = theme === 'dark' ? '☀' : '☾';
}

initTheme();

// ================================================================================
// 📱 SIDEBAR MOBILE
// ================================================================================
function toggleSidebar() {
  document.getElementById('sidebar').classList.toggle('open');
  document.getElementById('sidebarOverlay').classList.toggle('open');
}

function closeSidebarIfMobile() {
  if (window.innerWidth <= 900) {
    document.getElementById('sidebar').classList.remove('open');
    document.getElementById('sidebarOverlay').classList.remove('open');
  }
}

// ================================================================================
// 📂 TABS
// ================================================================================
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
  closeSidebarIfMobile();
}

// ================================================================================
// 🗄️ DATABASE
// ================================================================================
let currentData = [], currentCols = [], currentTableName = '', currentPk = '';
let sortCol = null, sortDir = 1;
let rawLogs = [];

async function loadTableList() {
  const res = await fetch('/api/tables');
  const data = await res.json();
  const sel = document.getElementById('tableSelect');
  const previous = sel.value;
  sel.innerHTML = data.tables.map(t => `<option value="${t}">${t}</option>`).join('');
  document.getElementById('sb-table-count').textContent = data.tables.length;
  // Reste sur la table précédente si elle existe encore, sinon prend la première
  if (data.tables.includes(previous)) sel.value = previous;
  loadTable();
}

async function loadTable() {
  const table = document.getElementById('tableSelect').value;
  if (!table) {
    // Plus aucune table (ex: dernière supprimée) → on vide l'affichage
    currentData = []; currentCols = []; currentTableName = ''; currentPk = '';
    document.getElementById('tableHead').innerHTML = '';
    document.getElementById('tableBody').innerHTML = '';
    document.getElementById('ti-table').textContent = '—';
    document.getElementById('bc-table').textContent = 'Base de données';
    document.getElementById('ti-pk').textContent = '';
    document.getElementById('ti-count').textContent = '0 entrée';
    document.getElementById('db-stats-grid').innerHTML = '';
    return;
  }
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

// ================================================================================
// 🗑️ SUPPRESSION DE TABLE
// ================================================================================
function confirmDeleteTable() {
  const table = document.getElementById('tableSelect').value;
  if (!table) { toast('Aucune table sélectionnée', 'err'); return; }

  document.getElementById('modal-confirm-text').textContent =
    `Supprimer définitivement la table "${table}" et toutes ses données ? Cette action est irréversible.`;

  const btn = document.getElementById('modal-confirm-btn');
  btn.textContent = 'Supprimer';
  btn.onclick = () => {
    deleteTable(table);
    document.getElementById('modal-confirm').style.display = 'none';
  };

  document.getElementById('modal-confirm').style.display = 'flex';
}

async function deleteTable(table) {
  try {
    const res = await fetch('/api/table/' + table + '/delete', {method:'POST'});
    const data = await res.json();
    if (data.ok) {
      toast('✓ Table "' + table + '" supprimée', 'ok');
      loadTableList();
    } else {
      toast('✕ ' + data.error, 'err');
    }
  } catch (e) {
    toast('✕ Erreur réseau', 'err');
  }
}

// ================================================================================
// ✏️ MODAL EDIT
// ================================================================================
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

// ================================================================================
// ◈ SQL
// ================================================================================
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
    // Si la requête SQL touchait une table qui vient d'être DROP/CREATE, on resynchronise la liste
    if (/drop\s+table|create\s+table/i.test(q)) loadTableList();
  } else {
    el.innerHTML = `<div style="background:var(--void);border:1px solid var(--green);border-left:3px solid var(--green);padding:12px 16px;color:var(--green);font-size:11px;margin-top:4px">✓ ${esc(data.message)}</div>`;
    if (/drop\s+table|create\s+table/i.test(q)) loadTableList();
  }
}

// ================================================================================
// ▤ LOGS
// ================================================================================
const LOG_REFRESH_INTERVAL_MS = 6000; // 6s : compromis entre réactivité et charge/bruit
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
  if (on) autoRefreshTimer = setInterval(loadLogs, LOG_REFRESH_INTERVAL_MS);
}

// ══════════════════════════════════════════════════════════════════════════════
// ACTIONS
// ══════════════════════════════════════════════════════════════════════════════
function confirmRestart() {
  document.getElementById('modal-confirm-text').textContent =
    'Cette action va redémarrer le process du bot. Continuer ?';
  const btn = document.getElementById('modal-confirm-btn');
  btn.textContent = 'Redémarrer';
  btn.onclick = () => {
    doAction('restart_bot', btn);
    document.getElementById('modal-confirm').style.display = 'none';
  };
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

// ================================================================================
// INIT
// ================================================================================
loadTableList();
autoRefreshTimer = setInterval(loadLogs, LOG_REFRESH_INTERVAL_MS);
