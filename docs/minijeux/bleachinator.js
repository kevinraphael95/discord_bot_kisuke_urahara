/* ═══════════════════════════════════════════════════════
   BLEACHINATOR — bleachinator.js
   ═══════════════════════════════════════════════════════ */

/* ── ÉTAT ────────────────────────────────────────────── */
let pool       = [];
let asked      = 0;
let botStreak  = 0;
let totalGames = 0;
let currentQ   = null;
let askedKeys  = new Set();

const MAX_Q = 7;

/* ── QUESTIONS ───────────────────────────────────────── */
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
    label: "Ton personnage est-il un <strong>Humain ou Fullbring</strong> ?",
    getValue: c => (c.r === "Humain" || c.r === "Fullbring") ? "oui" : "non",
    match: "oui"
  },
  {
    key: "r_hollow",
    label: "Ton personnage est-il un <strong>Hollow pur</strong> (pas Arrancar) ?",
    getValue: c => c.r === "Hollow" ? "oui" : "non",
    match: "oui"
  },
  {
    key: "r_modsoul",
    label: "Ton personnage est-il une <strong>âme artificielle / Mod-Soul</strong> ?",
    getValue: c => c.r === "Mod-Soul/Âme artificielle" ? "oui" : "non",
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
    key: "af_independant",
    label: "Ton personnage est-il <strong>indépendant</strong> (Urahara Shop, Vizards non promus…) ?",
    getValue: c => c.af === "Indépendant" ? "oui" : "non",
    match: "oui"
  },
  {
    key: "af_hueco",
    label: "Ton personnage réside-t-il à <strong>Hueco Mundo</strong> (sans être Espada) ?",
    getValue: c => c.af === "Hueco Mundo" ? "oui" : "non",
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
    label: "Ton personnage est-il <strong>mort définitivement</strong> ?",
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
    label: "Ton personnage est-il au <strong>sommet de la puissance</strong> (dangerosité 5) ?",
    getValue: c => c.d === 5 ? "oui" : "non",
    match: "oui"
  },
  {
    key: "d_low",
    label: "Ton personnage est-il <strong>peu puissant</strong> (dangerosité ≤ 2) ?",
    getValue: c => c.d <= 2 ? "oui" : "non",
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
    getValue: c => (c.hc === "Blanc" || c.hc === "Gris") ? "oui" : "non",
    match: "oui"
  },
  {
    key: "hc_chauve",
    label: "Ton personnage est-il <strong>chauve</strong> ?",
    getValue: c => c.hc === "Chauve" ? "oui" : "non",
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
    key: "arc_full",
    label: "Ton personnage est-il introduit dans l'<strong>arc Fullbringers</strong> ?",
    getValue: c => c.arc === "Arc Fullbringers (4)" ? "oui" : "non",
    match: "oui"
  },
  {
    key: "w_many",
    label: "Ton personnage a-t-il <strong>remporté beaucoup de combats</strong> (≥ 5 victoires) ?",
    getValue: c => c.w >= 5 ? "oui" : "non",
    match: "oui"
  },
  {
    key: "w_zero",
    label: "Ton personnage n'a <strong>jamais gagné de combat</strong> officiellement ?",
    getValue: c => c.w === 0 ? "oui" : "non",
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
  {
    key: "vicecaptain",
    label: "Ton personnage est-il (ou a-t-il été) <strong>vice-capitaine</strong> ?",
    getValue: c => {
      const vcs = [
        "Nanao Ise","Genshiro Okikiba","Marechiyo Omaeda","Izuru Kira",
        "Kiyone Kotetsu","Momo Hinamori","Renji Abarai","Shuhei Hisagi",
        "Mashiro Kuna","Rangiku Matsumoto","Ikkaku Madarame","Akon",
        "Sentaro Kotsubaki","Chojiro Sasakibe","Yachiru Kusajishi",
        "Nemu Kurotsuchi","Atau Rindo","Yuyu Yayahara"
      ];
      return vcs.includes(c.n) ? "oui" : "non";
    },
    match: "oui"
  },
  {
    key: "espada_top5",
    label: "Ton personnage est-il une <strong>Espada numérotée 1 à 5</strong> ?",
    getValue: c => {
      const top = ["Coyote Starrk","Lilynette Gingerbuck","Baraggan Louisenbairn","Tier Harribel","Ulquiorra Cifer","Nnoitra Gilga"];
      return top.includes(c.n) ? "oui" : "non";
    },
    match: "oui"
  },
  {
    key: "sternritter",
    label: "Ton personnage est-il un <strong>Sternritter</strong> (Chevalier Étoilé) ?",
    getValue: c => {
      const sr = [
        "Jugram Haschwalth","Pernida Parnkgjas","Askin Nakk Le Vaar","Gerard Valkyrie",
        "Lille Barro","Bambietta Basterbine","As Nodt","Liltotto Lamperd","Bazz-B",
        "Cang Du","Quilge Opie","BG9","PePe Waccabrada","Robert Accutrone",
        "Driscoll Berci","Meninas McAllon","Berenice Gabrielli","Jerome Guizbatt",
        "Mask De Masculine","Candice Catnipp","NaNaNa Najahkoop","Gremmy Thoumeaux",
        "Nianzol Weizol","Royd Lloyd","Loyd Lloyd","Giselle Gewelle"
      ];
      return sr.includes(c.n) ? "oui" : "non";
    },
    match: "oui"
  },
];

/* ── ENTROPIE DE SHANNON ─────────────────────────────── */
// Score maximal = 1 quand yes == no (split parfait 50/50)
// Score minimal → 0 quand tout est d'un côté
function entropy(yes, total) {
  if (yes === 0 || yes === total) return 0;
  const p = yes / total;
  const q = 1 - p;
  return -(p * Math.log2(p) + q * Math.log2(q));
}

function bestQuestion() {
  let best = null, bestScore = -1;
  const n = pool.length;

  for (const q of QUESTIONS) {
    if (askedKeys.has(q.key)) continue;
    let yes = 0;
    for (const c of pool) {
      if (q.getValue(c) === q.match) yes++;
    }
    if (yes === 0 || yes === n) continue; // question inutile
    const score = entropy(yes, n);
    if (score > bestScore) { bestScore = score; best = q; }
  }

  return best;
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
    d.className = "bi-dot" +
      (i < asked ? " asked" : i === asked ? " active" : "");
    el.appendChild(d);
  }
  document.getElementById("qNum").textContent = Math.min(asked + 1, MAX_Q);
}

/* ── QUESTION SUIVANTE ───────────────────────────────── */
function nextQuestion() {
  // Devinette directe si pool ≤ 2 ou dernière question
  if (pool.length <= 2 || asked >= MAX_Q - 1) {
    const top = pool.reduce((a, b) => (b.w > a.w ? b : a), pool[0]);
    return guessChar(top);
  }

  const q = bestQuestion();
  if (!q) {
    const top = pool.reduce((a, b) => (b.w > a.w ? b : a), pool[0]);
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
    nextQuestion();
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
    document.getElementById("winName").textContent        = name;
    document.getElementById("wQuestions").textContent     = asked + 1;
    document.getElementById("wStreak").textContent        = botStreak;
    document.getElementById("wTotal").textContent         = totalGames;
    document.getElementById("gameBox").style.display      = "none";
    document.getElementById("winBox").style.display       = "block";
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
