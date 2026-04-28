/* ══════════════════════════════════════════
   BLEACH — Quel Chapitre ? · chapitre.js
   ══════════════════════════════════════════ */

const BLEACH_ID = 'be5f4e76-b030-4b96-834c-a4a17792da4e';
const MAX_TRIES = 5;
const CLOSE_MARGIN = 15;

let target = null, tries = [], over = false, score = 0, streak = 0, best = 0, round = 0;
const $ = id => document.getElementById(id);

window.addEventListener('load', () => {
    const s = JSON.parse(localStorage.getItem('bqc_v1'));
    if (s) { score = s.score || 0; best = s.best || 0; }
    newRound();
});

/* ══════════════════════════════════════════
   RESET
   ══════════════════════════════════════════ */
async function newRound() {
    tries = []; over = false; target = null;

    ['imgBox','inputBox','feedback','result','errorBox'].forEach(id => {
        const el = $(id); if (el) el.style.display = 'none';
    });

    $('loadBox').style.display = 'flex';
    $('histBox').innerHTML = '';
    $('mangaImg').className = 'blurred';

    updTries();
    updStats();

    try {
        await loadPage();
    } catch(e) {
        console.error(e);
        $('loadBox').style.display = 'none';
        $('errorBox').style.display = 'flex';
        $('errMsg').textContent = "Connexion impossible.";
    }
}

/* ══════════════════════════════════════════
   FETCH API
   ══════════════════════════════════════════ */
async function apiGet(url) {
    const res = await fetch(`https://corsproxy.io/?${encodeURIComponent(url)}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
}

/* ══════════════════════════════════════════
   LOAD IMAGE
   ══════════════════════════════════════════ */
async function loadImage(chapterId) {
    for (let i = 0; i < 3; i++) {
        try {
            const pData = await apiGet(`https://api.mangadex.org/at-home/server/${chapterId}`);
            if (!pData?.chapter?.dataSaver?.length) throw new Error();

            const url = `${pData.baseUrl}/data-saver/${pData.chapter.hash}/${pData.chapter.dataSaver[0]}`;
            const img = $('mangaImg');

            await new Promise((resolve, reject) => {
                img.onload = resolve;
                img.onerror = reject;
                img.src = url;
            });

            return url;
        } catch {
            console.warn(`Retry image (${i + 1}/3)...`);
        }
    }
    throw new Error("Image failed");
}

/* ══════════════════════════════════════════
   LOAD CHAPITRE
   ══════════════════════════════════════════ */
async function loadPage(attempt = 0) {
    if (attempt > 5) throw new Error("Trop de tentatives");

    setLoad('🎲 Recherche...', 30);

    const offset = Math.floor(Math.random() * 400);
    const params = new URLSearchParams({
        limit: 50, offset,
        includeEmptyPages: 0,
        includeFuturePublishAt: 0,
        includeExternalUrl: 0
    });
    params.append('translatedLanguage[]', 'fr');
    params.append('contentRating[]', 'safe');
    params.append('order[chapter]', 'desc');

    const d = await apiGet(`https://api.mangadex.org/manga/${BLEACH_ID}/feed?${params.toString()}`);

    const valid = d?.data?.filter(c => !isNaN(parseFloat(c.attributes.chapter)));
    if (!valid?.length) return loadPage(attempt + 1);

    const chap = valid[Math.floor(Math.random() * valid.length)];
    setLoad('🖼 Image...', 70);

    const pageUrl = await loadImage(chap.id);

    target = { num: parseFloat(chap.attributes.chapter), id: chap.id, pageUrl };
    round++;

    $('loadBox').style.display = 'none';
    $('imgBox').style.display = 'block';
    $('inputBox').style.display = 'flex';
    updStats();
}

/* ══════════════════════════════════════════
   GAME
   ══════════════════════════════════════════ */
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

        if (res === 'correct') {
            score += 100;
            streak++;
            if (streak > best) best = streak;
        } else {
            streak = 0;
        }

        localStorage.setItem('bqc_v1', JSON.stringify({ score, best }));

        $('result').style.display = 'flex';
        $('resTtl').textContent = res === 'correct' ? '🎉 BIEN JOUÉ !' : '💀 PERDU !';
        $('resChap').textContent = "C'était le chapitre " + target.num;

        updStats();
    }
}

/* ══════════════════════════════════════════
   UI
   ══════════════════════════════════════════ */
function setLoad(m, p) {
    $('loadMsg').textContent = m;
    $('progFill').style.width = p + '%';
}

function updTries() {
    $('triesRow').innerHTML = '';
    for (let i = 0; i < MAX_TRIES; i++) {
        const d = document.createElement('div');
        d.className = 'try-dot' + (i < tries.length ? ' filled' : '');
        $('triesRow').appendChild(d);
    }
}

function updStats() {
    $('sScore').textContent = score;
    $('sStreak').textContent = streak;
    $('sBest').textContent = best;
    $('sRound').textContent = round;
}
