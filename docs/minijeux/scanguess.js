const MAX_TRIES = 5;
const CLOSE_MARGIN = 3;
const MAX_VOLUME = 74;

let target = null;
let tries = [];
let over = false;
let score = 0;
let streak = 0;
let best = 0;
let round = 0;

const $ = id => document.getElementById(id);

/* ── INIT ── */
window.addEventListener("load", () => {
    const s = JSON.parse(localStorage.getItem("bqc_v1") || "null");
    if (s) {
        score = s.score || 0;
        best = s.best || 0;
    }
    newRound();
});

/* ── NEW ROUND ── */
async function newRound() {
    tries = [];
    over = false;
    target = null;

    const hide = ["imgBox", "inputBox", "result", "errorBox"];
    hide.forEach(id => {
        const el = $(id);
        if (el) el.style.display = "none";
    });

    $("loadBox").style.display = "flex";
    $("histBox").innerHTML = "";

    updTries();
    updStats();

    try {
        await loadVolume();
    } catch (e) {
        console.error(e);
        $("loadBox").style.display = "none";
        $("errorBox").style.display = "flex";
        $("errMsg").textContent = "Connexion impossible.";
    }
}

/* ── FETCH HTML ── */
async function fetchHtml(url) {
    const res = await fetch(`https://corsproxy.io/?${encodeURIComponent(url)}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.text();
}

/* ── LOAD VOLUME ── */
async function loadVolume(attempt = 0) {
    if (attempt > 8) throw new Error("Trop de tentatives");

    setLoad("🎲 Tirage du tome...", 20);

    const num = Math.floor(Math.random() * MAX_VOLUME) + 1;
    const url = `https://sushiscan.fr/bleach-volume-${num}/`;

    let html;
    try {
        html = await fetchHtml(url);
    } catch {
        return loadVolume(attempt + 1);
    }

    const match = html.match(/ts_reader\.run\((.+?)\)\s*;/s);
    if (!match) return loadVolume(attempt + 1);

    let data;
    try {
        data = JSON.parse(match[1]);
    } catch {
        return loadVolume(attempt + 1);
    }

    const images = data?.sources?.[0]?.images;
    if (!images?.length) return loadVolume(attempt + 1);

    const pageIndex = Math.floor(Math.random() * (images.length - 1)) + 1;
    const imgUrl = images[pageIndex];

    setLoad("🖼 Chargement image...", 70);

    await new Promise((resolve, reject) => {
        const img = $("mangaImg");
        img.onload = resolve;
        img.onerror = reject;
        img.src = imgUrl;

        setTimeout(reject, 10000);
    });

    target = { num, imgUrl };
    round++;

    $("loadBox").style.display = "none";
    $("imgBox").style.display = "block";
    $("inputBox").style.display = "flex";

    updStats();
}

/* ── SUBMIT ── */
function submit() {
    if (over || !target) return;

    const raw = parseInt($("chapInput").value);
    if (isNaN(raw) || raw < 1 || raw > MAX_VOLUME) return;

    const diff = Math.abs(raw - target.num);
    const res = diff === 0 ? "correct" : diff <= CLOSE_MARGIN ? "close" : "wrong";
    const arr = raw < target.num ? "▲ plus tard" : "▼ plus tôt";

    tries.push({ result: res });

    const item = document.createElement("div");
    item.className = "hist-item " + res;
    item.innerHTML = `<span>Tome ${raw}</span><span>${res === "correct" ? "✅" : arr}</span>`;
    $("histBox").appendChild(item);

    updTries();
    $("chapInput").value = "";

    if (res === "correct" || tries.length >= MAX_TRIES) {
        over = true;

        if (res === "correct") {
            score += 100;
            streak++;
            if (streak > best) best = streak;
        } else {
            streak = 0;
        }

        localStorage.setItem("bqc_v1", JSON.stringify({ score, best }));

        $("result").style.display = "flex";
        $("resTtl").textContent = res === "correct" ? "🎉 BIEN JOUÉ !" : "💀 PERDU !";
        $("resChap").textContent = "C'était le tome " + target.num;

        updStats();
    }
}

/* ── LOADING UI ── */
function setLoad(m, p) {
    $("loadMsg").textContent = m;
    $("progFill").style.width = p + "%";
}

/* ── TRIES UI ── */
function updTries() {
    $("triesRow").innerHTML = "";

    for (let i = 0; i < MAX_TRIES; i++) {
        const d = document.createElement("div");
        d.className = "try-dot" + (i < tries.length ? " " + tries[i].result : "");
        $("triesRow").appendChild(d);
    }
}

/* ── STATS ── */
function updStats() {
    $("sScore").textContent = score;
    $("sStreak").textContent = streak;
    $("sBest").textContent = best;
    $("sRound").textContent = round;
}

/* ── GLOBAL EXPORT (important si onclick HTML) ── */
window.submit = submit;
window.newRound = newRound;
