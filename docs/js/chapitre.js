/* ══════════════════════════════════════════
   BLEACH — Quel Chapitre ? · chapitre.js
   Version ULTIME : Correction Double Encodage
   ══════════════════════════════════════════ */

const BLEACH_ID    = 'be5f4e76-b030-4b96-834c-a4a17792da4e';
const API_BASE     = 'https://api.mangadex.org';
const MAX_TRIES    = 5;
const CLOSE_MARGIN = 15;

// AllOrigins est le plus fiable ici car il ne modifie pas l'URL interne
const PROXIES = [
  url => `https://api.allorigins.win/raw?url=${encodeURIComponent(url)}`,
  url => `https://api.codetabs.com/v1/proxy?quest=${encodeURIComponent(url)}`
];

let target = null, tries = [], over = false, score = 0, streak = 0, best = 0, round = 0;
const $ = id => document.getElementById(id);

window.addEventListener('load', () => { 
  const s = JSON.parse(localStorage.getItem('bqc_v1'));
  if (s) { score = s.score || 0; best = s.best || 0; }
  newRound(); 
});

async function newRound() {
  tries = []; over = false; target = null;
  ['imgBox','inputBox','feedback','result','errorBox'].forEach(id => $(id).style.display = 'none');
  $('loadBox').style.display = 'flex';
  $('histBox').innerHTML = '';
  $('chapInput').value = '';
  $('mangaImg').className = 'blurred';
  updTries(); updStats();
  
  try { await loadPage(); } 
  catch(e) { 
    $('loadBox').style.display = 'none'; 
    $('errorBox').style.display = 'flex';
    $('errMsg').textContent = "Erreur : " + e.message;
  }
}

async function apiGet(path) {
  const fullUrl = API_BASE + path;
  
  for (const makeProxy of PROXIES) {
    try {
      const pUrl = makeProxy(fullUrl);
      const r = await fetch(pUrl, { cache: 'no-store' });
      if (r.ok) {
        const text = await r.text();
        // AllOrigins peut renvoyer le JSON direct ou dans .contents
        try {
          const data = JSON.parse(text);
          return data.contents ? JSON.parse(data.contents) : data;
        } catch(e) {
          return JSON.parse(text);
        }
      }
    } catch(e) { console.warn("Proxy instable, essai suivant..."); }
  }
  throw new Error("MangaDex est surchargé. Réessaie.");
}

async function loadPage() {
  setLoad('🎲 Recherche...', 30);
  const randomChap = Math.floor(Math.random() * 680) + 1;

  // URL SIMPLIFIÉE : On retire les crochets [] qui font planter les proxies
  // MangaDex accepte les paramètres sans crochets pour les filtres simples
  const path = `/manga/${BLEACH_ID}/feed?limit=1&chapter=${randomChap}&translatedLanguage=fr&contentRating=safe`;
  
  const d = await apiGet(path);

  if (!d.data || d.data.length === 0) {
      // Si pas de FR, on tente en anglais sans crochets non plus
      const dEn = await apiGet(`/manga/${BLEACH_ID}/feed?limit=1&chapter=${randomChap}&translatedLanguage=en&contentRating=safe`);
      if (!dEn.data || dEn.data.length === 0) return loadPage();
      var chap = dEn.data[0];
  } else {
      var chap = d.data[0];
  }

  setLoad('🖼 Image...', 60);
  const pData = await apiGet(`/at-home/server/${chap.id}`);
  const pageUrl = `${pData.baseUrl}/data-saver/${pData.chapter.hash}/${pData.chapter.dataSaver[0]}`;

  target = { num: parseFloat(chap.attributes.chapter), id: chap.id, pageUrl };
  
  // Chargement image via proxy
  const img = $('mangaImg');
  img.src = `https://api.allorigins.win/raw?url=${encodeURIComponent(pageUrl)}`;
  
  img.onload = () => {
    round++;
    $('loadBox').style.display = 'none';
    $('imgBox').style.display = 'block';
    $('inputBox').style.display = 'flex';
    updStats();
  };
}

function submit() {
  if (over) return;
  const raw = parseInt($('chapInput').value);
  if (isNaN(raw)) return;
  
  const diff = Math.abs(raw - target.num);
  const res = diff === 0 ? 'correct' : diff <= CLOSE_MARGIN ? 'close' : 'wrong';
  const arr = raw < target.num ? "▲ plus tard" : "▼ plus tôt";
  
  tries.push({ result: res });
  const item = document.createElement('div');
  item.className = 'hist-item ' + res;
  item.innerHTML = `<span>Ch. ${raw}</span> <span>${res === 'correct' ? '✅' : arr}</span>`;
  $('histBox').appendChild(item);
  
  updTries();
  $('chapInput').value = '';

  if (res === 'correct' || tries.length >= MAX_TRIES) {
    over = true;
    $('mangaImg').classList.remove('blurred');
    if (res === 'correct') { score += 100; streak++; if (streak > best) best = streak; } else { streak = 0; }
    localStorage.setItem('bqc_v1', JSON.stringify({ score, best }));
    $('result').style.display = 'flex';
    $('resTtl').textContent = res === 'correct' ? '🎉 BIEN JOUÉ !' : '💀 PERDU !';
    $('resChap').textContent = 'C\'était le chapitre ' + target.num;
    updStats();
  }
}

function setLoad(msg, pct) {
  $('loadMsg').textContent = msg;
  $('progFill').style.width = pct + '%';
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
