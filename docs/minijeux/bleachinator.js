/* ═══════════════════════════════════════════════════════
   BLEACHINATOR — bleachinator.js
   ═══════════════════════════════════════════════════════ */

/* ── ÉTAT ────────────────────────────────────────────── */
let pool      = [];   // personnages encore possibles
let asked     = 0;    // questions réelles posées (sans "je sais pas")
let botStreak = 0;
let totalGames= 0;
let currentQ  = null; // question en cours

const MAX_Q = 5;

/* ── QUESTIONS DISPONIBLES ───────────────────────────── */
// Chaque question : { key, label, getValue(char) → string|number }
const QUESTIONS = [
  {
    key: "sx",
    label: "Ton personnage est-il <strong>masculin</strong> ?",
    getValue: c => c.sx,
    match: "M"
  },
  {
    key: "r_shinigami",
    label: "Ton personnage est-il un <strong>Shinigami</strong> (ou Vizard) ?",
    getValue: c => (c.r === "Shinigami" || c.r === "Vizard") ? "oui" : "non",
    match: "oui"
  },
  {
    key: "r_arrancar",
    label: "Ton personnage est-il un <strong>Arrancar</strong> ?",
    getValue: c => c.r === "Arrancar" ? "oui" : "non",
    match: "oui"
  },
  {
    key: "r_quincy",
    label: "Ton personnage est-il un <strong>Quincy</strong> ?",
    getValue: c => c.r === "Quincy" ? "oui" : "non",
    match: "oui"
  },
  {
    key: "r_human",
    label: "Ton personnage est-il un <strong>Humain / Fullbring</strong> ?",
    getValue: c => (c.r === "Humain" || c.r === "Fullbring") ? "oui" : "non",
    match: "oui"
  },
  {
    key: "r_hollow",
    label: "Ton personnage est-il un <strong>Hollow</strong> (pur) ?",
    getValue: c => c.r === "Hollow" ? "oui" : "non",
    match: "oui"
  },
  {
    key: "af_gotei",
    label: "Ton personnage appartient-il (ou a-t-il appartenu) au <strong>Gotei 13</strong> ?",
    getValue: c => c.af === "Gotei 13" ? "oui" : "non",
    match: "oui"
  },
  {
    key: "af_wandenreich",
    label: "Ton personnage appartient-il au <strong>Wandenreich</strong> ?",
    getValue: c => c.af === "Wandenreich" ? "oui" : "non",
    match: "oui"
  },
  {
    key: "af_espada",
    label: "Ton personnage est-il (ou a-t-il été) une <strong>Espada</strong> ?",
    getValue: c => c.af === "Espada" ? "oui" : "non",
    match: "oui"
  },
  {
    key: "af_karakura",
    label: "Ton personnage vient de <strong>Karakura</strong> ?",
    getValue: c => c.af === "Karakura" ? "oui" : "non",
    match: "oui"
  },
  {
    key: "af_zero",
    label: "Ton personnage fait partie de la <strong>Division Zéro</strong> ?",
    getValue: c => c.af === "Division Zero" ? "oui" : "non",
    match: "oui"
  },
  {
    key: "st_vivant",
    label: "Ton personnage est-il <strong>vivant</strong> à la fin de l'histoire ?",
    getValue: c => c.st === "Vivant" ? "oui" : "non",
    match: "oui"
  },
  {
    key: "st_mort",
    label: "Ton personnage est-il <strong>mort</strong> (définitivement) ?",
    getValue: c => c.st === "Mort" ? "oui" : "non",
    match: "oui"
  },
  {
    key: "d_high",
    label: "Ton personnage est-il <strong>très puissant</strong> (dangerosité ≥ 4) ?",
    getValue: c => c.d >= 4 ? "oui" : "non",
    match: "oui"
  },
  {
    key: "d_max",
    label: "Ton personnage est au <strong>sommet de la puissance</strong> (dangerosité 5) ?",
    getValue: c => c.d === 5 ? "oui" : "non",
    match: "oui"
  },
  {
    key: "hc_noir",
    label: "Ton personnage a-t-il les <strong>cheveux noirs</strong> ?",
    getValue: c => c.hc === "Noir" ? "oui" : "non",
    match: "oui"
  },
  {
    key: "hc_blanc",
    label: "Ton personnage a-t-il les <strong>cheveux blancs ou gris</strong> ?",
    getValue: c => (c.hc === "Blanc" || c.hc === "Gris" || c.hc === "Chauve") ? "oui" : "non",
    match: "oui"
  },
  {
    key: "hc_blond",
    label: "Ton personnage a-t-il les <strong>cheveux blonds</strong> ?",
    getValue: c => c.hc === "Blond" ? "oui" : "non",
    match: "oui"
  },
  {
    key: "hc_coul",
    label: "Ton personnage a-t-il une <strong>couleur de cheveux atypique</strong> (roux, violet, rose, vert, bleu…) ?",
    getValue: c => ["Roux","Violet","Rose","Vert","Bleu","Rouge"].includes(c.hc) ? "oui" : "non",
    match: "oui"
  },
  {
    key: "arc_1",
    label: "Ton personnage apparaît-il dès <strong>l'arc 1</strong> (Shinigami Remplaçant) ?",
    getValue: c => c.arc === "Le Shinigami Remplaçant (1)" ? "oui" : "non",
    match: "oui"
  },
  {
    key: "arc_ss",
    label: "Ton personnage est-il introduit dans l'arc <strong>Soul Society</strong> ?",
    getValue: c => c.arc.startsWith("Soul Society") ? "oui" : "non",
    match: "oui"
  },
  {
    key: "arc_arrancar",
    label: "Ton personnage est-il introduit dans l'arc <strong>Arrancar</strong> ?",
    getValue: c => c.arc.startsWith("Arrancar") ? "oui" : "non",
    match: "oui"
  },
  {
    key: "arc_tbtp",
    label: "Ton personnage est-il introduit dans la <strong>Guerre Sanglante de Mille Ans</strong> ?",
    getValue: c => c.arc === "Guerre Sanglante de Mille Ans (5)" ? "oui" : "non",
    match: "oui"
  },
  {
    key: "w_many",
    label: "Ton personnage a-t-il <strong>remporté de nombreux combats</strong> (victoires ≥ 5) ?",
    getValue: c => c.w >= 5 ? "oui" : "non",
    match: "oui"
  },
  {
    key: "captain",
    label: "Ton personnage est-il (ou a-t-il été) <strong>capitaine</strong> d'une division ?",
    getValue: c => {
      const caps = [
        "Shunsui Kyoraku","Soi Fon","Rose Otoribashi","Isane Kotetsu",
        "Shinji Hirako","Byakuya Kuchiki","Tetsuzaemon Iba","Lisa Yadomaru",
        "Kensei Muguruma","Toshiro Hitsugaya","Kenpachi Zaraki",
        "Mayuri Kurotsuchi","Rukia Kuchiki","Genryusai Yamamoto",
        "Retsu Unohana","Sosuke Aizen","Sajin Komamura","Kaname Tousen",
        "Gin Ichimaru","Jushiro Ukitake"
      ];
      return caps.includes(c.n) ? "oui" : "non";
    },
    match: "oui"
  },
];

/* ─ Questions déjà posées dans cette partie ─ */
let askedKeys = new Set();

/* ── SCORE BEST QUESTION ─────────────────────────────── */
// Choisit la question qui équilibre le mieux oui/non dans pool
function bestQuestion() {
  let best = null, bestScore = -1;

  for (const q of QUESTIONS) {
    if (askedKeys.has(q.key)) continue;

    let yes = 0;
    for (const c of pool) {
      if (q.getValue(c) === q.match) yes++;
    }
    const no = pool.length - yes;
    // On veut minimiser l'écart entre yes et no
    const balance = Math.min(yes, no);
    // Bonus si les deux côtés sont non nuls
    if (yes === 0 || no === 0) continue; // question inutile

    if (balance > bestScore) {
      bestScore = balance;
      best = q;
    }
  }

  return best; // null si plus rien
}

/* ── INIT ────────────────────────────────────────────── */
function startGame() {
  pool       = [...CHARS];
  asked      = 0;
  askedKeys  = new Set();
  currentQ   = null;

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
    d.className = "bi-dot" +
      (i < asked ? " asked" : i === asked ? " active" : "");
    el.appendChild(d);
  }
  document.getElementById("qNum").textContent = asked + 1;
}

/* ── QUESTION SUIVANTE ───────────────────────────────── */
function nextQuestion() {
  // Si plus qu'un seul candidat → on devine direct
  if (pool.length === 1) {
    return guessChar(pool[0]);
  }

  // Dernière question (asked === MAX_Q - 1) → on devine le plus probable
  if (asked === MAX_Q - 1) {
    // Tenter le plus "populaire" (w élevé) parmi les restants
    const top = pool.reduce((a, b) => (b.w > a.w ? b : a), pool[0]);
    return guessChar(top);
  }

  const q = bestQuestion();
  if (!q) {
    // Plus de questions discriminantes → on tente quand même
    const top = pool.reduce((a, b) => (b.w > a.w ? b : a), pool[0]);
    return guessChar(top);
  }

  currentQ = q;
  showQuestion(q.label);
}

/* ── AFFICHAGE QUESTION ──────────────────────────────── */
function showQuestion(label) {
  document.getElementById("biEmoji").textContent    = "🤔";
  document.getElementById("biQuestion").innerHTML   = label;
  document.getElementById("biHint").textContent     =
    `${pool.length} personnage${pool.length > 1 ? "s" : ""} possible${pool.length > 1 ? "s" : ""}`;

  const btns = document.getElementById("biBtns");
  btns.innerHTML = `
    <button class="bi-btn yes"   onclick="answer('oui')">✅ Oui</button>
    <button class="bi-btn no"    onclick="answer('non')">❌ Non</button>
    <button class="bi-btn maybe" onclick="answer('sais_pas')">🤷 Je sais pas</button>
  `;
}

/* ── RÉPONSE JOUEUR ──────────────────────────────────── */
function answer(rep) {
  if (rep === "sais_pas") {
    // Ne filtre pas, ne compte pas
    nextQuestion();
    return;
  }

  // Filtrer le pool
  const q = currentQ;
  pool = pool.filter(c => {
    const val = q.getValue(c);
    return rep === "oui" ? val === q.match : val !== q.match;
  });

  askedKeys.add(q.key);
  asked++;
  renderDots();

  if (pool.length === 0) {
    // Aucun candidat → bot perd
    showLose();
    return;
  }

  nextQuestion();
}

/* ── DEVINER UN PERSO ────────────────────────────────── */
function guessChar(char) {
  document.getElementById("biEmoji").textContent  = "💡";
  document.getElementById("biQuestion").innerHTML =
    `C'est… <strong>${char.n}</strong> ?`;
  document.getElementById("biHint").textContent   = "";

  const btns = document.getElementById("biBtns");
  btns.innerHTML = `
    <button class="bi-btn yes" onclick="guessResult(true,  '${escQ(char.n)}')">✅ Oui !</button>
    <button class="bi-btn no"  onclick="guessResult(false, '${escQ(char.n)}')">❌ Non…</button>
  `;
}

function escQ(s) {
  return s.replace(/'/g, "\\'");
}

/* ── RÉSULTAT DEVINETTE ──────────────────────────────── */
function guessResult(correct, name) {
  totalGames++;

  if (correct) {
    botStreak++;
    document.getElementById("winName").textContent = name;
    document.getElementById("wQuestions").textContent = asked + 1;
    document.getElementById("wStreak").textContent  = botStreak;
    document.getElementById("wTotal").textContent   = totalGames;
    document.getElementById("gameBox").style.display = "none";
    document.getElementById("winBox").style.display  = "block";
  } else {
    // Retirer ce perso du pool et continuer si on a encore de la marge
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
  botStreak = 0;
  totalGames++;

  document.getElementById("gameBox").style.display  = "none";
  document.getElementById("loseBox").style.display  = "block";
  document.getElementById("lStreak").textContent    = botStreak;
  document.getElementById("lTotal").textContent     = totalGames;

  // Peupler le select
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
  const name = document.getElementById("nameSelect").value;
  document.getElementById("loseBox").style.display = "none";
  // Juste réinitialiser pour la prochaine partie
  document.getElementById("introBox").style.display = "block";
}
