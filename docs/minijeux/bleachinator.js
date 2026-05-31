/* ═══════════════════════════════════════════════════════
   BLEACHINATOR — bleachinator.js
   Partition optimale 50/50 par propriété
   ═══════════════════════════════════════════════════════ */

let pool       = [];
let asked      = 0;
let botStreak  = 0;
let totalGames = 0;
let currentQ   = null;
let askedKeys  = new Set();

const MAX_Q = 7;

/* ── PROPRIÉTÉS INTERROGEABLES ───────────────────────── */
const FIELDS = [
  { key: "sx",  label: v => `Ton personnage est-il <strong>${v === "M" ? "masculin" : "féminin"}</strong> ?` },
  { key: "r",   label: v => `Ton personnage est-il de race <strong>${v}</strong> ?` },
  { key: "af",  label: v => `Ton personnage appartient-il à <strong>${v}</strong> ?` },
  { key: "st",  label: v => `Le statut de ton personnage est-il <strong>${v}</strong> ?` },
  { key: "hc",  label: v => v === "Chauve" ? "Ton personnage est-il <strong>chauve</strong> ?" : `Ton personnage a-t-il les <strong>cheveux ${v.toLowerCase()}</strong> ?` },
  { key: "arc", label: v => `Ton personnage est-il introduit dans <strong>${v}</strong> ?` },
];

const NUMERIC_FIELDS = [
  { key: "d", label_gte: v => `Ton personnage a-t-il une <strong>dangerosité ≥ ${v}</strong> ?` },
  { key: "w", label_gte: v => `Ton personnage a-t-il remporté <strong>≥ ${v} combat${v>1?"s":""}</strong> ?` },
];

/* ── ENTROPIE ────────────────────────────────────────── */
function entropy(yes, total) {
  if (yes === 0 || yes === total) return 0;
  const p = yes / total, q = 1 - p;
  return -(p * Math.log2(p) + q * Math.log2(q));
}

/* ── MEILLEURE PARTITION PAR CHAMP ──────────────────── */
// Pour un champ donné, trouve le sous-ensemble de valeurs
// qui partitionne le pool le plus proche de 50/50
function bestPartitionForField(field) {
  const n = pool.length;
  // Grouper les persos par valeur
  const groups = {};
  for (const c of pool) {
    const v = c[field.key];
    if (!groups[v]) groups[v] = [];
    groups[v].push(c);
  }
  const vals = Object.keys(groups);
  if (vals.length < 2) return null;

  // Chercher le sous-ensemble de valeurs dont le total est le plus proche de n/2
  // Pour éviter 2^n on utilise une approche greedy : trier par taille et remplir
  const target = n / 2;
  const sorted = vals.slice().sort((a, b) => groups[a].length - groups[b].length);

  let bestSubset = null, bestDist = Infinity;

  // Tester toutes les combinaisons (n de valeurs distinct est petit ~2-9 max)
  const total = vals.length;
  for (let mask = 1; mask < (1 << total) - 1; mask++) {
    let count = 0;
    const subset = [];
    for (let i = 0; i < total; i++) {
      if (mask & (1 << i)) { count += groups[vals[i]].length; subset.push(vals[i]); }
    }
    const dist = Math.abs(count - target);
    if (dist < bestDist) { bestDist = dist; bestSubset = { subset, count }; }
  }

  if (!bestSubset) return null;

  const { subset, count } = bestSubset;
  const ent = entropy(count, n);
  if (ent === 0) return null;

  // Label : si un seul élément dans le subset, label précis ; sinon liste
  let label;
  if (subset.length === 1) {
    label = field.label(subset[0]);
  } else if (total - subset.length === 1) {
    // Complément = 1 valeur → poser la question sur le complément (plus court)
    const complement = vals.find(v => !subset.includes(v));
    label = field.label(complement);
    // Inverser : oui = complément
    return {
      key: `${field.key}__NOT__${complement}`,
      label: field.label(complement),
      entropy: ent,
      getValue: c => !subset.includes(c[field.key]) ? "oui" : "non",
      match: "oui",
    };
  } else {
    const names = subset.join(", ");
    label = `Ton personnage fait-il partie de ce groupe : <strong>${names}</strong> ?`;
  }

  return {
    key: `${field.key}__${subset.sort().join("|")}`,
    label,
    entropy: ent,
    getValue: c => subset.includes(c[field.key]) ? "oui" : "non",
    match: "oui",
  };
}

/* ── MEILLEURE QUESTION NUMÉRIQUE ────────────────────── */
function bestNumericQuestion(nf) {
  const vals = [...new Set(pool.map(c => c[nf.key]))].sort((a, b) => a - b);
  const n = pool.length;
  let best = null, bestEnt = -1;
  for (const v of vals) {
    const yes = pool.filter(c => c[nf.key] >= v).length;
    if (yes === 0 || yes === n) continue;
    const e = entropy(yes, n);
    if (e > bestEnt) { bestEnt = e; best = { v, yes, e }; }
  }
  if (!best) return null;
  return {
    key: `${nf.key}_gte_${best.v}`,
    label: nf.label_gte(best.v),
    entropy: best.e,
    getValue: c => c[nf.key] >= best.v ? "oui" : "non",
    match: "oui",
  };
}

/* ── SÉLECTION DE LA MEILLEURE QUESTION ──────────────── */
function bestQuestion() {
  const candidates = [];

  for (const field of FIELDS) {
    const q = bestPartitionForField(field);
    if (q && !askedKeys.has(q.key)) candidates.push(q);
  }
  for (const nf of NUMERIC_FIELDS) {
    const q = bestNumericQuestion(nf);
    if (q && !askedKeys.has(q.key)) candidates.push(q);
  }

  if (!candidates.length) return null;

  // Trier par entropie décroissante
  candidates.sort((a, b) => b.entropy - a.entropy);

  // Variation légère : choisir aléatoirement parmi le top à entropie quasi-égale
  const TOP = 0.04;
  const top = candidates.filter(q => candidates[0].entropy - q.entropy <= TOP);
  return top[Math.floor(Math.random() * top.length)];
}

/* ── INIT ────────────────────────────────────────────── */
function startGame() {
  pool      = [...CHARS];
  asked     = 0;
  askedKeys = new Set();
  currentQ  = null;

  document.getElementById("introBox").style.display = "none";
  document.getElementById("winBox").style.display   = "none";
  document.getElementById("loseBox").style.display  = "none";
  document.getElementById("gameBox").style.display  = "block";

  renderDots();
  nextQuestion();
}

function restart() {
  document.getElementById("winBox").style.display  = "none";
  document.getElementById("loseBox").style.display = "none";
  startGame();
}

/* ── DOTS ────────────────────────────────────────────── */
function renderDots() {
  const el = document.getElementById("biDots");
  el.innerHTML = "";
  for (let i = 0; i < MAX_Q; i++) {
    const d = document.createElement("div");
    d.className = "bi-dot" + (i < asked ? " asked" : i === asked ? " active" : "");
    el.appendChild(d);
  }
  document.getElementById("qNum").textContent = Math.min(asked + 1, MAX_Q);
}

/* ── QUESTION SUIVANTE ───────────────────────────────── */
function nextQuestion() {
  if (pool.length <= 2 || asked >= MAX_Q - 1) {
    const top = pool.reduce((a, b) => b.w > a.w ? b : a, pool[0]);
    return guessChar(top);
  }

  const q = bestQuestion();
  if (!q) {
    const top = pool.reduce((a, b) => b.w > a.w ? b : a, pool[0]);
    return guessChar(top);
  }

  currentQ = q;
  showQuestion(q.label);
}

/* ── AFFICHAGE QUESTION ──────────────────────────────── */
function showQuestion(label) {
  document.getElementById("biEmoji").textContent  = "🤔";
  document.getElementById("biQuestion").innerHTML = label;
  document.getElementById("biHint").textContent   =
    `${pool.length} personnage${pool.length > 1 ? "s" : ""} possible${pool.length > 1 ? "s" : ""}`;

  document.getElementById("biBtns").innerHTML = `
    <button class="bi-btn yes"   onclick="answer('oui')">✅ Oui</button>
    <button class="bi-btn no"    onclick="answer('non')">❌ Non</button>
    <button class="bi-btn maybe" onclick="answer('sais_pas')">🤷 Je sais pas</button>
  `;
}

/* ── RÉPONSE JOUEUR ──────────────────────────────────── */
function answer(rep) {
  if (rep === "sais_pas") {
    const skippedKey = currentQ.key;
    askedKeys.add(skippedKey);
    const q = bestQuestion();
    askedKeys.delete(skippedKey);
    if (!q) {
      const top = pool.reduce((a, b) => b.w > a.w ? b : a, pool[0]);
      return guessChar(top);
    }
    currentQ = q;
    showQuestion(q.label);
    return;
  }

  const q = currentQ;
  pool = pool.filter(c => {
    const val = q.getValue(c);
    return rep === "oui" ? val === q.match : val !== q.match;
  });

  askedKeys.add(q.key);
  asked++;
  renderDots();

  if (pool.length === 0) { showLose(); return; }

  nextQuestion();
}

/* ── DEVINETTE ───────────────────────────────────────── */
function guessChar(char) {
  document.getElementById("biEmoji").textContent  = "💡";
  document.getElementById("biQuestion").innerHTML = `C'est… <strong>${char.n}</strong> ?`;
  document.getElementById("biHint").textContent   = "";

  document.getElementById("biBtns").innerHTML = `
    <button class="bi-btn yes" onclick="guessResult(true,  '${escQ(char.n)}')">✅ Oui !</button>
    <button class="bi-btn no"  onclick="guessResult(false, '${escQ(char.n)}')">❌ Non…</button>
  `;
}

function escQ(s) { return s.replace(/\\/g, "\\\\").replace(/'/g, "\\'"); }

/* ── RÉSULTAT DEVINETTE ──────────────────────────────── */
function guessResult(correct, name) {
  if (correct) {
    totalGames++;
    botStreak++;
    document.getElementById("winName").textContent    = name;
    document.getElementById("wQuestions").textContent = asked + 1;
    document.getElementById("wStreak").textContent    = botStreak;
    document.getElementById("wTotal").textContent     = totalGames;
    document.getElementById("gameBox").style.display  = "none";
    document.getElementById("winBox").style.display   = "block";
  } else {
    pool = pool.filter(c => c.n !== name);
    if (pool.length > 0 && asked < MAX_Q - 1) {
      nextQuestion();
    } else {
      showLose();
    }
  }
}

/* ── BOT PERD ────────────────────────────────────────── */
function showLose() {
  totalGames++;
  botStreak = 0;

  document.getElementById("gameBox").style.display = "none";
  document.getElementById("loseBox").style.display = "block";
  document.getElementById("lStreak").textContent   = botStreak;
  document.getElementById("lTotal").textContent    = totalGames;

  const sel = document.getElementById("nameSelect");
  sel.innerHTML = "";
  CHARS.slice().sort((a, b) => a.n.localeCompare(b.n)).forEach(c => {
    const opt = document.createElement("option");
    opt.value = c.n;
    opt.textContent = c.n;
    sel.appendChild(opt);
  });
}

function confirmName() {
  document.getElementById("loseBox").style.display  = "none";
  document.getElementById("introBox").style.display = "block";
}
