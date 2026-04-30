const MAX_VOLUME = 74;
const $ = id => document.getElementById(id);

let imgA = null, imgB = null;
let usedImages = new Set();
let streak = 0, best = 0, loading = false;

window.addEventListener('load', () => {
    const s = JSON.parse(localStorage.getItem('bqc_tl_v1') || 'null');
    if (s) { best = s.best || 0; }
    updStats();
    startGame();
});

async function fetchHtml(url) {
    const res = await fetch(`https://corsproxy.io/?${encodeURIComponent(url)}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.text();
}

async function fetchRandomPage(attempt = 0) {
    if (attempt > 15) throw new Error("Trop de tentatives");
    const num = Math.floor(Math.random() * MAX_VOLUME) + 1;
    const url = `https://sushiscan.fr/bleach-volume-${num}/`;
    let html;
    try { html = await fetchHtml(url); } catch { return fetchRandomPage(attempt + 1); }
    const match = html.match(/ts_reader\.run\((.+?)\)\s*;/s);
    if (!match) return fetchRandomPage(attempt + 1);
    let data;
    try { data = JSON.parse(match[1]); } catch { return fetchRandomPage(attempt + 1); }
    const images = data?.sources?.[0]?.images;
    if (!images?.length) return fetchRandomPage(attempt + 1);
    const pageIndex = Math.floor(Math.random() * (images.length - 1)) + 1;
    const imgUrl = images[pageIndex];
    if (usedImages.has(imgUrl)) return fetchRandomPage(attempt + 1);
    return { num, imgUrl };
}

async function loadImg(elId, data) {
    return new Promise((resolve, reject) => {
        const el = $(elId);
        const timeout = setTimeout(reject, 10000);
        el.onload = () => { clearTimeout(timeout); resolve(); };
        el.onerror = reject;
        el.src = data.imgUrl;
    });
}

async function startGame() {
    if (loading) return;
    loading = true;
    showState('loading');

    try {
        // Charger deux images différentes en parallèle
        let a, b;
        a = await fetchRandomPage();
        usedImages.add(a.imgUrl);
        do { b = await fetchRandomPage(); } while (b.num === a.num);
        usedImages.add(b.imgUrl);

        imgA = a; imgB = b;

        await Promise.all([loadImg('imgA', imgA), loadImg('imgB', imgB)]);

        showState('game');
    } catch(e) {
        console.error(e);
        showState('error');
    }
    loading = false;
}

function answer(choice) {
    if (loading) return;

    // choice = 'before' | 'after'
    const correct = (choice === 'before' && imgB.num < imgA.num) ||
                    (choice === 'after'  && imgB.num > imgA.num);

    if (correct) {
        streak++;
        if (streak > best) {
            best = streak;
            localStorage.setItem('bqc_tl_v1', JSON.stringify({ best }));
        }
        updStats();
        // L'image B devient la nouvelle image A, on charge une nouvelle B
        nextRound();
    } else {
        showResult(false);
    }
}

async function nextRound() {
    if (loading) return;
    loading = true;
    showState('loading');

    try {
        // imgB devient le nouveau imgA
        imgA = imgB;
        $('imgA').src = imgA.imgUrl;

        let b;
        do { b = await fetchRandomPage(); } while (b.num === imgA.num);
        usedImages.add(b.imgUrl);
        imgB = b;

        await loadImg('imgB', imgB);
        showState('game');
    } catch(e) {
        showState('error');
    }
    loading = false;
}

function showResult(win) {
    showState('result');
    if (!win) {
        $('resStreak').textContent = streak;
        $('resBest').textContent = best;
        streak = 0;
        updStats();
        localStorage.setItem('bqc_tl_v1', JSON.stringify({ best }));
    }
}

function restart() {
    usedImages = new Set();
    imgA = null; imgB = null;
    startGame();
}

function showState(state) {
    ['loadBox','gameBox','resultBox','errorBox'].forEach(id => {
        const el = $(id); if (el) el.style.display = 'none';
    });
    if (state === 'loading') $('loadBox').style.display = 'flex';
    if (state === 'game')    $('gameBox').style.display = 'flex';
    if (state === 'result')  $('resultBox').style.display = 'flex';
    if (state === 'error')   $('errorBox').style.display = 'flex';
}

function updStats() {
    $('sStreak').textContent = streak;
    $('sBest').textContent = best;
}
