// ── auth.js — Supabase Auth + Leaderboard ────────────────────
const SUPA_URL = 'https://nzhinbrmaemkwprbxqbt.supabase.co';
const SUPA_KEY = 'sb_publishable_Jd5qpEcHJcx05etVqRphOg_DPUQZgNL';

const { createClient } = supabase;
const db = createClient(SUPA_URL, SUPA_KEY);

let currentUser = null;

// ── Init : vérif session au chargement ───────────────────────
async function authInit() {
  const { data: { session } } = await db.auth.getSession();
  if (session?.user) {
    currentUser = session.user;
    renderAuthBtn(session.user);
  }

  db.auth.onAuthStateChange((_event, session) => {
    currentUser = session?.user || null;
    renderAuthBtn(currentUser);
  });

  // Redirect OAuth : fermer le modal si on revient après login
  const hash = window.location.hash;
  if (hash && hash.includes('access_token')) {
    const { data: { session: s } } = await db.auth.getSession();
    if (s?.user) {
      currentUser = s.user;
      renderAuthBtn(s.user);
      hideAuthModal();
      window.history.replaceState(null, '', window.location.pathname);
    }
  }
}

// ── Login ────────────────────────────────────────────────────
async function loginWith(provider) {
  await db.auth.signInWithOAuth({
    provider,
    options: { redirectTo: window.location.href }
  });
}

// ── Logout ───────────────────────────────────────────────────
async function logout() {
  await db.auth.signOut();
  currentUser = null;
  renderAuthBtn(null);
  closeUserMenu();
}

// ── Bouton auth dans .msw ─────────────────────────────────────
function renderAuthBtn(user) {
  const btn = document.getElementById('auth-msw-btn');
  if (!btn) return;
  if (user) {
    const avatar = user.user_metadata?.avatar_url;
    const name   = user.user_metadata?.full_name || user.user_metadata?.name || user.email?.split('@')[0] || '?';
    btn.innerHTML = avatar
      ? `<img src="${avatar}" class="auth-avatar" alt="${name}" title="${name}">`
      : `<span class="auth-initials">${name[0].toUpperCase()}</span>`;
    btn.classList.add('connected');
    btn.title = name;
  } else {
    btn.innerHTML = '👤';
    btn.classList.remove('connected');
    btn.title = 'Se connecter';
  }
}

// ── Menu utilisateur (déco) ───────────────────────────────────
function toggleUserMenu() {
  if (!currentUser) { showAuthModal(); return; }
  
  let menu = document.getElementById('user-menu');
  if (menu) { closeUserMenu(); return; }

  const btn = document.getElementById('auth-msw-btn');
  const name = currentUser.user_metadata?.full_name || currentUser.user_metadata?.name || currentUser.email?.split('@')[0] || '?';

  menu = document.createElement('div');
  menu.id = 'user-menu';
  menu.className = 'user-menu';
  menu.innerHTML = `
    <div class="um-name">${name}</div>
    <div class="um-email">${currentUser.email || ''}</div>
    <button class="um-logout" onclick="logout()">⏏ Se déconnecter</button>
  `;

  document.body.appendChild(menu);
  
  const rect = btn.getBoundingClientRect();
  menu.style.position = 'fixed';
  menu.style.top = (rect.bottom + 6) + 'px';
  menu.style.left = rect.left + 'px';
  menu.style.zIndex = '9999';

  setTimeout(() => document.addEventListener('click', closeUserMenuOutside), 100);
}

function closeUserMenuOutside(e) {
  const menu = document.getElementById('user-menu');
  if (menu && !menu.contains(e.target) && e.target.id !== 'auth-msw-btn') {
    closeUserMenu();
  }
}

function closeUserMenu() {
  const menu = document.getElementById('user-menu');
  if (menu) menu.remove();
  document.removeEventListener('click', closeUserMenuOutside);
}

// ── Modal auth ────────────────────────────────────────────────
function showAuthModal() {
  const m = document.getElementById('auth-modal');
  if (m) m.classList.add('on');
}

function hideAuthModal() {
  const m = document.getElementById('auth-modal');
  if (m) m.classList.remove('on');
}

function skipAuth() {
  hideAuthModal();
}

// ── Soumission du score ───────────────────────────────────────
async function submitScore({ date, found, attempts, mode }) {
  if (!currentUser) return;

  const pseudo     = currentUser.user_metadata?.full_name
                  || currentUser.user_metadata?.name
                  || currentUser.email?.split('@')[0]
                  || 'Anonyme';
  const avatar_url = currentUser.user_metadata?.avatar_url || null;

  await db.from('scores').upsert({
    user_id: currentUser.id,
    pseudo,
    avatar_url,
    date,
    found,
    attempts,
    mode,
  }, { onConflict: 'user_id,date,mode' });
}

// ── Chargement leaderboard mensuel ───────────────────────────
async function loadLeaderboard() {
  const now   = new Date();
  const year  = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const from  = `${year}-${month}-01`;
  const to    = `${year}-${month}-31`;

  const { data, error } = await db
    .from('scores')
    .select('pseudo, avatar_url, found, attempts, date, mode')
    .gte('date', from)
    .lte('date', to)
    .eq('found', true)
    .order('attempts', { ascending: true });

  if (error || !data) return [];

  // Agrégation : par pseudo, compter trouvés et total tentatives
  const map = {};
  for (const row of data) {
    if (!map[row.pseudo]) map[row.pseudo] = { pseudo: row.pseudo, avatar_url: row.avatar_url, found: 0, attempts: 0 };
    map[row.pseudo].found++;
    map[row.pseudo].attempts += row.attempts;
  }

  return Object.values(map)
    .sort((a, b) => b.found - a.found || a.attempts - b.attempts)
    .slice(0, 20);
}

// ── Modal leaderboard ─────────────────────────────────────────
async function showLeaderboard() {
  let modal = document.getElementById('lb-modal');
  if (!modal) return;
  modal.classList.add('on');

  const body = document.getElementById('lb-body');
  body.innerHTML = '<div class="lb-loading">Chargement…</div>';

  const rows = await loadLeaderboard();

  if (!rows.length) {
    body.innerHTML = '<div class="lb-empty">Aucun score ce mois-ci.</div>';
    return;
  }

  const now = new Date();
  const monthLabel = now.toLocaleDateString('fr-FR', { month: 'long', year: 'numeric' });
  document.getElementById('lb-month').textContent = monthLabel.charAt(0).toUpperCase() + monthLabel.slice(1);

  body.innerHTML = rows.map((r, i) => {
    const medal = i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : `<span class="lb-rank">${i + 1}</span>`;
    const avg   = r.found > 0 ? (r.attempts / r.found).toFixed(1) : '—';
    const av    = r.avatar_url
      ? `<img src="${r.avatar_url}" class="lb-av" alt="${r.pseudo}">`
      : `<span class="lb-av lb-av-init">${r.pseudo[0].toUpperCase()}</span>`;
    return `
      <div class="lb-row ${i < 3 ? 'lb-top' : ''}">
        <div class="lb-pos">${medal}</div>
        ${av}
        <div class="lb-info">
          <div class="lb-name">${r.pseudo}</div>
          <div class="lb-sub">${r.found} trouvé${r.found > 1 ? 's' : ''} · moy. ${avg} essai${avg !== '1.0' ? 's' : ''}</div>
        </div>
        <div class="lb-score">${r.found}</div>
      </div>`;
  }).join('');
}

function hideLeaderboard() {
  const modal = document.getElementById('lb-modal');
  if (modal) modal.classList.remove('on');
}

// ── Lancer l'init dès que possible ───────────────────────────
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', authInit);
} else {
  authInit();
}
