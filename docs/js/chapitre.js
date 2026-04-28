/* ══════════════════════════════════════════
   BLEACH — Quel Chapitre ? · chapitre.js
   Version ULTRA-LIGHT : Fix Proxy & Performance
   ══════════════════════════════════════════ */

const BLEACH_ID    = 'be5f4e76-b030-4b96-834c-a4a17792da4e';
const MAX_TRIES    = 5;
const CLOSE_MARGIN = 15;

// On utilise un proxy plus performant (Hyzis ou 1001)
const PROXIES = [
  url => `https://api.allorigins.win/raw?url=${encodeURIComponent(url)}`,
  url => `https://thingproxy.freeboard.io/fetch/${url}`
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
    $('errMsg').textContent = "MangaDex met trop de temps à répondre. Réessaie.";
  }
}

async function apiGet(url) {
  // On tente sans proxy d'abord (certains navigateurs l'acceptent pour MangaDex)
  // Sinon on boucle sur les proxies
  for (const makeProxy of PROXIES) {
    try {
      const pUrl = makeProxy(url);
      const r = await fetch(pUrl);
      if (r.ok) {
        const data = await r.json();
        return data.contents ? JSON.parse(data.contents) : data;
      }
    } catch(e) { continue; }
  }
  throw new Error("Timeout");
}

async function loadPage() {
  setLoad('🎲 Recherche...', 30);
  
  // ASTUCE : On demande les 100 derniers chapitres d'un coup pour éviter de boucler
  // On choisit ensuite un chapitre au hasard dans cette liste
  const offset = Math.floor(Math.random() * 500);
  const feedUrl = `https://api.mangadex.org/manga/${BLEACH_ID}/feed?limit=100&offset=${offset}&translatedLanguage[]=fr&contentRating[]=safe&order[chapter]=asc`;
  
  const d = await apiGet(feedUrl);
  if (!d.data || d.data.length === 0) return loadPage();

  // On prend un chapitre au hasard dans la liste reçue
  const chap = d.data[Math.floor(Math.random() * d.data.length)];
  
  setLoad('🖼 Image...', 70);
  const serverUrl = `https://api.mangadex.org/at-home/server/${chap.id}`;
  const pData = await apiGet(serverUrl);
  
  const pageUrl = `${pData.baseUrl}/data-saver/${pData.chapter.hash}/${pData.chapter.dataSaver[0]}`;
  target = { num: parseFloat(chap.attributes.chapter), id: chap.id, pageUrl };
  
  // Pour l'image, on tente le lien direct MangaDex (souvent autorisé)
  const img = $('mangaImg');
  img.src = pageUrl; 

  // Si l'image direct échoue (CORS), on passe par AllOrigins
  img.onerror = () => {
    img.src = `https://api.allorigins.win/raw?url=${encodeURIComponent(pageUrl)}`;
  };
  
  img.onload = () => {
    round++;
    $('loadBox').style.display = 'none';
    $('imgBox').style.display = 'block';
    $('inputBox').style.display = 'flex';
    updStats();
  };
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
