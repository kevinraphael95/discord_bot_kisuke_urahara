/* ═══════════════════════════════════════════════════════════════════
   SCANGUESS — De quel tome vient cette page ?
   ───────────────────────────────────────────────────────────────────
   But du jeu :
     Une page de Bleach s'affiche. Le joueur doit deviner le numéro
     du tome d'origine, en 5 essais, avec indicateur chaud/froid.

   Dépendances :
     - minijeux.css (styles)
     - corsproxy.io (proxy CORS pour sushiscan.fr)

   API externe :
     - sushiscan.fr → pages de manga

   Sections :
     1. CONSTANTES & ÉTAT
     2. INITIALISATION
     3. NOUVELLE MANCHE
     4. CHARGEMENT D'UN TOME
     5. SOUMISSION D'UNE RÉPONSE
     6. INTERFACE : CHARGEMENT / ESSAIS / STATS
   ═══════════════════════════════════════════════════════════════════ */

/* ───────────────────────────────────────────────────────────────────
   1. CONSTANTES & ÉTAT
   ─────────────────────────────────────────────────────────────────── */

const MAX_TRIES = 5;           // Nombre d'essais par manche
const CLOSE_MARGIN = 3;        // Écart max pour avoir "proche"
const MAX_VOLUME = 74;         // Bleach a 74 tomes

let target = null;             // { num, imgUrl }
let tries = [];                // Historique des essais [{ result }]
let over = false;              // Manche terminée ?
let score = 0;                 // Score total cumulé
let streak = 0;                // Série actuelle
let best = 0;                  // Meilleure série
let round = 0;                 // Numéro de manche

const $ = id => document.getElementById(id);

/* ───────────────────────────────────────────────────────────────────
   2. INITIALISATION
   ─────────────────────────────────────────────────────────────────── */

window.addEventListener("load", () => {
  // Charge score + record depuis localStorage
  const s = JSON.parse(localStorage.getItem("bqc_v1") || "null");
  if (s) {
    score = s.score || 0;
    best  = s.best  || 0;
  }
  newRound();
});

/* ───────────────────────────────────────────────────────────────────
   3. NOUVELLE MANCHE
   Reset l'état et lance le chargement d'un tome
   ─────────────────────────────────────────────────────────────────── */

async function newRound() {
  tries = [];
  over = false;
  target = null;

  // Cache les blocs image / input / résultat / erreur
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

/* ───────────────────────────────────────────────────────────────────
   4. CHARGEMENT D'UN TOME
   Récupère les pages via corsproxy → extrait une image aléatoire
   ─────────────────────────────────────────────────────────────────── */

async function fetchHtml(url) {
  const res = await fetch(`https://corsproxy.io/?${encodeURIComponent(url)}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.text();
}

async function loadVolume(attempt = 0) {
  if (attempt > 8) throw new Error("Trop de tentatives");

  setLoad("🎲 Tirage du tome...", 20);

  const num = Math.floor(Math.random() * MAX_VOLUME) + 1;
  const url = `https://sushiscan.fr/bleach-volume-${num}/`;

  // 1. Récupère le HTML du tome
  let html;
  try { html = await fetchHtml(url); }
  catch { return loadVolume(attempt + 1); }

  // 2. Extrait le JSON ts_reader (contient les URLs des images)
  const match = html.match(/ts_reader\.run\((.+?)\)\s*;/s);
  if (!match) return loadVolume(attempt + 1);

  let data;
  try { data = JSON.parse(match[1]); }
  catch { return loadVolume(attempt + 1); }

  const images = data?.sources?.[0]?.images;
  if (!images?.length) return loadVolume(attempt + 1);

  // 3. Choisit une page au hasard (pas la 1ère qui est la couv')
  const pageIndex = Math.floor(Math.random() * (images.length - 1)) + 1;
  const imgUrl = images[pageIndex];

  setLoad("🖼 Chargement image...", 70);

  // 4. Attend que l'image se charge
  await new Promise((resolve, reject) => {
    const img = $("mangaImg");
    img.onload = resolve;
    img.onerror = reject;
    img.src = imgUrl;
    setTimeout(reject, 10000);
  });

  target = { num, imgUrl };
  round++;

  // 5. Affiche le jeu
  $("loadBox").style.display = "none";
  $("imgBox").style.display = "block";
  $("inputBox").style.display = "flex";

  updStats();
}

/* ───────────────────────────────────────────────────────────────────
   5. SOUMISSION D'UNE RÉPONSE
   Compare au tome cible, détermine correct/close/wrong
   ─────────────────────────────────────────────────────────────────── */

function submit() {
  if (over || !target) return;

  const raw = parseInt($("chapInput").value);
  if (isNaN(raw) || raw < 1 || raw > MAX_VOLUME) return;

  const diff = Math.abs(raw - target.num);
  const res  = diff === 0 ? "correct" : diff <= CLOSE_MARGIN ? "close" : "wrong";
  const arr  = raw < target.num ? "▲ plus tard" : "▼ plus tôt";

  tries.push({ result: res });

  // Ajoute la ligne dans l'historique
  const item = document.createElement("div");
  item.className = "hist-item " + res;
  item.innerHTML = `<span>Tome ${raw}</span><span>${res === "correct" ? "✅" : arr}</span>`;
  $("histBox").appendChild(item);

  updTries();
  $("chapInput").value = "";

  // Fin de manche ?
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
    $("resTtl").textContent  = res === "correct" ? "🎉 BIEN JOUÉ !" : "💀 PERDU !";
    $("resChap").textContent = "C'était le tome " + target.num;

    updStats();
  }
}

/* ───────────────────────────────────────────────────────────────────
   6. INTERFACE : CHARGEMENT / ESSAIS / STATS
   ─────────────────────────────────────────────────────────────────── */

function setLoad(m, p) {
  $("loadMsg").textContent = m;
  $("progFill").style.width = p + "%";
}

// Affiche les 5 pastilles d'essai (vert/jaune/rouge selon résultat)
function updTries() {
  $("triesRow").innerHTML = "";
  for (let i = 0; i < MAX_TRIES; i++) {
    const d = document.createElement("div");
    d.className = "try-dot" + (i < tries.length ? " " + tries[i].result : "");
    $("triesRow").appendChild(d);
  }
}

function updStats() {
  $("sScore").textContent  = score;
  $("sStreak").textContent = streak;
  $("sBest").textContent   = best;
  $("sRound").textContent  = round;
}

/* ───────────────────────────────────────────────────────────────────
   EXPORT GLOBAL (nécessaire car appelé via onclick="...")
   ─────────────────────────────────────────────────────────────────── */

window.submit  = submit;
window.newRound = newRound;