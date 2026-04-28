/* ══════════════════════════════════════════
   BLEACH — Quel Chapitre ? · chapitre.js
   Version "Hardcore" : Encodage d'URL strict
   ══════════════════════════════════════════ */

const BLEACH_ID    = 'be5f4e76-b030-4b96-834c-a4a17792da4e';
const API_BASE     = 'https://api.mangadex.org';
const MAX_TRIES    = 5;
const CLOSE_MARGIN = 15;

// AllOrigins est souvent le plus stable pour les APIs complexes
const PROXIES = [
  url => `https://api.allorigins.win/raw?url=${encodeURIComponent(url)}`,
  url => `https://corsproxy.io/?url=${encodeURIComponent(url)}`,
];

const ARCS = [
  [1,   'Agent de la Shinigami'], [70,  'Soul Society'], [182, 'Arrancar'],
  [240, 'Hueco Mundo'], [343, 'Fullbring'], [424, 'Guerre de 1000 ans']
];

let target = null, tries = [], over = false, hints = new Set(), score = 0, streak = 0, best = 0, round = 0;
const $ = id => document.getElementById(id);

window.addEventListener('load', () => { loadRec(); newRound(); });

function loadRec() {
  const s = JSON.parse(localStorage.getItem('bqc_v1'));
  if (s) { score = s.score || 0; best = s.best || 0; }
}

async function newRound() {
  tries = []; over = false; hints = new Set(); target = null;
  ['imgBox','inputBox','feedback','result','errorBox'].forEach(id => $(id).style.display = 'none');
  $('loadBox').style.display = 'flex';
  ['histBox','hintTags'].forEach(id => $(id).innerHTML = '');
  $('chapInput').value = ''; $('chapInput').disabled = false; $('subBtn').disabled = false;
  $('mangaImg').className = 'blurred';
  updTries(); updStats();
  
  try { await loadPage(); } 
  catch(e) { 
    $('loadBox').style.display = 'none'; 
    $('errorBox').style.display = 'flex';
    $('errMsg').textContent = e.message;
  }
}

// CETTE FONCTION CORRIGE L'ERREUR 400
async function apiGet(endpoint, params = {}) {
  const url = new URL(API_BASE + endpoint);
  Object.keys(params).forEach(key => url.searchParams.append(key, params[key]));
  const fullUrl = url.toString();

  for (const makeProxy of PROXIES) {
    try {
      const pUrl = makeProxy(fullUrl);
      const r = await fetch(pUrl, { cache: 'no-store', signal: AbortSignal.timeout(10000) });
      if (r.ok) {
        const res = await r.json();
        return res.contents ? JSON.parse(res.contents) : res;
      }
    } catch(e) { console.warn("Echec proxy..."); }
  }
  throw new Error("Serveurs indisponibles. Réessaie.");
}

async function loadPage() {
  setLoad('🎲 Recherche...', 30);
  const randomChap = Math.floor(Math.random() * 686) + 1;

  // Paramètres simplifiés pour éviter les erreurs 400
  const d = await apiGet(`/manga/${BLEACH_ID}/feed`, {
    'limit': 1,
    'chapter': randomChap,
    'translatedLanguage[]': 'fr',
    'contentRating[]': 'safe'
  });

  if (!d.data || d.data.length === 0) return loadPage();
  const chap = d.data[0];

  setLoad('🖼 Image...', 60);
  const pData = await apiGet(`/at-home/server/${chap.id}`);
  const pageUrl = `${pData.baseUrl}/data-saver/${pData.chapter.hash}/${pData.chapter.dataSaver[0]}`;

  target = { num: parseFloat(chap.attributes.chapter), id: chap.id, pageUrl };
  await loadImg(pageUrl);

  round++;
  $('loadBox').style.display = 'none';
  $('imgBox').style.display = 'block';
  $('inputBox').style.display = 'flex';
  updStats();
}

function loadImg(url) {
  return new Promise((res, rej) => {
    const img = $('mangaImg');
    img.onload = res;
    img.onerror = rej;
    // On passe l'image par AllOrigins pour éviter le blocage direct
    img.src = `https://api.allorigins.win/raw?url=${encodeURIComponent(url)}`;
  });
}

function setLoad(msg, pct) {
  $('loadMsg').textContent = msg;
  $('progFill').style.width = pct + '%';
}

function submit() {
  const raw = parseInt($('chapInput').value);
  if (isNaN(raw)) return;
  const diff = Math.abs(raw - target.num);
  const res = diff === 0 ? 'correct' : diff <= CLOSE_MARGIN ? 'close' : 'wrong';
  const arr = raw < target.num ? "▲ plus tard" : "▼ plus tôt";
  
  tries.push({ result: res });
  addHist(raw, res, diff, arr);
  updTries();
  if (res === 'correct' || tries.length >= MAX_TRIES) endRound(res === 'correct');
}

function endRound(won) {
  over = true;
  $('inputBox').style.display = 'none';
  $('mangaImg').classList.remove('blurred');
  if (won) { score += 50; streak++; if (streak > best) best = streak; } else { streak = 0; }
  localStorage.setItem('bqc_v1', JSON.stringify({ score, best }));
  $('result').style.display = 'flex';
  $('resTtl').textContent = won ? '🎉 GAGNE !' : '💀 PERDU !';
  $('resChap').textContent = 'Chapitre ' + target.num;
  $('resImg').src = `https://api.allorigins.win/raw?url=${encodeURIComponent(target.pageUrl)}`;
}

function addHist(g, r, d, a) {
  const item = document.createElement('div');
  item.className = 'hist-item ' + r;
  item.innerHTML = `<span>Ch. ${g}</span> <span>${r === 'correct' ? '✅' : a}</span>`;
  $('histBox').appendChild(item);
}

function updTries() {
  $('triesRow').innerHTML = '';
  for (let i = 0; i < MAX_TRIES; i++) {
    const dot = document.createElement('div');
    dot.className = 'try-dot' + (i < tries.length ? ' filled' : '');
    $('triesRow').appendChild(dot);
  }
}

function updStats() {
  $('sScore').textContent = score;
  $('sStreak').textContent = streak;
  $('sBest').textContent = best;
  $('sRound').textContent = round;
}

function saveRec() { localStorage.setItem('bqc_v1', JSON.stringify({ score, best })); }
