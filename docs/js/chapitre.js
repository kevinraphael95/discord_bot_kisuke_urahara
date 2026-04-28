/* ══════════════════════════════════════════
   BLEACH — Quel Chapitre ? · chapitre.js
   Version RESISTANCE : Proxy Pro & Anti-CORS
   ══════════════════════════════════════════ */

const BLEACH_ID = 'be5f4e76-b030-4b96-834c-a4a17792da4e';
const MAX_TRIES = 5;
const CLOSE_MARGIN = 15;

// On utilise un proxy plus moderne et moins surchargé
const PROXIES = [
    url => `https://api.allorigins.win/raw?url=${encodeURIComponent(url)}`,
    url => `https://cors-anywhere.herokuapp.com/${url}`, // Nécessite souvent d'activer l'accès sur leur site
    url => `https://proxy.cors.sh/${url}`
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
    ['imgBox','inputBox','feedback','result','errorBox'].forEach(id => {
        const el = $(id); if(el) el.style.display = 'none';
    });
    $('loadBox').style.display = 'flex';
    $('histBox').innerHTML = '';
    $('mangaImg').className = 'blurred';
    updTries(); updStats();
    try { await loadPage(); } 
    catch(e) { 
        $('loadBox').style.display = 'none'; 
        $('errorBox').style.display = 'flex';
        $('errMsg').textContent = "Connexion impossible. MangaDex ou le Proxy est saturé.";
    }
}

async function apiGet(url) {
    // Tentative avec AllOrigins (nettoyé)
    try {
        const response = await fetch(`https://api.allorigins.win/get?url=${encodeURIComponent(url)}`);
        if (response.ok) {
            const data = await response.json();
            return JSON.parse(data.contents);
        }
    } catch(e) {
        console.warn("AllOrigins a échoué, tentative alternative...");
    }

    // Proxy de secours n°2 (Bypass direct)
    try {
        const res = await fetch(`https://corsproxy.io/?${encodeURIComponent(url)}`);
        if (res.ok) return await res.json();
    } catch(e) {}

    throw new Error("Timeout");
}

async function loadPage() {
    setLoad('🎲 Recherche...', 30);
    
    // On demande un offset aléatoire mais fixe pour éviter de trop solliciter l'API
    const offset = Math.floor(Math.random() * 400);
    // ON NE MET PAS DE CROCHETS [] DANS L'URL POUR LE PROXY
    const feedUrl = `https://api.mangadex.org/manga/${BLEACH_ID}/feed?limit=50&offset=${offset}&translatedLanguage=fr&contentRating=safe`;
    
    const d = await apiGet(feedUrl);
    if (!d || !d.data || d.data.length === 0) return loadPage();

    const chap = d.data[Math.floor(Math.random() * d.data.length)];
    
    setLoad('🖼 Image...', 70);
    const serverUrl = `https://api.mangadex.org/at-home/server/${chap.id}`;
    const pData = await apiGet(serverUrl);
    
    const pageUrl = `${pData.baseUrl}/data-saver/${pData.chapter.hash}/${pData.chapter.dataSaver[0]}`;
    target = { num: parseFloat(chap.attributes.chapter), id: chap.id, pageUrl };
    
    const img = $('mangaImg');
    // On passe l'image par un proxy simple
    img.src = `https://corsproxy.io/?${encodeURIComponent(pageUrl)}`;

    img.onload = () => {
        round++;
        $('loadBox').style.display = 'none';
        $('imgBox').style.display = 'block';
        $('inputBox').style.display = 'flex';
        updStats();
    };

    img.onerror = () => {
        // Si corsproxy échoue, on tente AllOrigins pour l'image
        img.src = `https://api.allorigins.win/raw?url=${encodeURIComponent(pageUrl)}`;
    };
}

// ... (reste du code submit, updStats, etc. identique)

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
        $('mangaImg').className = '';
        if (res === 'correct') { score += 100; streak++; if (streak > best) best = streak; } else { streak = 0; }
        localStorage.setItem('bqc_v1', JSON.stringify({ score, best }));
        $('result').style.display = 'flex';
        $('resTtl').textContent = res === 'correct' ? '🎉 BIEN JOUÉ !' : '💀 PERDU !';
        $('resChap').textContent = 'C\'était le chapitre ' + target.num;
        updStats();
    }
}
function setLoad(m, p) { $('loadMsg').textContent = m; $('progFill').style.width = p + '%'; }
function updTries() {
    $('triesRow').innerHTML = '';
    for (let i = 0; i < MAX_TRIES; i++) {
        const d = document.createElement('div');
        d.className = 'try-dot' + (i < tries.length ? ' filled' : '');
        $('triesRow').appendChild(d);
    }
}
function updStats() {
    $('sScore').textContent = score; $('sStreak').textContent = streak;
    $('sBest').textContent = best; $('sRound').textContent = round;
}
