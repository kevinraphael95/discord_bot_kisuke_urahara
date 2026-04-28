/* ══════════════════════════════════════════
   BLEACH — Quel Chapitre ? · chapitre.js
   Version stabilisée : Fix Erreur 400 & CORS
   ══════════════════════════════════════════ */

const BLEACH_ID    = 'be5f4e76-b030-4b96-834c-a4a17792da4e';
const API_BASE     = 'https://api.mangadex.org';
const MAX_TRIES    = 5;
const CLOSE_MARGIN = 15;

// AllOrigins est mis en premier car il est plus tolérant sur les caractères spéciaux
const PROXIES = [
  url => `https://api.allorigins.win/raw?url=${encodeURIComponent(url)}`,
  url => `https://corsproxy.io/?url=${encodeURIComponent(url)}`,
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

let target = null, tries = [], over = false, hints = new Set();
let score = 0, streak = 0, best = 0, round = 0;

const $ = id => document.getElementById(id);

window.addEventListener('load', () => {
  loadRec();
  newRound();
});

function loadRec() {
  try {
    const s = JSON.parse(localStorage.getItem('bqc_v1'));
    if (s) { score = s.score || 0; best = s.best || 0; }
  } catch(e) {}
}

function saveRec() {
  try { localStorage.setItem('bqc_v1', JSON.stringify({ score, best })); } catch(e) {}
}

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
    $('errMsg').textContent = 'Erreur réseau : ' + e.message;
    $('errorBox').style.display = 'flex';
  }
}

async function apiGet(path) {
  const fullUrl = API_BASE + path;
  for (const makeProxy of PROXIES) {
    try {
      const proxyUrl = makeProxy(fullUrl);
      const r = await fetch(proxyUrl, { 
        cache: 'no-store', 
        signal: AbortSignal.timeout(15000) // Timeout étendu à 15s
      });

      if (r.ok) {
        const text = await r.text();
        try {
          const json = JSON.parse(text);
          // Gère le format spécifique de AllOrigins
          return json.contents ? JSON.parse(json.contents) : json;
        } catch (err) { continue; }
      }
    } catch(e) { console.warn('Proxy échoué, essai suivant...'); }
  }
  throw new Error('Tous les proxies ont échoué. Réessaie dans un instant.');
}

async function loadPage() {
  setLoad('🎲 Recherche d\'un chapitre...', 30);

  // Tirage aléatoire entre 1 et 686
  const randomChap = Math.floor(Math.random() * 686) + 1;

  // On simplifie la requête pour éviter l'erreur 400 (Bad Request) sur les proxies
  const path = `/manga/${BLEACH_ID}/feed?limit=1&chapter=${randomChap}&translatedLanguage[]=fr&contentRating[]=safe`;
  
  const d = await apiGet(path);

  // Si pas de VF, on tente sans filtre de langue (souvent de l'Anglais par défaut)
  if (!d.data || d.data.length === 0) {
      const fallbackPath = `/manga/${BLEACH_ID}/feed?limit=1&chapter=${randomChap}&contentRating[]=safe`;
      const dFallback = await apiGet(fallbackPath);
      if (!dFallback.data || dFallback.data.length === 0) return loadPage();
      var chap = dFallback.data[0];
  } else {
      var chap = d.data[0];
  }

  setLoad('🖼 Préparation de l\'image...', 60);

  const pData = await apiGet(`/at-home/server/${chap.id}`);
  const hash = pData.chapter.hash;
  const pages = pData.chapter.dataSaver;
  
  if (!pages?.length) return loadPage();

  const idx = pages.length > 1 ? 1 + Math.floor(Math.random() * (pages.length - 1)) : 0;
  const pageUrl = `${pData.baseUrl}/data-saver/${hash}/${pages[idx]}`;

  target = {
    num: parseFloat(chap.attributes.chapter),
    id: chap.id,
    title: chap.attributes.title || '',
    pageUrl: pageUrl
  };

  await loadImg(pageUrl);

  round++;
  $('loadBox').style.display = 'none';
  $('imgBox').style.display = 'block';
  $('inputBox').style.display = 'flex';
  $('chapInput').focus();
  updStats();
}

function loadImg(url) {
  return new Promise((res, rej) => {
    const img = $('mangaImg');
    img.onload = res;
    img.onerror = () => rej(new Error('Image bloquée par MangaDex'));
    // Utilisation de AllOrigins pour l'image également pour plus de fiabilité
    img.src = `https://api.allorigins.win/raw?url=${encodeURIComponent(url)}`;
  });
}

function setLoad(msg, pct) {
  $('loadMsg').textContent = msg;
  $('progFill').style.width = pct + '%';
}

function submit() {
  if (over || !target) return;
  const raw = parseInt($('chapInput').value);
  if (isNaN(raw) || raw < 1 || raw > 750) { shake($('chapInput')); return; }

  const diff = Math.abs(raw - target.num);
  const res = diff === 0 ? 'correct' : diff <= CLOSE_MARGIN ? 'close' : 'wrong';
  const arr = raw < target.num ? "▲ plus tard" : raw > target.num ? "▼ plus tôt" : '';

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

function showFeedback(res, diff, arr) {
  const fb = $('feedback');
  fb.style.display = 'flex';
  fb.className = res;
  $('fbTitle').textContent = res === 'close' ? '🟡 Pas loin !' : '❌ Raté';
  $('fbDetail').textContent = `${arr} (Écart: ${diff}). Il reste ${MAX_TRIES - tries.length} essais.`;
}

function endRound(won) {
  over = true;
  $('chapInput').disabled = true;
  $('subBtn').disabled = true;
  $('feedback').style.display = 'none';
  $('inputBox').style.display = 'none';
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
  $('resTtl').textContent = won ? '🎉 Bravo !' : '💀 Perdu !';
  // On repasse par proxy pour l'image de résultat également
  $('resImg').src = `https://api.allorigins.win/raw?url=${encodeURIComponent(target.pageUrl)}`;
  $('resChap').textContent = 'Chapitre ' + target.num;
  $('resArc').textContent = (target.title ? '"' + target.title + '" — ' : '') + getArc(target.num);
}

function addHist(guess, res, diff, arr) {
  const d = document.createElement('div');
  d.className = 'hist-item ' + res;
  const badge = res === 'correct' ? '✅' : res === 'close' ? '🟡' : '❌';
  d.innerHTML = `<span>Ch. ${guess}</span><span>${arr} ${badge}</span>`;
  $('histBox').appendChild(d);
}

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
  $('sScore').textContent = score;
  $('sStreak').textContent = streak;
  $('sBest').textContent = best;
  $('sRound').textContent = round;
}

function giveHint(type) {
  if (hints.has(type) || !target) return;
  hints.add(type);
  if (type === 'unblur') {
    $('mangaImg').classList.remove('blurred');
    $('hintUnblur').disabled = true;
  } else if (type === 'arc') {
    const span = document.createElement('div');
    span.className = 'hint-tag';
    span.textContent = '🗡 Arc : ' + getArc(target.num);
    $('hintTags').appendChild(span);
    $('hintArc').disabled = true;
  } else if (type === 'range') {
    const span = document.createElement('div');
    span.className = 'hint-tag';
    const lo = Math.max(1, Math.floor(target.num - 40));
    const hi = Math.min(686, Math.floor(target.num + 40));
    span.textContent = `📐 Entre ${lo} et ${hi}`;
    $('hintTags').appendChild(span);
    $('hintRange').disabled = true;
  }
}

function getArc(n) {
  let a = ARCS[0][1];
  for (const [s, nm] of ARCS) { if (n >= s) a = nm; else break; }
  return a;
}

function shake(el) {
  el.animate([{ transform: 'translateX(-5px)' }, { transform: 'translateX(5px)' }, { transform: 'translateX(0)' }], { duration: 200 });
}

function openMangadex() {
  if (target) window.open('https://mangadex.org/chapter/' + target.id, '_blank');
}
