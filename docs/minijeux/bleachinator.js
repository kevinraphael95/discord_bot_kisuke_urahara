/* ═══════════════════════════════════════════════════════
   BLEACHINATOR — bleachinator.js
   Questions 100% dynamiques générées depuis CHARS
   ═══════════════════════════════════════════════════════ */

/* ── ÉTAT ────────────────────────────────────────────── */
let pool       = [];
let asked      = 0;
let botStreak  = 0;
let totalGames = 0;
let currentQ   = null;
let askedKeys  = new Set();

const MAX_Q = 7;

/* ── LABELS LISIBLES ─────────────────────────────────── */
const LABELS = {
  r:   { _: "Ton personnage est-il de la race <strong>{v}</strong> ?",
          "Shinigami":                "Ton personnage est-il un <strong>Shinigami</strong> ?",
          "Vizard":                   "Ton personnage est-il un <strong>Vizard</strong> ?",
          "Arrancar":                 "Ton personnage est-il un <strong>Arrancar</strong> ?",
          "Quincy":                   "Ton personnage est-il un <strong>Quincy</strong> ?",
          "Humain":                   "Ton personnage est-il un <strong>Humain</strong> (sans pouvoir spécial) ?",
          "Fullbring":                "Ton personnage est-il un <strong>Fullbring</strong> ?",
          "Hollow":                   "Ton personnage est-il un <strong>Hollow pur</strong> (pas Arrancar) ?",
          "Mod-Soul/Âme artificielle":"Ton personnage est-il une <strong>âme artificielle / Mod-Soul</strong> ?",
  },
  sx:  { "M": "Ton personnage est-il <strong>masculin</strong> ?",
          "F": "Ton personnage est-il <strong>féminin</strong> ?",
  },
  af:  { _: "Ton personnage appartient-il à <strong>{v}</strong> ?",
          "Gotei 13":     "Ton personnage appartient-il (ou a-t-il appartenu) au <strong>Gotei 13</strong> ?",
          "Wandenreich":  "Ton personnage appartient-il au <strong>Wandenreich</strong> ?",
          "Espada":       "Ton personnage est-il (ou a-t-il été) une <strong>Espada</strong> ?",
          "Karakura":     "Ton personnage vient-il de <strong>Karakura</strong> ?",
          "Division Zero":"Ton personnage fait-il partie de la <strong>Division Zéro</strong> ?",
          "Indépendant":  "Ton personnage est-il <strong>indépendant</strong> (Urahara Shop, Vizards non promus…) ?",
          "Hueco Mundo":  "Ton personnage réside-t-il à <strong>Hueco Mundo</strong> (hors Espada) ?",
          "Xcution":      "Ton personnage fait-il partie du groupe <strong>Xcution</strong> ?",
  },
  st:  { "Vivant":    "Ton personnage est-il <strong>vivant</strong> à la fin de l'histoire ?",
          "Mort":      "Ton personnage est-il <strong>mort définitivement</strong> ?",
          "Incertain": "Le statut de ton personnage est-il <strong>incertain</strong> à la fin ?",
  },
  hc:  { _: "Ton personnage a-t-il les <strong>cheveux {v}</strong> ?",
          "Chauve": "Ton personnage est-il <strong>chauve</strong> ?",
          "Noir":   "Ton personnage a-t-il les <strong>cheveux noirs</strong> ?",
          "Blond":  "Ton personnage a-t-il les <strong>cheveux blonds</strong> ?",
          "Blanc":  "Ton personnage a-t-il les <strong>cheveux blancs</strong> ?",
          "Gris":   "Ton personnage a-t-il les <strong>cheveux gris</strong> ?",
          "Brun":   "Ton personnage a-t-il les <strong>cheveux bruns</strong> ?",
          "Roux":   "Ton personnage a-t-il les <strong>cheveux roux</strong> ?",
          "Rouge":  "Ton personnage a-t-il les <strong>cheveux rouges</strong> ?",
          "Rose":   "Ton personnage a-t-il les <strong>cheveux roses</strong> ?",
          "Violet": "Ton personnage a-t-il les <strong>cheveux violets</strong> ?",
          "Vert":   "Ton personnage a-t-il les <strong>cheveux verts</strong> ?",
          "Bleu":   "Ton personnage a-t-il les <strong>cheveux bleus</strong> ?",
  },
  arc: { _: "Ton personnage est-il introduit dans l'arc <strong>{v}</strong> ?",
          "Le Shinigami Remplaçant (1)":                    "Ton personnage apparaît-il dès <strong>l'arc 1</strong> (Shinigami Remplaçant) ?",
          "Soul Society : L'Invasion (2.1)":                "Ton personnage est-il introduit dans <strong>Soul Society — L'Invasion</strong> ?",
          "Soul Society : Le Sauvetage (2.2)":              "Ton personnage est-il introduit dans <strong>Soul Society — Le Sauvetage</strong> ?",
          "Arrancar : Invasion du monde des humains (3.1)": "Ton personnage est-il introduit dans <strong>l'Invasion du monde des humains</strong> ?",
          "Arrancar : Invasion du Hueco Mundo (3.2)":       "Ton personnage est-il introduit lors de <strong>l'Invasion de Hueco Mundo</strong> ?",
          "Arrancar : Bataille de Karakura (3.3)":          "Ton personnage est-il introduit lors de la <strong>Bataille de Karakura</strong> ?",
          "Arc Fullbringers (4)":                           "Ton personnage est-il introduit dans l'<strong>arc Fullbringers</strong> ?",
          "Guerre Sanglante de Mille Ans (5)":              "Ton personnage est-il introduit dans la <strong>Guerre Sanglante de Mille Ans</strong> ?",
          "NO BREATHES FROM HELL (6)":                      "Ton personnage est-il introduit dans <strong>No Breathes from Hell</strong> ?",
  },
};

/* ── QUESTIONS NUMÉRIQUES (seuils) ───────────────────── */
// Générées dynamiquement selon les valeurs réelles du pool
const NUMERIC_FIELDS = [
  { key: "d", label_gte: v => `Ton personnage a-t-il une <strong>dangerosité ≥ ${v}</strong> ?`,
               label_lte: v => `Ton personnage a-t-il une <strong>dangerosité ≤ ${v}</strong> ?` },
  { key: "w", label_gte: v => `Ton personnage a-t-il <strong>remporté ≥ ${v} combat${v>1?"s":""}</strong> ?`,
               label_lte: v => `Ton personnage a-t-il <strong>remporté ≤ ${v} combat${v>1?"s":""}</strong> ?` },
];

/* ── GÉNÉRATION DYNAMIQUE DES QUESTIONS ──────────────── */
function generateQuestions(currentPool) {
  const questions = [];

  // Questions catégorielles : une question par valeur distincte dans le pool
  for (const field of ["r", "sx", "af", "st", "hc", "arc"]) {
    const values = [...new Set(currentPool.map(c => c[field]))];
    // Ne générer que si la valeur divise le pool (pas tout d'un côté)
    for (const val of values) {
      const key = `${field}__${val}`;
      const yes = currentPool.filter(c => c[field] === val).length;
      if (yes === 0 || yes === currentPool.length) continue;

      const labelMap = LABELS[field] || {};
      const label = labelMap[val]
        || (labelMap._ ? labelMap._.replace("{v}", val) : `Ton personnage a-t-il <strong>${field} = ${val}</strong> ?`);

      questions.push({
        key,
        label,
        getValue: c => c[field] === val ? "oui" : "non",
        match: "oui",
      });
    }
  }

  // Questions numériques : seuils dynamiques
  for (const nf of NUMERIC_FIELDS) {
    const vals = [...new Set(currentPool.map(c => c[nf.key]))].sort((a,b)=>a-b);
    // Tester chaque valeur comme seuil ≥ et ≤
    for (const v of vals) {
      // ≥ v
      const key_gte = `${nf.key}_gte_${v}`;
      const yes_gte = currentPool.filter(c => c[nf.key] >= v).length;
      if (yes_gte > 0 && yes_gte < currentPool.length) {
        questions.push({
          key: key_gte,
          label: nf.label_gte(v),
          getValue: c => c[nf.key] >= v ? "oui" : "non",
          match: "oui",
        });
      }
      // ≤ v
      const key_lte = `${nf.key}_lte_${v}`;
      const yes_lte = currentPool.filter(c => c[nf.key] <= v).length;
      if (yes_lte > 0 && yes_lte < currentPool.length) {
        questions.push({
          key: key_lte,
          label: nf.label_lte(v),
          getValue: c => c[nf.key] <= v ? "oui" : "non",
          match: "oui",
        });
      }
    }
  }

  return questions;
}

/* ── ENTROPIE DE SHANNON ─────────────────────────────── */
function entropy(yes, total) {
  if (yes === 0 || yes === total) return 0;
  const p = yes / total;
  const q = 1 - p;
  return -(p * Math.log2(p) + q * Math.log2(q));
}

/* ── MEILLEURE QUESTION ──────────────────────────────── */
function bestQuestion() {
  const candidates = generateQuestions(pool).filter(q => !askedKeys.has(q.key));
  if (!candidates.length) return null;

  // Trier par entropie décroissante
  candidates.sort((a, b) => {
    const ya = pool.filter(c => a.getValue(c) === a.match).length;
    const yb = pool.filter(c => b.getValue(c) === b.match).length;
    return entropy(yb, pool.length) - entropy(ya, pool.length);
  });

  // Parmi le top (entropie très proche du max), choisir aléatoirement
  // pour varier un peu tout en restant optimal
  const best = candidates[0];
  const bestScore = entropy(pool.filter(c => best.getValue(c) === best.match).length, pool.length);
  const TOP_BAND = 0.05; // tolérance pour la variation
  const topCandidates = candidates.filter(q => {
    const y = pool.filter(c => q.getValue(c) === q.match).length;
    return bestScore - entropy(y, pool.length) <= TOP_BAND;
  });

  return topCandidates[Math.floor(Math.random() * topCandidates.length)];
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
