/* ═══════════════════════════════════════════════════════════════════
   AVANT OU APRÈS — La 2e image est-elle avant/après la 1ère ?
   ───────────────────────────────────────────────────────────────────
   But du jeu :
     Deux pages de Bleach s'affichent. Le joueur doit dire si la 2e
     vient AVANT ou APRÈS la 1ère dans le manga.
     La comparaison se fait sur le numéro de page dans le même volume.

   Dépendances :
     - minijeux.css (styles)
     - corsproxy.io (proxy pour contourner CORS sur sushiscan.fr)

   API externe :
     - sushiscan.fr → pages de manga

   Sections :
     1. ÉTAT GLOBAL
     2. INITIALISATION
     3. FETCH HTML (proxy)
     4. TIRAGE DES PAGES
     5. CHARGEMENT DES IMAGES
     6. DÉMARRAGE / PARTIE SUIVANTE
     7. RÉPONSE DU JOUEUR
     8. ÉCRAN DE RÉSULTAT
     9. RELANCE / UTILITAIRES
    10. GESTION DES ÉTATS DE L'INTERFACE
   ═══════════════════════════════════════════════════════════════════ */

/* ───────────────────────────────────────────────────────────────────
   1. ÉTAT GLOBAL
   ─────────────────────────────────────────────────────────────────── */

const MAX_VOLUME = 74;                        // Bleach a 74 tomes
const $ = id => document.getElementById(id);

let imgA = null, imgB = null;                 // { num, imgUrl, pageIndex }
let usedImages = new Set();                   // Pour éviter les doublons
let streak = 0;                               // Série actuelle
let best = 0;                                 // Meilleure série
let loading = false;                          // Évite les clics pendant un chargement

/* ───────────────────────────────────────────────────────────────────
   2. INITIALISATION
   ─────────────────────────────────────────────────────────────────── */

window.addEventListener('load', () => {
  const s = JSON.parse(localStorage.getItem('bqc_tl_v1') || 'null');
  if (s) best = s.best || 0;
  updStats();
  startGame();
});

/* ───────────────────────────────────────────────────────────────────
   3. FETCH HTML (proxy)
   On passe par corsproxy.io pour éviter le blocage CORS de sushiscan.fr
   ─────────────────────────────────────────────────────────────────── */

async function fetchHtml(url) {
  const res = await fetch(`https://corsproxy.io/?${encodeURIComponent(url)}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.text();
}

// Met à jour le message de chargement + la barre de progression
function setLoad(msg, pct) {
  $('loadMsg').textContent = msg;
  $('progFill').style.width = pct + '%';
}

/* ───────────────────────────────────────────────────────────────────
   4. TIRAGE DES PAGES
   Va chercher les pages d'un tome et en tire une au hasard
   ─────────────────────────────────────────────────────────────────── */

// Tire une page depuis un tome aléatoire
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

  return { num, imgUrl, pageIndex };
}

// Tire une page dans un tome précis (en excluant un index donné)
async function fetchRandomPageInVolume(num, excludeIndex = -1, attempt = 0) {
  if (attempt > 15) throw new Error("Trop de tentatives");
  const url = `https://sushiscan.fr/bleach-volume-${num}/`;

  let html;
  try { html = await fetchHtml(url); } catch { return fetchRandomPageInVolume(num, excludeIndex, attempt + 1); }

  const match = html.match(/ts_reader\.run\((.+?)\)\s*;/s);
  if (!match) throw new Error("Parse fail");

  let data;
  try { data = JSON.parse(match[1]); } catch { throw new Error("JSON fail"); }

  const images = data?.sources?.[0]?.images;
  if (!images?.length) throw new Error("No images");

  // Cherche un index différent de celui d'imgA et non déjà utilisé
  let pageIndex;
  let tries = 0;
  do {
    pageIndex = Math.floor(Math.random() * (images.length - 1)) + 1;
    tries++;
    if (tries > 50) throw new Error("Pas assez de pages distinctes");
  } while (usedImages.has(images[pageIndex]) || pageIndex === excludeIndex);

  const imgUrl = images[pageIndex];
  usedImages.add(imgUrl);
  return { num, imgUrl, pageIndex };
}

/* ───────────────────────────────────────────────────────────────────
   5. CHARGEMENT DES IMAGES
   Attend qu'une <img> se charge (avec timeout)
   ─────────────────────────────────────────────────────────────────── */

function loadImgEl(elId, data) {
  return new Promise((resolve, reject) => {
    const el = $(elId);
    const timeout = setTimeout(reject, 12000);
    el.onload  = () => { clearTimeout(timeout); resolve(); };
    el.onerror = () => { clearTimeout(timeout); reject(); };
    el.src = data.imgUrl;
  });
}

/* ───────────────────────────────────────────────────────────────────
   6. DÉMARRAGE / PARTIE SUIVANTE
   ─────────────────────────────────────────────────────────────────── */

async function startGame() {
  if (loading) return;
  loading = true;
  showState('loading');
  setLoad('🎲 Tirage des pages…', 20);

  try {
    // Page A : tirage depuis un tome aléatoire
    let a = await fetchRandomPage();
    usedImages.add(a.imgUrl);

    // Page B : tirage dans le MÊME tome qu'A (mais page différente)
    setLoad('🎲 Tirage de la deuxième page…', 50);
    let b = await fetchRandomPageInVolume(a.num, a.pageIndex);

    imgA = a; imgB = b;

    // Charge les deux images en parallèle
    setLoad('🖼 Chargement images…', 80);
    await Promise.all([loadImgEl('imgA', imgA), loadImgEl('imgB', imgB)]);

    showState('game');
  } catch(e) {
    console.error(e);
    showState('error');
  }
  loading = false;
}

// Manche suivante : B devient A, on tire une nouvelle B dans le même tome
async function nextRound() {
  if (loading) return;
  loading = true;
  showState('loading');
  setLoad('🖼 Nouvelle page…', 30);

  try {
    imgA = imgB;
    $('imgA').src = imgA.imgUrl;

    let b = await fetchRandomPageInVolume(imgA.num, imgA.pageIndex);
    imgB = b;

    setLoad('🖼 Chargement…', 70);
    await loadImgEl('imgB', imgB);

    showState('game');
  } catch(e) {
    console.error(e);
    showState('error');
  }
  loading = false;
}

/* ───────────────────────────────────────────────────────────────────
   7. RÉPONSE DU JOUEUR
   Compare les index de page : B avant A → 'before', sinon 'after'
   ─────────────────────────────────────────────────────────────────── */

function answer(choice) {
  if (loading) return;

  const correct = (choice === 'before' && imgB.pageIndex < imgA.pageIndex) ||
                  (choice === 'after'  && imgB.pageIndex > imgA.pageIndex);

  if (correct) {
    streak++;
    if (streak > best) {
      best = streak;
      localStorage.setItem('bqc_tl_v1', JSON.stringify({ best }));
    }
    updStats();
    nextRound();
  } else {
    showResult();
  }
}

/* ───────────────────────────────────────────────────────────────────
   8. ÉCRAN DE RÉSULTAT
   Affiche la série ratée + les deux images
   ─────────────────────────────────────────────────────────────────── */

function showResult() {
  $('resStreak').textContent = streak;
  $('resBest').textContent = best > 0 ? `Record : ${best}` : '';
  $('resImgA').src = imgA.imgUrl;
  $('resImgB').src = imgB.imgUrl;

  streak = 0;
  updStats();
  localStorage.setItem('bqc_tl_v1', JSON.stringify({ best }));

  showState('result');
}

/* ───────────────────────────────────────────────────────────────────
   9. RELANCE / UTILITAIRES
   ─────────────────────────────────────────────────────────────────── */

function restart() {
  usedImages = new Set();
  imgA = null; imgB = null;
  streak = 0;
  updStats();
  startGame();
}

function updStats() {
  $('sStreak').textContent = streak;
  $('sBest').textContent   = best;
}

/* ───────────────────────────────────────────────────────────────────
   10. GESTION DES ÉTATS DE L'INTERFACE
   ─────────────────────────────────────────────────────────────────── */

function showState(state) {
  ['loadBox','gameBox','resultBox','errorBox'].forEach(id => {
    const el = $(id);
    if (el) el.style.display = 'none';
  });
  const map = { loading: 'loadBox', game: 'gameBox', result: 'resultBox', error: 'errorBox' };
  const target = $(map[state]);
  if (target) target.style.display = 'flex';
}