/* ══════════════════════════════════════════════════════
   PIXEL GUESS — GAME LOGIC
   ══════════════════════════════════════════════════════ */
const $ = id => document.getElementById(id);

const LEVELS = [4, 6, 8, 10, 13, 16, 20, 25, 32, 45, 64, 120];

const CROPS = [
  [0,    0,    1,    0.70],[0,    0.05, 1,    0.70],[0,    0.10, 1,    0.70],
  [0,    0.15, 1,    0.70],[0,    0.20, 1,    0.70],[0,    0.25, 1,    0.70],
  [0,    0,    1,    0.55],[0,    0.10, 1,    0.55],[0.05, 0,    0.90, 0.80],
  [0.10, 0,    0.80, 0.80],[0,    0,    0.85, 0.85],[0.15, 0,    0.85, 0.85],
  [0.05, 0.05, 0.90, 0.65],[0,    0,    0.75, 1   ],[0.25, 0,    0.75, 1   ],
];

let characters = [], allNames = [];
let used       = new Set();
let current, img, currentCrop;
let level = 0, streak = 0, best = 0, loading = false;
let sessionGuesses = [];
let aSel = -1;  // selected index for autocomplete

const canvas = $("canvas");
const ctx    = canvas.getContext("2d");
const sleep  = ms => new Promise(r => setTimeout(r, ms));

/* ── INIT ──────────────────────────────────────────────────── */
window.addEventListener("load", async () => {
  const s = JSON.parse(localStorage.getItem("pixel_bleach") || "null");
  if (s) best = s.best || 0;
  await loadCharacters();
  updateStats();
  startGame();
});

/* ── LOAD CHARACTERS ───────────────────────────────────────── */
async function loadCharacters() {
  const dataNames = new Set(CHARS.map(c => normalize(c.n)));
  const imageMap  = {};

  setLoadMsg("Source 1/3 — Jikan Bleach…");
  await fetchJikan(269, dataNames, imageMap);

  setLoadMsg("Source 2/3 — Jikan TYBW…");
  await fetchJikan(41467, dataNames, imageMap);

  setLoadMsg("Source 3/3 — AniList…");
  await fetchAniList([205, 146065], dataNames, imageMap);

  characters = CHARS
    .filter(c => imageMap[normalize(c.n)]?.size > 0)
    .map(c => ({ name: c.n, images: [...imageMap[normalize(c.n)]] }));

  allNames = CHARS.map(c => c.n);

  if (!characters.length) setLoadMsg("Aucune image trouvée. Recharge la page.");
}

function setLoadMsg(msg) { $("loadMsg").textContent = msg; }

async function fetchJikan(animeId, dataNames, imageMap) {
  try {
    const res  = await fetch(`https://api.jikan.moe/v4/anime/${animeId}/characters`);
    const json = await res.json();
    (json.data || []).forEach(e => {
      if (!e.character?.images?.jpg?.image_url) return;
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
        await sleep(250);
      } catch(e) {
        console.warn("AniList", mediaId, "page", page, e);
        break;
      }
    }
  }
}

/* ── AUTOCOMPLETE (identique à guesser.js) ─────────────────── */
function onIn() {
  const v = $("guessInput").value.toLowerCase().trim();
  const l = $("acl");
  l.innerHTML = "";
  aSel = -1;
  if (!v) return;
  
  const done = new Set(sessionGuesses.map(g => normalize(g.name)));
  const matches = allNames.filter(x => x.toLowerCase().includes(v) && !done.has(normalize(x))).slice(0, 8);
  
  matches.forEach(x => {
    const i = document.createElement("div");
    i.className = "aci";
    // trouver la race du personnage pour le badge
    const char = CHARS.find(c => c.n === x);
    const race = char ? char.r : "?";
    i.innerHTML = x + '<span class="acb">' + race + '</span>';
    i.onclick = () => {
      $("guessInput").value = x;
      l.innerHTML = "";
      submit();
    };
    l.appendChild(i);
  });
}

function onKD(e) {
  const l = $("acl");
  const items = l.querySelectorAll(".aci");
  if (!items.length) return;
  
  if (e.key === "ArrowDown") {
    e.preventDefault();
    aSel = Math.min(aSel + 1, items.length - 1);
    items.forEach((x, i) => x.classList.toggle("sel", i === aSel));
    if (items[aSel]) {
      $("guessInput").value = items[aSel].firstChild.textContent.trim();
      items[aSel].scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
  } else if (e.key === "ArrowUp") {
    e.preventDefault();
    aSel = Math.max(aSel - 1, -1);
    items.forEach((x, i) => x.classList.toggle("sel", i === aSel));
    if (aSel >= 0 && items[aSel]) {
      $("guessInput").value = items[aSel].firstChild.textContent.trim();
      items[aSel].scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
  } else if (e.key === "Enter") {
    e.preventDefault();
    l.innerHTML = "";
    submit();
  } else if (e.key === "Escape") {
    l.innerHTML = "";
  }
}

document.addEventListener("click", e => {
  if (!e.target.closest(".acw")) $("acl").innerHTML = "";
});

/* ── GAME LIFECYCLE ────────────────────────────────────────── */
function startGame() {
  loading = true;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  canvas.style.opacity = "0";
  sessionGuesses = [];
  renderGuessList();
  updateAttempts();
  showState("load");

  if (!characters.length) { setLoadMsg("Aucun personnage disponible."); return; }

  const pool = characters.filter(c => !used.has(c.name));
  if (!pool.length) used.clear();

  current     = pool[Math.floor(Math.random() * pool.length)];
  currentCrop = CROPS[Math.floor(Math.random() * CROPS.length)];
  used.add(current.name);
  level = 0;

  $("attemptsMax").textContent = LEVELS.length;

  const url = current.images[Math.floor(Math.random() * current.images.length)];
  tryLoad(url, current.images);
}

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

function draw() {
  const size = LEVELS[level];
  const [cx, cy, cw, ch] = currentCrop;

  const srcX = Math.floor(cx * img.naturalWidth);
  const srcY = Math.floor(cy * img.naturalHeight);
  const srcW = Math.floor(cw * img.naturalWidth);
  const srcH = Math.floor(ch * img.naturalHeight);

  const off = document.createElement("canvas");
  off.width = off.height = size;
  const octx = off.getContext("2d");
  octx.imageSmoothingEnabled = false;
  octx.drawImage(img, srcX, srcY, srcW, srcH, 0, 0, size, size);

  ctx.imageSmoothingEnabled = false;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.drawImage(off, 0, 0, size, size, 0, 0, canvas.width, canvas.height);

  $("sLevel").textContent = `${size}×${size}`;
}

/* ── INPUT & SUBMIT ────────────────────────────────────────── */
function submit() {
  if (loading) return;
  $("acl").innerHTML = "";
  const raw = $("guessInput").value.trim();
  if (!raw) return;

  const val = normalize(raw);
  $("guessInput").value = "";

  if (sessionGuesses.some(g => normalize(g.name) === val)) {
    flashInput("Déjà proposé !");
    return;
  }

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

function flashInput(msg) {
  const input = $("guessInput");
  const prev  = input.placeholder;
  input.placeholder = msg;
  input.style.borderColor = "rgba(224,85,85,.6)";
  setTimeout(() => { input.placeholder = prev; input.style.borderColor = ""; }, 1400);
}

function win() {
  streak++;
  if (streak > best) best = streak;
  save(); updateStats();
  setTimeout(() => showResult("✅ Bien joué !"), 250);
}

function wrong() {
  level++;
  updateAttempts();
  if (level >= LEVELS.length) return lose();
  draw();
  updateHints();
}

function lose() {
  streak = 0; save(); updateStats();
  setTimeout(() => showResult("💀 Perdu !"), 250);
}

function showResult(titre) {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  canvas.style.opacity = "0";
  $("resTitle").textContent  = titre;
  $("resName").textContent   = current.name;
  $("resultImg").src         = img.src;
  const wrongs = sessionGuesses.filter(g => !g.correct).length;
  $("resGuessesInfo").textContent = wrongs === 0
    ? "Trouvé du premier coup !"
    : `${wrongs} mauvaise${wrongs > 1 ? "s" : ""} proposition${wrongs > 1 ? "s" : ""}`;
  showState("result");
}

/* ── RENDER GUESS LIST ─────────────────────────────────────── */
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

function updateAttempts() { $("attemptsCount").textContent = sessionGuesses.length; }

/* ── HINTS ─────────────────────────────────────────────────── */
function updateHints() {
  const parts = current.name.split(" ");
  if (level === 2) $("hintBox").textContent = "Initiale : " + current.name[0];
  if (level === 5) $("hintBox").textContent = "Prénom : " + parts[0];
  if (level === 8) $("hintBox").textContent = "Prénom : " + parts[0] + " | Nom : " + (parts[1] || "?");
}

/* ── UTILS ─────────────────────────────────────────────────── */
function normalize(s) {
  return s.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[^a-z0-9]/g, "");
}
function isClose(a, b)  { return a === b || b.includes(a) || a.includes(b); }
function escapeHtml(s)  { return s.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;"); }
function save()         { localStorage.setItem("pixel_bleach", JSON.stringify({ best })); }
function updateStats()  { $("sStreak").textContent = streak; $("sBest").textContent = best; }
function restart()      { used.clear(); streak = 0; updateStats(); startGame(); }

function showState(s) {
  $("loadBox").style.display   = s === "load"   ? "flex"  : "none";
  $("gameBox").style.display   = s === "game"   ? "flex"  : "none";
  $("resultBox").style.display = s === "result" ? "flex"  : "none";
}
