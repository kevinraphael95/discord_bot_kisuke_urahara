// ── auth.js — Supabase Auth + Leaderboard ────────────────────
const SUPA_URL = 'https://nzhinbrmaemkwprbxqbt.supabase.co';
const SUPA_KEY = 'sb_publishable_Jd5qpEcHJcx05etVqRphOg_DPUQZgNL';

const { createClient } = supabase;
const db = createClient(SUPA_URL, SUPA_KEY);

let currentUser = null;

// ── Cache leaderboard (évite un appel Supabase à chaque ouverture) ──────
const _lb = { data: null, ts: 0 };
const LB_TTL = 60_000; // 60 secondes

// ── Init ──────────────────────────────────────────────────────
async function authInit() {
  const fullUrl = window.location.href;
  const hashIdx = fullUrl.indexOf('#');
  if (hashIdx !== -1) {
    const fragment = fullUrl.slice(hashIdx+1).replace(/^#/,'');
    if (fragment.includes('access_token')) {
      window.history.replaceState(null,'', window.location.pathname+'#'+fragment);
    }
  }

  const { data: { session } } = await db.auth.getSession();
  if (session?.user) {
    currentUser = session.user;
    renderAuthBtn(session.user);
    window.history.replaceState(null,'', window.location.pathname);
    await loadDailyFromSupabase();
  }

  if (typeof onAuthReady === 'function') onAuthReady();

  db.auth.onAuthStateChange(async (_event, session) => {
    currentUser = session?.user || null;
    renderAuthBtn(currentUser);
    if (typeof onAuthReady === 'function') onAuthReady();
    if (currentUser) await loadDailyFromSupabase();
  });
}

// ── Charger progression daily depuis Supabase ─────────────────
async function loadDailyFromSupabase() {
  if (!currentUser) return;
  if (typeof mode !== 'undefined' && mode !== 'daily') return;
  const today = typeof todayKey === 'function' ? todayKey() : null;
  if (!today) return;

  try {
    // Nouvelle structure : on lit dans monthly_scores la colonne days (JSONB)
    // days = { "2025-6-1": { found: true, attempts: 3, guesses: [...] }, ... }
    const year  = new Date().getFullYear();
    const month = new Date().getMonth() + 1;
    const monthKey = `${year}-${month}`;

    const { data } = await db
      .from('monthly_scores')
      .select('days')
      .eq('user_id', currentUser.id)
      .eq('month', monthKey)
      .single();

    const dayData = data?.days?.[today];
    if (!dayData?.guesses?.length) return;

    await new Promise(resolve => {
      function restore() {
        if (typeof CHARS==='undefined'||typeof cmp==='undefined'||typeof todayChar==='undefined') {
          setTimeout(restore, 80); return;
        }
        // Utilise l'objet daily centralisé de guesser.js
        daily.guesses = []; daily.over = false; clr();
        for (const name of dayData.guesses) {
          const m = CHAR_MAP.get(name.toLowerCase());
          if (!m) continue;
          const f = cmp(m, daily.tgt);
          daily.guesses.push({m,f});
          if (mode==='daily') { mkRow(m,f,daily.tgt); mkCard(m,f,daily.tgt); }
        }
        if (mode==='daily') updDots();
        try {
          localStorage.setItem('bleachg25v2', JSON.stringify({
            date: today, guesses: dayData.guesses,
            over: dayData.found || dayData.attempts >= MAX, won: dayData.found,
          }));
        } catch(e) {}
        const over = dayData.found || dayData.attempts >= MAX;
        if (over) { daily.over=true; if(mode==='daily'){hideGameUI();showDRes(dayData.found);} }
        resolve();
      }
      restore();
    });
  } catch(e) {
    // Pas de données pour ce mois : normal, on ne fait rien
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

  if (typeof clr==='function') clr();
  if (typeof updDots==='function') { daily.guesses=[]; daily.over=false; updDots(); }

  const rb = document.getElementById('rb');
  if (rb) rb.classList.remove('on','win','lose');

  if (typeof loadDaily==='function') loadDaily();
  if (typeof onAuthReady==='function') onAuthReady();
}

// ── Bouton auth ───────────────────────────────────────────────
function renderAuthBtn(user) {
  const btn = document.getElementById('auth-msw-btn');
  if (!btn) return;
  if (user) {
    const avatar = user.user_metadata?.avatar_url;
    const name   = user.user_metadata?.full_name||user.user_metadata?.name||user.email?.split('@')[0]||'?';
    btn.innerHTML = avatar
      ? `<img src="${avatar}" class="auth-avatar" alt="${name}" title="${name}">`
      : `<span class="auth-initials">${name[0].toUpperCase()}</span>`;
    btn.classList.add('connected');
    btn.title = name;
  } else {
    btn.innerHTML='👤'; btn.classList.remove('connected'); btn.title='Se connecter';
  }
}

// ── Menu utilisateur ──────────────────────────────────────────
function toggleUserMenu() {
  if (!currentUser) { showAuthModal(); return; }
  const existing = document.getElementById('user-menu');
  if (existing) { closeUserMenu(); return; }
  const btn  = document.getElementById('auth-msw-btn');
  const name = currentUser.user_metadata?.full_name||currentUser.user_metadata?.name||currentUser.email?.split('@')[0]||'?';
  const menu = document.createElement('div');
  menu.id='user-menu'; menu.className='user-menu';
  menu.innerHTML=`<div class="um-name">${name}</div><div class="um-email">${currentUser.email||''}</div><button class="um-logout" onclick="logout()">⏏ Se déconnecter</button>`;
  document.body.appendChild(menu);
  const rect = btn.getBoundingClientRect();
  menu.style.cssText=`position:fixed;top:${rect.bottom+6}px;left:${rect.left}px;z-index:9999`;
  setTimeout(()=>document.addEventListener('click',closeUserMenuOutside), 100);
}

function closeUserMenuOutside(e) {
  const menu=document.getElementById('user-menu');
  if (menu&&!menu.contains(e.target)&&e.target.id!=='auth-msw-btn') closeUserMenu();
}
function closeUserMenu() {
  const menu=document.getElementById('user-menu');
  if(menu)menu.remove();
  document.removeEventListener('click',closeUserMenuOutside);
}

// ── Modal auth ────────────────────────────────────────────────
function showAuthModal() { const m=document.getElementById('auth-modal'); if(m)m.classList.add('on'); }
function hideAuthModal() { const m=document.getElementById('auth-modal'); if(m)m.classList.remove('on'); }
function skipAuth()      { hideAuthModal(); }

// ── Soumission du score ───────────────────────────────────────
// Nouvelle structure : une seule ligne par (user_id, month)
// La colonne `days` (JSONB) stocke chaque jour du mois :
//   { "2025-6-1": { found, attempts, guesses }, "2025-6-2": { ... }, ... }
//
// SQL à exécuter dans Supabase pour créer la table :
// ---------------------------------------------------
// create table monthly_scores (
//   id          uuid primary key default gen_random_uuid(),
//   user_id     uuid not null references auth.users(id),
//   pseudo      text,
//   avatar_url  text,
//   month       text not null,          -- ex: "2025-6"
//   days        jsonb not null default '{}',
//   found_count int  not null default 0, -- nb de jours réussis ce mois
//   total_attempts int not null default 0,
//   updated_at  timestamptz default now(),
//   unique(user_id, month)
// );
// alter table monthly_scores enable row level security;
// create policy "Users manage own scores"
//   on monthly_scores for all using (auth.uid() = user_id);
// ---------------------------------------------------

async function submitScore({ date, found, attempts, mode, guesses }) {
  if (!currentUser) return;

  // Validation minimale côté client
  if (!date || typeof found !== 'boolean' || typeof attempts !== 'number') return;
  if (attempts < 1 || attempts > MAX) return;
  if (!Array.isArray(guesses) || guesses.length !== attempts) return;
  if (date !== todayKey()) return; // bloque les dates bidons
  // Vérifie que chaque guess est un vrai perso
  if (!guesses.every(n => CHAR_MAP.has(n.toLowerCase()))) return;

  const pseudo     = currentUser.user_metadata?.full_name||currentUser.user_metadata?.name||currentUser.email?.split('@')[0]||'Anonyme';
  const avatar_url = currentUser.user_metadata?.avatar_url||null;
  const now        = new Date();
  const monthKey   = `${now.getFullYear()}-${now.getMonth()+1}`;

  try {
    // Récupère la ligne existante pour ce mois
    const { data: existing } = await db
      .from('monthly_scores')
      .select('id, days, found_count, total_attempts')
      .eq('user_id', currentUser.id)
      .eq('month', monthKey)
      .single();

    const dayEntry = { found, attempts, guesses };

    if (existing) {
      // Si ce jour a déjà été soumis, ne pas ré-écraser
      if (existing.days?.[date]) return;

      const newDays     = { ...existing.days, [date]: dayEntry };
      const newFound    = existing.found_count + (found ? 1 : 0);
      const newAttempts = existing.total_attempts + attempts;

      const { error } = await db
        .from('monthly_scores')
        .update({ days: newDays, found_count: newFound, total_attempts: newAttempts, pseudo, avatar_url, updated_at: new Date().toISOString() })
        .eq('id', existing.id);

      if (error) console.warn('[submitScore] update error:', error.message);
    } else {
      // Première soumission du mois
      const { error } = await db
        .from('monthly_scores')
        .insert({
          user_id: currentUser.id, pseudo, avatar_url, month: monthKey,
          days: { [date]: dayEntry },
          found_count: found ? 1 : 0,
          total_attempts: attempts,
        });

      if (error) console.warn('[submitScore] insert error:', error.message);
    }

    // Invalide le cache leaderboard
    _lb.ts = 0;
  } catch(err) {
    console.warn('[submitScore] réseau:', err.message);
  }
}

// ── Leaderboard ───────────────────────────────────────────────
async function _fetchLeaderboard() {
  const now      = new Date();
  const monthKey = `${now.getFullYear()}-${now.getMonth()+1}`;

  const { data, error } = await db
    .from('monthly_scores')
    .select('pseudo, avatar_url, found_count, total_attempts')
    .eq('month', monthKey)
    .gt('found_count', 0)
    .order('found_count', { ascending: false })
    .order('total_attempts', { ascending: true })
    .limit(20);

  if (error || !data) return [];
  return data.map(r => ({
    pseudo:    r.pseudo,
    avatar_url:r.avatar_url,
    found:     r.found_count,
    attempts:  r.total_attempts,
  }));
}

async function loadLeaderboard() {
  if (_lb.data && Date.now() - _lb.ts < LB_TTL) return _lb.data;
  const rows = await _fetchLeaderboard();
  _lb.data = rows; _lb.ts = Date.now();
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
    if (!rows.length) { body.innerHTML='<div class="lb-empty">Aucun score ce mois-ci.</div>'; return; }

    const monthLabel = new Date().toLocaleDateString('fr-FR',{month:'long',year:'numeric'});
    document.getElementById('lb-month').textContent = monthLabel.charAt(0).toUpperCase()+monthLabel.slice(1);

    body.innerHTML = rows.map((r,i) => {
      const medal = i===0?'🥇':i===1?'🥈':i===2?'🥉':`<span class="lb-rank">${i+1}</span>`;
      const avg   = r.found>0 ? (r.attempts/r.found).toFixed(1) : '—';
      const av    = r.avatar_url
        ? `<img src="${r.avatar_url}" class="lb-av" alt="${r.pseudo}">`
        : `<span class="lb-av lb-av-init">${r.pseudo[0].toUpperCase()}</span>`;
      return `
        <div class="lb-row ${i<3?'lb-top':''}">
          <div class="lb-pos">${medal}</div>
          ${av}
          <div class="lb-info">
            <div class="lb-name">${r.pseudo}</div>
            <div class="lb-sub">${r.found} trouvé${r.found>1?'s':''} · moy. ${avg} essai${avg!=='1.0'?'s':''}</div>
          </div>
          <div class="lb-score">${r.found}</div>
        </div>`;
    }).join('');
  } catch(err) {
    body.innerHTML='<div class="lb-empty">Erreur de chargement. Réessayez.</div>';
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
