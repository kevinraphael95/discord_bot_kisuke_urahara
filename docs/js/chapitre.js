/* ══════════════════════════════════════════
   BLEACH — Quel Chapitre ? · chapitre.js
   Fix CORS : utilise cors-anywhere + fallbacks fiables
   ══════════════════════════════════════════ */

const BLEACH_ID    = 'be5f4e76-b030-4b96-834c-a4a17792da4e';
const API_BASE     = 'https://api.mangadex.org';
const MAX_TRIES    = 5;
const CLOSE_MARGIN = 15;

/*
 * PROXIES CORS — ordonnés du plus fiable au moins fiable.
 *
 * 1. corsproxy.io    → proxy public moderne, fonctionne bien sur GitHub Pages
 * 2. allorigins      → fiable mais parfois lent
 * 3. api.codetabs    → bon fallback
 *
 * MangaDex bloque les requêtes cross-origin depuis les navigateurs,
 * donc on passe TOUJOURS par un proxy (pas de tentative directe).
 */
const PROXIES = [
  url => `https://corsproxy.io/?url=${encodeURIComponent(url)}`,
  url => `https://api.allorigins.win/raw?url=${encodeURIComponent(url)}`,
  url => `https://api.codetabs.com/v1/proxy?quest=${encodeURIComponent(url)}`,
];

const ARCS = [
  [1,   'Agent de la Shinigami'],
  [70,  'Soul Society — Perturbation'],
  [118, 'Soul Society — Sauvetage'],
  [182, 'Arrancar'],
  [240, 'Hueco Mundo'],
  [295, 'Fake Karakura Town'],
  [343, 'Fullbring'],
  [424, 'La Guerre des Mille Ans'],
  [480, 'La Guerre des Mille Ans — La Fumée'],
  [541, 'Sang pour Sang'],
  [612, 'La Moisson'],
  [665, 'Épilogue'],
];

let target = null, tries = [], over = false, hints = new Set(), chapCache = null;
let score = 0, streak = 0, best = 0, round = 0;

const $ = id => document.getElementById(id);

window.addEventListener('load', () => {
  loadRec();
  newRound();
});

/* ── PERSISTANCE ── */
function loadRec() {
  try {
    const s = JSON.parse(localStorage.getItem('bqc_v1'));
    if (s) { score = s.score || 0; best = s.best || 0; }
  } catch(e) {}
}
function saveRec() {
  try { localStorage.setItem('bqc_v1', JSON.stringify({ score, best })); } catch(e) {}
}

/* ── NOUVELLE MANCHE ── */
async function newRound() {
  tries = []; over = false; hints = new Set(); target = null;
  ['imgBox','inputBox','feedback','result','errorBox'].forEach(id => $(id).style.display = 'none');
  $('loadBox').style.display = 'flex';
  ['histBox','hintTags'].forEach(id => $(id).innerHTML = '');
  $('chapInput').value = '';
  $('chapInput').disabled = false;
  $('subBtn').disabled = false;
  $('mangaImg').className = 'blurred';
  ['hintArc','hintRange','hintUnblur'].forEach(id => $(id).disabled = false);
  updTries();
  updStats();
  try {
    await loadPage();
  } catch(e) {
    console.error(e);
    $('loadBox').style.display = 'none';
    $('errMsg').textContent = 'Erreur : ' + e.message;
    $('errorBox').style.display = 'flex';
  }
}

/* ── FETCH AVEC PROXIES ── */
async function apiGet(path) {
  const fullUrl = API_BASE + path;

  // On essaie chaque proxy dans l'ordre, sans tentative directe
  // (MangaDex bloque systématiquement les appels directs depuis les navigateurs)
  for (const makeProxy of PROXIES) {
    try {
      const proxyUrl = makeProxy(fullUrl);
      const r = await fetch(proxyUrl, { signal: AbortSignal.timeout(10000) });
      if (r.ok) {
        const text = await r.text();
        // allorigins encapsule parfois dans { contents: "..." }
        try {
          const json = JSON.parse(text);
          if (json.contents) return JSON.parse(json.contents);
          return json;
        } catch {
          throw new Error('Réponse non-JSON');
        }
      }
    } catch(e) {
      console.warn('Proxy échoué, essai suivant…', e.message);
    }
  }
  throw new Error('Tous les proxies CORS ont échoué. Réessaie dans quelques secondes.');
}

/* ── CHARGER UNE PAGE ── */
async function loadPage() {
  setLoad('📚 Récupération des chapitres…', 15);

  if (!chapCache) chapCache = await fetchChapters();

  setLoad('🎲 Sélection aléatoire…', 65);
  const chap = chapCache[Math.floor(Math.random() * chapCache.length)];

  setLoad('🖼 Chargement de la page…', 80);

  // Serveur de pages MangaDex — même problème CORS, on passe par proxy
  const serverPath = `/at-home/server/${chap.id}`;
  const pData = await apiGet(serverPath);

  const hash  = pData.chapter.hash;
  const pages = pData.chapter.dataSaver;
  if (!pages?.length) throw new Error('Chapitre sans pages disponibles');

  // On évite la page 0 (souvent une couverture ou page de titre)
  const idx     = 1 + Math.floor(Math.random() * (pages.length - 1));
  const pageUrl = `${pData.baseUrl}/data-saver/${hash}/${pages[idx]}`;

  target = {
    num:     parseFloat(chap.attrs.chapter),
    id:      chap.id,
    title:   chap.attrs.title || '',
    pageUrl
  };

  setLoad('✅ Prêt !', 100);
  await loadImg(pageUrl);

  round++;
  $('loadBox').style.display  = 'none';
  $('imgBox').style.display   = 'block';
  $('inputBox').style.display = 'flex';
  $('chapInput').focus();
  updStats();
}

/* ── RÉCUPÉRER TOUS LES CHAPITRES ── */
async function fetchChapters() {
  let all = [], offset = 0, total = Infinity;

  while (offset < total && all.length < 900) {
    const path = `/manga/${BLEACH_ID}/feed`
      + `?translatedLanguage[]=fr&translatedLanguage[]=en`
      + `&limit=100&offset=${offset}`
      + `&order[chapter]=asc`
      + `&includeEmptyPages=0`
      + `&contentRating[]=safe`;

    const d = await apiGet(path);
    total = d.total;

    const valid = (d.data || []).filter(c => {
      const n = parseFloat(c.attributes.chapter);
      return !isNaN(n) && n >= 1 && n <= 686;
    });

    all = all.concat(valid.map(c => ({ id: c.id, attrs: c.attributes })));
    offset += 100;

    if (offset < total) {
      setLoad(`📚 ${all.length} chapitres chargés…`, Math.round(15 + 50 * (offset / Math.min(total, 700))));
    }
  }

  if (!all.length) throw new Error('Aucun chapitre trouvé — le proxy a peut-être retourné une réponse vide.');

  // Dédoublonnage par numéro de chapitre
  const seen = new Set();
  return all.filter(c => {
    const n = parseFloat(c.attrs.chapter);
    if (seen.has(n)) return false;
    seen.add(n);
    return true;
  });
}

/* ── CHARGER L'IMAGE ── */
function loadImg(url) {
  return new Promise((res, rej) => {
    const img = $('mangaImg');
    img.onload  = res;
    img.onerror = () => rej(new Error('Image non chargeable (serveur MangaDex)'));
    img.src = url;
  });
}

function setLoad(msg, pct) {
  $('loadMsg').textContent  = msg;
  $('progFill').style.width = pct + '%';
}

/* ── SOUMETTRE UNE RÉPONSE ── */
function submit() {
  if (over || !target) return;
  const raw  = parseInt($('chapInput').value);
  if (isNaN(raw) || raw < 1 || raw > 686) { shake($('chapInput')); return; }

  const diff = Math.abs(raw - target.num);
  const res  = diff === 0 ? 'correct' : diff <= CLOSE_MARGIN ? 'close' : 'wrong';
  const arr  = raw < target.num ? "▲ c'est plus tard" : raw > target.num ? "▼ c'est plus tôt" : '';

  tries.push({ guess: raw, result: res, diff, arr });
  addHist(raw, res, diff, arr);
  updTries();
  $('chapInput').value = '';

  if (res === 'correct' || tries.length >= MAX_TRIES) {
    endRound(res === 'correct');
  } else {
    showFeedback(res, diff, arr);
    $('chapInput').focus();
  }
}

/* ── FEEDBACK INTERMÉDIAIRE ── */
function showFeedback(res, diff, arr) {
  const fb = $('feedback');
  fb.style.display = 'flex';
  fb.className = res;
  $('fbTitle').textContent  = res === 'close' ? '🟡 Presque — tu chauffes !' : '❌ Raté';
  $('fbDetail').textContent = `Écart de ${diff} chapitre${diff > 1 ? 's' : ''}. ${arr} — ${MAX_TRIES - tries.length} essai${MAX_TRIES - tries.length > 1 ? 's' : ''} restant${MAX_TRIES - tries.length > 1 ? 's' : ''}.`;
}

/* ── FIN DE MANCHE ── */
function endRound(won) {
  over = true;
  $('chapInput').disabled = true;
  $('subBtn').disabled    = true;
  $('feedback').style.display  = 'none';
  $('inputBox').style.display  = 'none';
  $('mangaImg').classList.remove('blurred');

  if (won) {
    score += Math.max(10, 100 - (tries.length - 1) * 15 - hints.size * 10);
    streak++;
    if (streak > best) best = streak;
  } else {
    streak = 0;
  }
  saveRec();
  updStats();

  const r = $('result');
  r.style.display = 'flex';
  r.className = won ? 'win' : 'lose';
  $('resTtl').textContent  = won ? '🎉 Bien vu !' : '💀 Raté !';
  $('resImg').src          = target.pageUrl;
  $('resChap').textContent = 'Chapitre ' + target.num;
  $('resArc').textContent  = (target.title ? '"' + target.title + '" — ' : '') + getArc(target.num);
}

/* ── HISTORIQUE ── */
function addHist(guess, res, diff, arr) {
  const d = document.createElement('div');
  d.className = 'hist-item ' + res;
  const badge = res === 'correct' ? '✅ Exact' : res === 'close' ? '🟡 Proche' : '❌ Raté';
  d.innerHTML = `
    <span class="hist-guess">Chapitre ${guess}</span>
    <span class="hist-info">
      ${res !== 'correct' ? `<span class="hist-arrow">${arr} · écart ${diff}</span>` : ''}
      <span class="hist-badge ${res}">${badge}</span>
    </span>`;
  $('histBox').appendChild(d);
}

/* ── UI ── */
function updTries() {
  const row = $('triesRow');
  row.innerHTML = '';
  for (let i = 0; i < MAX_TRIES; i++) {
    const d = document.createElement('div');
    d.className = 'try-dot' + (i < tries.length ? ' ' + tries[i].result : '');
    row.appendChild(d);
  }
}
function updStats() {
  $('sScore').textContent  = score;
  $('sStreak').textContent = streak;
  $('sBest').textContent   = best;
  $('sRound').textContent  = round;
}

/* ── INDICES ── */
function giveHint(type) {
  if (hints.has(type) || !target) return;
  hints.add(type);

  if (type === 'unblur') {
    $('mangaImg').classList.remove('blurred');
    $('hintUnblur').disabled = true;
    return;
  }

  let text = '';
  if (type === 'arc') {
    text = '🗡 Arc : ' + getArc(target.num);
    $('hintArc').disabled = true;
  } else if (type === 'range') {
    const lo = Math.max(1, target.num - 50);
    const hi = Math.min(686, target.num + 50);
    text = `📐 Entre le chapitre ${lo} et ${hi}`;
    $('hintRange').disabled = true;
  }

  const span = document.createElement('div');
  span.className   = 'hint-tag';
  span.textContent = text;
  $('hintTags').appendChild(span);
}

function getArc(n) {
  let a = ARCS[0][1];
  for (const [s, nm] of ARCS) { if (n >= s) a = nm; else break; }
  return a;
}

/* ── UTILS ── */
function shake(el) {
  el.animate(
    [{ transform: 'translateX(-5px)' }, { transform: 'translateX(5px)' }, { transform: 'translateX(0)' }],
    { duration: 240 }
  );
  el.style.borderColor = 'var(--ko-bd)';
  setTimeout(() => el.style.borderColor = '', 1000);
}

function openMangadex() {
  if (target) window.open('https://mangadex.org/chapter/' + target.id, '_blank');
}
