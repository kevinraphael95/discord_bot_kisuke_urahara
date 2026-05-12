// ── auth.js — Supabase Auth + Leaderboard ────────────────────
const SUPA_URL = 'https://nzhinbrmaemkwprbxqbt.supabase.co';
const SUPA_KEY = 'sb_publishable_Jd5qpEcHJcx05etVqRphOg_DPUQZgNL';

const { createClient } = supabase;
const db = createClient(SUPA_URL, SUPA_KEY);

let currentUser = null;

// ── Cache leaderboard : évite un appel Supabase à chaque ouverture ─────────
const _lb = { data: null, ts: 0, err: false };
const LB_TTL = 60_000; // 60 secondes

// ── Init ──────────────────────────────────────────────────────
async function authInit() {
  const fullUrl = window.location.href;
  const hashIdx = fullUrl.indexOf('#');
  if (hashIdx !== -1) {
    const fragment = fullUrl.slice(hashIdx + 1).replace(/^#/, '');
    if (fragment.includes('access_token')) {
      window.history.replaceState(null, '', window.location.pathname + '#' + fragment);
    }
  }

  const { data: { session } } = await db.auth.getSession();
  if (session?.user) {
    currentUser = session.user;
    renderAuthBtn(session.user);
    window.history.replaceState(null, '', window.location.pathname);
    await loadDailyFromSupabase();
  } else {
    if (typeof onAuthReady === 'function') onAuthReady();
  }

  db.auth.onAuthStateChange(async (_event, session) => {
    currentUser = session?.user || null;
    renderAuthBtn(currentUser);
    if (currentUser) {
      await loadDailyFromSupabase();
    } else {
      if (typeof onAuthReady === 'function') onAuthReady();
    }
  });
}

// ── Charger progression daily depuis Supabase ─────────────────
async function loadDailyFromSupabase() {
  if (!currentUser) return;
  if (typeof mode !== 'undefined' && mode !== 'daily') return;

  const today = typeof todayKey === 'function' ? todayKey() : null;
  if (!today) return;

  try {
    const { data } = await db
      .from('scores')
      .select('guesses, found, attempts')
      .eq('user_id', currentUser.id)
      .eq('date', today)
      .eq('mode', 'daily')
      .single();

    if (data?.guesses?.length) {
      await new Promise(resolve => {
        function restore() {
          if (
            typeof CHARS === 'undefined' ||
            typeof cmp   === 'undefined' ||
            typeof tgt   === 'undefined' ||
            tgt === null
          ) { setTimeout(restore, 80); return; }

          // Remplir dG sans rien rendre — onAuthReady s'en charge
          dG = [];
          for (const name of data.guesses) {
            const m = typeof CHAR_MAP !== 'undefined'
              ? CHAR_MAP.get(name.toLowerCase())
              : CHARS.find(x => x.n === name);
            if (!m) continue;
            dG.push({ m, f: cmp(m, tgt) });
          }

          dOver = data.found || data.attempts >= MAX;

          try {
            localStorage.setItem('bleachg25v2', JSON.stringify({
              date:    today,
              guesses: data.guesses,
              over:    dOver,
              won:     data.found,
            }));
          } catch(e) {}

          resolve();
        }
        restore();
      });
    }

  } catch(e) {
    // Erreur réseau / pas de ligne : silencieux
  }

  // Délègue tout le rendu à onAuthReady
  if (typeof mode !== 'undefined' && mode === 'daily' && typeof onAuthReady === 'function') {
    onAuthReady();
  }
}

// ── Login ─────────────────────────────────────────────────────
async function loginWith(provider) {
  const redirect = window.location.origin + window.location.pathname;
  await db.auth.signInWithOAuth({ provider, options: { redirectTo: redirect } });
}

// ── Logout ────────────────────────────────────────────────────
async function logout() {
  await db.auth.signOut();
  currentUser = null;
  renderAuthBtn(null);
  closeUserMenu();

  if (typeof clr === 'function') clr();
  if (typeof updDots === 'function') { dG = []; dOver = false; updDots(); }

  const rb = document.getElementById('rb');
  if (rb) rb.classList.remove('on', 'win', 'lose');

  if (typeof loadDaily === 'function') loadDaily();
  if (typeof onAuthReady === 'function') onAuthReady();
}

// ── Bouton auth ───────────────────────────────────────────────
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

// ── Menu utilisateur ──────────────────────────────────────────
function toggleUserMenu() {
  if (!currentUser) { showAuthModal(); return; }
  const existing = document.getElementById('user-menu');
  if (existing) { closeUserMenu(); return; }

  const btn  = document.getElementById('auth-msw-btn');
  const name = currentUser.user_metadata?.full_name || currentUser.user_metadata?.name || currentUser.email?.split('@')[0] || '?';

  const menu = document.createElement('div');
  menu.id = 'user-menu'; menu.className = 'user-menu';
  menu.innerHTML = `
    <div class="um-name">${name}</div>
    <div class="um-email">${currentUser.email || ''}</div>
    <button class="um-logout" onclick="logout()">⏏ Se déconnecter</button>
  `;
  document.body.appendChild(menu);

  const rect = btn.getBoundingClientRect();
  menu.style.cssText = `position:fixed;top:${rect.bottom + 6}px;left:${rect.left}px;z-index:9999`;
  setTimeout(() => document.addEventListener('click', closeUserMenuOutside), 100);
}

function closeUserMenuOutside(e) {
  const menu = document.getElementById('user-menu');
  if (menu && !menu.contains(e.target) && e.target.id !== 'auth-msw-btn') closeUserMenu();
}
function closeUserMenu() {
  const menu = document.getElementById('user-menu');
  if (menu) menu.remove();
  document.removeEventListener('click', closeUserMenuOutside);
}

// ── Modal auth ────────────────────────────────────────────────
function showAuthModal() { const m = document.getElementById('auth-modal'); if (m) m.classList.add('on'); }
function hideAuthModal() { const m = document.getElementById('auth-modal'); if (m) m.classList.remove('on'); }
function skipAuth()      { hideAuthModal(); }

// ── Soumission du score ───────────────────────────────────────
async function submitScore({ date, found, attempts, mode, guesses }) {
  if (!currentUser) return;

  if (!date || date !== (typeof todayKey === 'function' ? todayKey() : '')) return;
  if (typeof found !== 'boolean' || typeof attempts !== 'number') return;
  if (attempts < 1 || attempts > MAX) return;
  if (!Array.isArray(guesses) || guesses.length !== attempts) return;
  if (typeof CHAR_MAP !== 'undefined') {
    if (!guesses.every(n => CHAR_MAP.has(n.toLowerCase()))) return;
  }

  const pseudo     = currentUser.user_metadata?.full_name || currentUser.user_metadata?.name || currentUser.email?.split('@')[0] || 'Anonyme';
  const avatar_url = currentUser.user_metadata?.avatar_url || null;

  try {
    const { error } = await db.from('scores').upsert(
      { user_id: currentUser.id, pseudo, avatar_url, date, found, attempts, mode, guesses },
      { onConflict: 'user_id,date,mode' }
    );
    if (error) console.warn('[submitScore]', error.message);
    else _lb.ts = 0;
  } catch(err) {
    console.warn('[submitScore] réseau:', err.message);
  }
}

// ── Leaderboard avec cache 60s ────────────────────────────────
async function _fetchLeaderboard() {
  const now   = new Date();
  const year  = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const from  = `${year}-${month}-01`;
  const to    = `${year}-${month}-31`;

  const { data, error } = await db
    .from('scores')
    .select('pseudo, avatar_url, found, attempts, date, mode')
    .gte('date', from).lte('date', to)
    .eq('found', true)
    .order('attempts', { ascending: true });

  if (error) throw new Error(error.message);
  if (!data) return [];

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

async function loadLeaderboard() {
  if (_lb.data && !_lb.err && (Date.now() - _lb.ts < LB_TTL)) return _lb.data;
  const rows = await _fetchLeaderboard();
  _lb.data = rows; _lb.ts = Date.now(); _lb.err = false;
  return rows;
}

async function showLeaderboard() {
  const modal = document.getElementById('lb-modal');
  if (!modal) return;
  modal.classList.add('on');

  const body = document.getElementById('lb-body');
  body.innerHTML = '<div class="lb-loading">Chargement…</div>';

  try {
    const rows = await loadLeaderboard();
    if (!rows.length) {
      body.innerHTML = '<div class="lb-empty">Aucun score ce mois-ci.</div>';
      return;
    }

    const monthLabel = new Date().toLocaleDateString('fr-FR', { month: 'long', year: 'numeric' });
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
  } catch(err) {
    _lb.err = true;
    body.innerHTML = '<div class="lb-empty">Erreur de connexion. Réessayez dans quelques instants.</div>';
    console.warn('[leaderboard]', err.message);
  }
}

function hideLeaderboard() {
  const modal = document.getElementById('lb-modal');
  if (modal) modal.classList.remove('on');
}

// ── Lancer l'init ─────────────────────────────────────────────
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', authInit);
} else {
  authInit();
}
