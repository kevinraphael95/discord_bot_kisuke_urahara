const MAX_TRIES = 5;
const CLOSE_MARGIN = 10;
const MAX_CHAPTER = 686;

let target = null, tries = [], over = false, score = 0, streak = 0, best = 0, round = 0;
const $ = id => document.getElementById(id);

window.addEventListener('load', () => {
    const s = JSON.parse(localStorage.getItem('bqc_ch_v1') || 'null');
    if (s) { score = s.score || 0; best = s.best || 0; }
    newRound();
});

async function newRound() {
    tries = []; over = false; target = null;

    ['imgBox','inputBox','feedback','result','errorBox'].forEach(id => {
        const el = $(id); if (el) el.style.display = 'none';
    });

    $('loadBox').style.display = 'flex';
    $('histBox').innerHTML = '';
    $('mangaImg').className = '';

    updTries();
    updStats();

    try {
        await loadChapter();
    } catch(e) {
        console.error(e);
        $('loadBox').style.display = 'none';
        $('errorBox').style.display = 'flex';
        $('errMsg').textContent = "Connexion impossible.";
    }
}

async function fetchHtml(url) {
    const res = await fetch(`https://corsproxy.io/?${encodeURIComponent(url)}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.text();
}

async function loadChapter(attempt = 0) {
    if (attempt > 8) throw new Error("Trop de tentatives");

    setLoad('🎲 Tirage du chapitre...', 20);

    const num = Math.floor(Math.random() * MAX_CHAPTER) + 1;
    const url = `https://sushiscan.fr/bleach-chapitre-${num}/`;

    let html;
    try {
        html = await fetchHtml(url);
    } catch {
        return loadChapter(attempt + 1);
    }

    const match = html.match(/ts_reader\.run\((.+?)\)\s*;/s);
    if (!match) return loadChapter(attempt + 1);

    let data;
    try {
        data = JSON.parse(match[1]);
    } catch {
        return loadChapter(attempt + 1);
    }

    const images = data?.sources?.[0]?.images;
    if (!images?.length) return loadChapter(attempt + 1);

    const pageIndex = Math.floor(Math.random() * (images.length - 1)) + 1;
    const imgUrl = images[pageIndex];

    setLoad('🖼 Chargement image...', 70);

    await new Promise((resolve, reject) => {
        const img = $('mangaImg');
        img.onload = resolve;
        img.onerror = reject;
        img.src = imgUrl;
        setTimeout(reject, 10000);
    });

    target = { num, imgUrl };
    round++;

    $('loadBox').style.display = 'none';
    $('imgBox').style.display = 'block';
    $('inputBox').style.display = 'flex';
    updStats();
}

function submit() {
    if (over || !target) return;

    const raw = parseInt($('chapInput').value);
    if (isNaN(raw) || raw < 1 || raw > MAX_CHAPTER) return;

    const diff = Math.abs(raw - target.num);
    const res = diff === 0 ? 'correct' : diff <= CLOSE_MARGIN ? 'close' : 'wrong';
    const arr = raw < target.num ? "▲ plus tard" : "▼ plus tôt";

    tries.push({ result: res });

    const item = document.createElement('div');
    item.className = 'hist-item ' + res;
    item.innerHTML = `<span>Chapitre ${raw}</span> <span>${res === 'correct' ? '✅' : arr}</span>`;
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

        localStorage.setItem('bqc_ch_v1', JSON.stringify({ score, best }));

        $('result').style.display = 'flex';
        $('resTtl').textContent = res === 'correct' ? '🎉 BIEN JOUÉ !' : '💀 PERDU !';
        $('resChap').textContent = "C'était le chapitre " + target.num;

        updStats();
    }
}

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
