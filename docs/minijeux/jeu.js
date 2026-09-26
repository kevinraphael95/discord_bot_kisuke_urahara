/* ═══════════════════════════════════════════════════════════════════
   PIXEL GUESSER — Devine le personnage pixelisé
   ───────────────────────────────────────────────────────────────────
   But du jeu :
     Une image de perso est pixelisée puis affichée.
     À chaque mauvaise réponse, la résolution augmente (moins de pixels).
     Le joueur a 12 tentatives pour deviner le perso.

   Dépendances :
     - ../js/data.js   (variable globale CHARS)
     - minijeux.css    (styles du canvas, input, autocomplete)

   API externes :
     - Jikan (api.jikan.moe) → récupère les images officielles
     - AniList (graphql.anilist.co) → fallback

   Sections :
     1. CONSTANTES & CONFIG
     2. ÉTAT GLOBAL
     3. INITIALISATION
     4. CHARGEMENT DES PERSOS (Jikan + AniList)
     5. AUTOCOMPLÉTION
     6. DÉMARRAGE D'UNE PARTIE
     7. PRÉCHARGEMENT D'IMAGE
     8. RENDU DU CANVAS (pixelisation)
     9. SOUMISSION D'UNE RÉPONSE
    10. ÉCRAN DE RÉSULTAT
    11. LISTE DES PROPOSITIONS
    12. INDICES
    13. UTILITAIRES
    14. GESTION DES ÉTATS DE L'INTERFACE
   ═══════════════════════════════════════════════════════════════════ */

/* ───────────────────────────────────────────────────────────────────
   1. CONSTANTES & CONFIG
   ─────────────────────────────────────────────────────────────────── */

const $ = id => document.getElementById(id);

// Résolutions successives (en pixels). Plus le chiffre est petit, plus
// l'image est pixelisée. On commence flou et on augmente.
const LEVELS = [4, 6, 8, 10, 13, 16, 20, 25, 32, 45, 64, 120];

// Cadrages appliqués à l'image : [x, y, w, h] en % de l'image source.
// Ça permet de zoomer sur le visage du perso plutôt que tout le corps.
const CROPS = [
  [0,    0,    1,    0.70], [0,    0.05, 1,    0.70], [0,    0.10, 1,    0.70],
  [0,    0.15, 1,    0.70], [0,    0.20, 1,    0.70], [0,    0.25, 1,    0.70],
  [0,    0,    1,    0.55], [0,    0.10, 1,    0.55], [0.05, 0,    0.90, 0.80],
  [0.10, 0,    0.80, 0.80], [0,    0,    0.85, 0.85], [0.15, 0,    0.85, 0.85],
  [0.05, 0.05, 0.90, 0.65], [0,    0,    0.75, 1   ], [0.25, 0,    0.75, 1   ],
];

/* ───────────────────────────────────────────────────────────────────
   2. ÉTAT GLOBAL
   ─────────────────────────────────────────────────────────────────── */

let characters = [];          // Persos avec images disponibles
let allNames   = [];          // Tous les noms (pour l'autocomplete)
let used       = new Set();   // Persos déjà utilisés (pour ne pas répéter)
let current, img, currentCrop;
let level = 0;                // Niveau actuel (index dans LEVELS)
let streak = 0;               // Série actuelle
let best = 0;                 // Meilleure série
let loading = false;          // Évite de soumettre pendant un chargement
let acIndex = -1;             // Index sélectionné dans l'autocomplete
let sessionGuesses = [];      // Propositions de la partie en cours

const canvas = $("canvas");
const ctx    = canvas.getContext("2d");
const sleep  = ms => new Promise(r => setTimeout(r, ms));

/* ───────────────────────────────────────────────────────────────────
   3. INITIALISATION
   ─────────────────────────────────────────────────────────────────── */

window.addEventListener("load", async () => {
  // Charge le record depuis localStorage
  const s = JSON.parse(localStorage.getItem("pixel_bleach") || "null");
  if (s) best = s.best || 0;

  await loadCharacters();      // Récupère les images via API
  initAutocomplete();          // Prépare la barre de suggestions
  updateStats();
  startGame();

  // Touche Entrée pour valider
  $("guessInput").addEventListener("keypress", e => {
    if (e.key === "Enter") submit();
  });
});

/* ───────────────────────────────────────────────────────────────────
   4. CHARGEMENT DES PERSOS (Jikan + AniList)
   Récupère les URLs d'images officielles et les associe aux persos
   de data.js via leur nom normalisé.
   ─────────────────────────────────────────────────────────────────── */

async function loadCharacters() {
  const dataNames = new Set(CHARS.map(c => normalize(c.n)));
  const imageMap  = {};        // { nomNormalisé: Set(urls) }

  setLoadMsg("Source 1/3 — Jikan Bleach…");
  await fetchJikan(269, dataNames, imageMap);       // Anime Bleach

  setLoadMsg("Source 2/3 — Jikan TYBW…");
  await fetchJikan(41467, dataNames, imageMap);     // Thousand-Year Blood War

  setLoadMsg("Source 3/3 — AniList…");
  await fetchAniList([205, 146065], dataNames, imageMap);

  // Ne garde que les persos avec au moins 1 image
  characters = CHARS
    .filter(c => imageMap[normalize(c.n)]?.size > 0)
    .map(c => ({ name: c.n, images: [...imageMap[normalize(c.n)]] }));

  allNames = CHARS.map(c => c.n);

  if (!characters.length) setLoadMsg("Aucune image trouvée. Recharge la page.");
}

function setLoadMsg(msg) { $("loadMsg").textContent = msg; }

// Récupère les images via Jikan pour un anime donné
async function fetchJikan(animeId, dataNames, imageMap) {
  try {
    const res  = await fetch(`https://api.jikan.moe/v4/anime/${animeId}/characters`);
    const json = await res.json();
    (json.data || []).forEach(e => {
      if (!e.character?.images?.jpg?.image_url) return;

      // Jikan renvoie "Nom, Prénom" → on remet dans l'ordre "Prénom Nom"
      const raw   = e.character.name;
      const parts = raw.split(", ");
      const name  = parts.length === 2
        ? `${parts[1].trim()} ${parts[0].trim()}`
        : raw.trim();

      const key = normalize(name);
      if (!dataNames.has(key)) return;
      if (!imageMap[key]) imageMap[key] = new Set();
      imageMap[key].add(e.character.images.jpg.image_url);
      if (e.character.images.webp?.image_url)
        imageMap[key].add(e.character.images.webp.image_url);
    });
  } catch(e) { console.warn("Jikan", animeId, e); }
}

// Récupère les images via l'API GraphQL d'AniList (fallback)
async function fetchAniList(mediaIds, dataNames, imageMap) {
  for (const mediaId of mediaIds) {
    let page = 1, hasNext = true;
    while (hasNext && page <= 8) {
      try {
        const query = `query($p:Int){Media(id:${mediaId},type:ANIME){characters(page:$p,perPage:25,sort:ROLE){pageInfo{hasNextPage}nodes{name{full}image{large medium}}}}}`;
        const res  = await fetch("https://graphql.anilist.co", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query, variables: { p: page } })
        });
        const json  = await res.json();
        const chars = json?.data?.Media?.characters;
        if (!chars) break;
        hasNext = chars.pageInfo.hasNextPage;
        chars.nodes.forEach(node => {
          const key = normalize(node.name.full);
          if (!dataNames.has(key)) return;
          if (!imageMap[key]) imageMap[key] = new Set();
          if (node.image.large)  imageMap[key].add(node.image.large);
          if (node.image.medium) imageMap[key].add(node.image.medium);
        });
        page++;
        await sleep(250);     // Respecte le rate-limit
      } catch(e) {
        console.warn("AniList", mediaId, "page", page, e);
        break;
      }
    }
  }
}

/* ───────────────────────────────────────────────────────────────────
   5. AUTOCOMPLÉTION
   Suggestions filtrées par saisie + navigation clavier (↑↓ Entrée Esc)
   ─────────────────────────────────────────────────────────────────── */

function initAutocomplete() {
  const input = $("guessInput");
  const box = $("autocompleteBox");

  // Filtre en direct à chaque frappe
  input.addEventListener("input", () => {
    const val = input.value.toLowerCase().trim();
    box.innerHTML = "";
    acIndex = -1;
    if (!val) { box.style.display = "none"; return; }

    const guessed = new Set(sessionGuesses.map(g => normalize(g.name)));
    const matches = allNames
      .filter(name => name.toLowerCase().includes(val) && !guessed.has(normalize(name)))
      .slice(0, 8);

    matches.forEach(name => {
      const div = document.createElement("div");
      div.className = "ac-item";
      div.textContent = name;
      div.onclick = () => {
        input.value = name;
        box.style.display = "none";
        submit();
      };
      box.appendChild(div);
    });

    box.style.display = matches.length ? "block" : "none";
  });

  // Navigation clavier
  input.addEventListener("keydown", (e) => {
    const items = [...box.querySelectorAll(".ac-item")];
    if (!items.length) return;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      acIndex = Math.min(acIndex + 1, items.length - 1);
      updateActiveItem(items);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      acIndex = Math.max(acIndex - 1, -1);
      updateActiveItem(items);
    } else if (e.key === "Enter" && acIndex >= 0 && items[acIndex]) {
      e.preventDefault();
      input.value = items[acIndex].textContent;
      box.style.display = "none";
      submit();
    } else if (e.key === "Escape") {
      box.style.display = "none";
    }
  });

  // Ferme le menu si on clique ailleurs
  document.addEventListener("click", (e) => {
    if (!box.contains(e.target) && e.target !== input) {
      box.style.display = "none";
    }
  });
}

function updateActiveItem(items) {
  items.forEach((item, i) => {
    item.classList.toggle("active", i === acIndex);
  });
  if (acIndex >= 0 && items[acIndex]) {
    items[acIndex].scrollIntoView({ block: "nearest", behavior: "smooth" });
  }
}

/* ───────────────────────────────────────────────────────────────────
   6. DÉMARRAGE D'UNE PARTIE
   Choisit un perso aléatoire (non déjà joué) + un crop, puis charge l'image
   ─────────────────────────────────────────────────────────────────── */

function startGame() {
  loading = true;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  canvas.style.opacity = "0";
  sessionGuesses = [];
  renderGuessList();
  updateAttempts();
  showState("load");

  if (!characters.length) {
    setLoadMsg("Aucun personnage disponible.");
    return;
  }

  // Pool = persos non encore utilisés
  const pool = characters.filter(c => !used.has(c.name));
  if (!pool.length) used.clear();

  current     = pool[Math.floor(Math.random() * pool.length)];
  currentCrop = CROPS[Math.floor(Math.random() * CROPS.length)];
  used.add(current.name);
  level = 0;

  $("attemptsMax").textContent = LEVELS.length;

  // Choisit une image au hasard parmi celles dispo
  const url = current.images[Math.floor(Math.random() * current.images.length)];
  tryLoad(url, current.images);
}

/* ───────────────────────────────────────────────────────────────────
   7. PRÉCHARGEMENT D'IMAGE
   Essaie l'URL donnée, si erreur on essaie une autre
   ─────────────────────────────────────────────────────────────────── */

function tryLoad(url, remaining) {
  preloadImage(url)
    .then(im => {
      img = im;
      draw();
      canvas.style.opacity = "1";
      $("hintBox").textContent = "";
      showState("game");
      $("guessInput").focus();
      loading = false;
    })
    .catch(() => {
      // Essaie une autre image, sinon passe au perso suivant
      const others = remaining.filter(u => u !== url);
      if (others.length) {
        const next = others[Math.floor(Math.random() * others.length)];
        tryLoad(next, others.filter(u => u !== next));
      } else {
        used.add(current.name);
        startGame();
      }
    });
}

function preloadImage(src) {
  return new Promise((resolve, reject) => {
    const im = new Image();
    im.crossOrigin = "Anonymous";
    im.onload  = () => resolve(im);
    im.onerror = reject;
    im.src = src;
  });
}

/* ───────────────────────────────────────────────────────────────────
   8. RENDU DU CANVAS (pixelisation)
   Dessine l'image dans un petit canvas offscreen puis l'agrandit
   sur le canvas principal, ce qui pixelise.
   ─────────────────────────────────────────────────────────────────── */

function draw() {
  const size = LEVELS[level];
  const [cx, cy, cw, ch] = currentCrop;

  // Coordonnées source (en pixels réels de l'image d'origine)
  const srcX = Math.floor(cx * img.naturalWidth);
  const srcY = Math.floor(cy * img.naturalHeight);
  const srcW = Math.floor(cw * img.naturalWidth);
  const srcH = Math.floor(ch * img.naturalHeight);

  // Passe 1 : dessine dans un canvas minuscule (size x size)
  const off = document.createElement("canvas");
  off.width = off.height = size;
  const octx = off.getContext("2d");
  octx.imageSmoothingEnabled = false;
  octx.drawImage(img, srcX, srcY, srcW, srcH, 0, 0, size, size);

  // Passe 2 : étire sur le canvas visible (donne l'effet pixelisé)
  ctx.imageSmoothingEnabled = false;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.drawImage(off, 0, 0, size, size, 0, 0, canvas.width, canvas.height);

  $("sLevel").textContent = `${size}×${size}`;
}

/* ───────────────────────────────────────────────────────────────────
   9. SOUMISSION D'UNE RÉPONSE
   Compare la réponse au perso cible, met à jour la liste et l'état
   ─────────────────────────────────────────────────────────────────── */

function submit() {
  if (loading) return;
  $("autocompleteBox").style.display = "none";
  const raw = $("guessInput").value.trim();
  if (!raw) return;

  const val = normalize(raw);
  $("guessInput").value = "";

  // Doublon ?
  if (sessionGuesses.some(g => normalize(g.name) === val)) {
    flashInput("Déjà proposé !");
    return;
  }

  // Bonne réponse ?
  if (isClose(val, normalize(current.name))) {
    sessionGuesses.push({ name: raw, correct: true });
    renderGuessList();
    win();
  } else {
    sessionGuesses.push({ name: raw, correct: false });
    renderGuessList();
    wrong();
  }
}

// Petit flash rouge sur l'input quand il faut signaler une erreur
function flashInput(msg) {
  const input = $("guessInput");
  const prev  = input.placeholder;
  input.placeholder = msg;
  input.style.borderColor = "rgba(224,85,85,.6)";
  setTimeout(() => {
    input.placeholder = prev;
    input.style.borderColor = "";
  }, 1400);
}

// Bonne réponse : série+, record si battu, résultat après 250ms
function win() {
  streak++;
  if (streak > best) best = streak;
  save(); updateStats();
  setTimeout(() => showResult("✅ Bien joué !"), 250);
}

// Mauvaise réponse : on monte d'un niveau (donc on dé-pixelise un peu)
function wrong() {
  level++;
  updateAttempts();
  if (level >= LEVELS.length) return lose();
  draw();
  updateHints();
}

// Plus d'essais : série remise à 0, résultat après 250ms
function lose() {
  streak = 0; save(); updateStats();
  setTimeout(() => showResult("💀 Perdu !"), 250);
}

/* ───────────────────────────────────────────────────────────────────
   10. ÉCRAN DE RÉSULTAT
   Affiche le perso (image nette), le pseudo-résultat et le nombre d'essais
   ─────────────────────────────────────────────────────────────────── */

function showResult(titre) {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  canvas.style.opacity = "0";
  $("resTitle").textContent = titre;
  $("resName").textContent  = current.name;
  $("resultImg").src        = img.src;

  const wrongs = sessionGuesses.filter(g => !g.correct).length;
  $("resGuessesInfo").textContent = wrongs === 0
    ? "Trouvé du premier coup !"
    : `${wrongs} mauvaise${wrongs > 1 ? "s" : ""} proposition${wrongs > 1 ? "s" : ""}`;

  showState("result");
}

/* ───────────────────────────────────────────────────────────────────
   11. LISTE DES PROPOSITIONS
   Affiche les essais précédents (les plus récents en haut)
   ─────────────────────────────────────────────────────────────────── */

function renderGuessList() {
  const list = $("guessList");
  list.querySelectorAll(".guess-item").forEach(el => el.remove());

  $("noGuesses").style.display = sessionGuesses.length ? "none" : "block";

  [...sessionGuesses].reverse().forEach(g => {
    const div = document.createElement("div");
    div.className = "guess-item guess-wrong";
    div.innerHTML = `<span class="guess-icon"></span><span>${escapeHtml(g.name)}</span>`;
    $("noGuesses").insertAdjacentElement("afterend", div);
  });
}

function updateAttempts() {
  $("attemptsCount").textContent = sessionGuesses.length;
}

/* ───────────────────────────────────────────────────────────────────
   12. INDICES
   Révèle progressivement le prénom, l'initiale, etc.
   ─────────────────────────────────────────────────────────────────── */

function updateHints() {
  const parts = current.name.split(" ");
  if (level === 2) $("hintBox").textContent = "Initiale : " + current.name[0];
  if (level === 5) $("hintBox").textContent = "Prénom : " + parts[0];
  if (level === 8) $("hintBox").textContent = "Prénom : " + parts[0] + " | Nom : " + (parts[1] || "?");
}

/* ───────────────────────────────────────────────────────────────────
   13. UTILITAIRES
   ─────────────────────────────────────────────────────────────────── */

// Normalise une chaîne pour comparer : minuscules + supprime accents et ponctuation
function normalize(s) {
  return s.toLowerCase().normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]/g, "");
}

// Comparaison souple : égal, ou l'un contient l'autre
function isClose(a, b) {
  return a === b || b.includes(a) || a.includes(b);
}

// Échappe le HTML pour éviter l'injection
function escapeHtml(s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

// Sauvegarde le record en localStorage
function save() {
  localStorage.setItem("pixel_bleach", JSON.stringify({ best }));
}

function updateStats() {
  $("sStreak").textContent = streak;
  $("sBest").textContent   = best;
}

// Réinitialise et relance une nouvelle partie
function restart() {
  used.clear();
  streak = 0;
  updateStats();
  startGame();
}

/* ───────────────────────────────────────────────────────────────────
   14. GESTION DES ÉTATS DE L'INTERFACE
   Affiche/cache les 3 blocs : chargement / jeu / résultat
   ─────────────────────────────────────────────────────────────────── */

function showState(s) {
  $("loadBox").style.display   = s === "load"   ? "flex" : "none";
  $("gameBox").style.display   = s === "game"   ? "flex" : "none";
  $("resultBox").style.display = s === "result" ? "flex" : "none";
}