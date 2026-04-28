/* ══════════════════════════════════════════
   BLEACH — Quel Chapitre ? · chapitre.js
   Version Stable : Anti-429 & Multi-Proxy
   ══════════════════════════════════════════ */

const BLEACH_ID    = 'be5f4e76-b030-4b96-834c-a4a17792da4e';
const API_BASE     = 'https://api.mangadex.org';
const MAX_TRIES    = 5;
const CLOSE_MARGIN = 15;

// Liste de proxies pour alterner si l'un répond 429
const PROXIES = [
  url => `https://api.allorigins.win/raw?url=${encodeURIComponent(url)}`,
  url => `https://api.codetabs.com/v1/proxy?quest=${encodeURIComponent(url)}`,
  url => `https://corsproxy.io/?url=${encodeURIComponent(url)}`
];

let target = null, tries = [], over = false, score = 0, streak = 0, best = 0, round = 0;
const $ = id => document.getElementById(id);

// Petite fonction pour attendre (évite le spam)
const sleep = ms => new Promise(res => setTimeout(res, ms));

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
  
  // On mélange un peu les proxies pour ne pas toujours taper sur le même
  const shuffledProxies = [...PROXIES].sort(() => Math.random() - 0.5);

  for (const makeProxy of shuffledProxies) {
    try {
      const pUrl = makeProxy(fullUrl);
      const r = await fetch(pUrl, { cache: 'no-store' });
      
      if (r.status === 429) continue; // Si limite atteinte, on passe au proxy suivant

      if (r.ok) {
        const text = await r.text();
        try {
          const data = JSON.parse(text);
          return data.contents ? JSON.parse(data.contents) : data;
        } catch(e) { return JSON.parse(text); }
      }
    } catch(e) { console.warn("Proxy instable..."); }
  }
  throw new Error("Trop de requêtes. Attends 30 secondes.");
}

async function loadPage() {
  setLoad('🎲 Recherche...', 30);
  
  // On limite à 680 pour éviter les chapitres bonus inexistants
  const randomChap = Math.floor(Math.random() * 680) + 1;
  const path = `/manga/${BLEACH_ID}/feed?limit=1&chapter=${randomChap}&translatedLanguage=fr&contentRating=safe`;
  
  try {
    const d = await apiGet(path);

    // Si le chapitre n'existe pas en FR, on ne boucle pas direct ! On attend un peu.
    if (!d.data || d.data.length === 0) {
        await sleep(500); 
        return loadPage();
    }

    const chap = d.data[0];
    setLoad('🖼 Image...', 60);

    const pData = await apiGet(`/at-home/server/${chap.id}`);
    const pageUrl = `${pData.baseUrl}/data-saver/${pData.chapter.hash}/${pData.chapter.dataSaver[0]}`;

    target = { num: parseFloat(chap.attributes.chapter), id: chap.id, pageUrl };
    
    const img = $('mangaImg');
    // On utilise AllOrigins pour l'image car il est plus rapide pour le binaire
    img.src = `https://api.allorigins.win/raw?url=${encodeURIComponent(pageUrl)}`;
    
    img.onload = () => {
      round++;
      $('loadBox').style.display = 'none';
      $('imgBox').style.display = 'block';
      $('inputBox').style.display = 'flex';
      updStats();
    };
  } catch (err) {
    throw err;
  }
}

function submit() {
  if (over || !target) return;
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
