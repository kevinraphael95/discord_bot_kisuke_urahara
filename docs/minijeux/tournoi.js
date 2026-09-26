/* ═══════════════════════════════════════════════════════════════════
   TOURNOI — Bracket à élimination directe
   ───────────────────────────────────────────────────────────────────
   But du jeu :
     16 personnages Bleach s'affrontent en 1v1.
     Le joueur choisit son préféré à chaque match.
     Les gagnants avancent → huitièmes → quarts → demies → finale.

   Dépendances :
     - ../js/data.js (variable globale CHARS)
     - minijeux.css

   Sections :
     1. ÉTAT GLOBAL
     2. NOMS DES TOURS
     3. DÉMARRAGE
     4. CONSTRUCTION D'UN TOUR
     5. AFFICHAGE D'UN MATCH
     6. CHOIX DU GAGNANT
     7. PASSAGE AU TOUR SUIVANT
     8. FIN DU TOURNOI
     9. ÉCOUTEURS D'ÉVÉNEMENTS
    10. INITIALISATION
   ═══════════════════════════════════════════════════════════════════ */

/* ───────────────────────────────────────────────────────────────────
   1. ÉTAT GLOBAL
   ─────────────────────────────────────────────────────────────────── */

let pool = [];                 // Les 16 persos du tournoi
let round = [];                // Matchs du tour actuel : [[p1, p2], [p3, p4], ...]
let winners = [];              // Gagnants du tour actuel (alimente le tour suivant)
let currentMatch = 0;          // Index du match affiché dans le tour
let roundNumber = 0;           // Numéro du tour (0 = huitièmes)
let totalMatchesInRound = 0;   // Nombre de matchs dans le tour actuel

/* ───────────────────────────────────────────────────────────────────
   2. NOMS DES TOURS
   ─────────────────────────────────────────────────────────────────── */

const ROUND_NAMES = ['Huitièmes de finale', 'Quarts de finale', 'Demi-finales', 'Finale'];

/* ───────────────────────────────────────────────────────────────────
   3. DÉMARRAGE
   Choisit 16 persos au hasard et lance les huitièmes
   ─────────────────────────────────────────────────────────────────── */

function startTournament() {
  document.getElementById('gameBox').style.display = 'block';
  document.getElementById('resultBox').style.display = 'none';

  if (typeof CHARS === 'undefined') return;

  pool = shuffle([...CHARS]).slice(0, 16);
  roundNumber = 0;
  buildRound(pool);
}

/* ───────────────────────────────────────────────────────────────────
   4. CONSTRUCTION D'UN TOUR
   Regroupe les persos par paires pour créer les matchs
   ─────────────────────────────────────────────────────────────────── */

function buildRound(chars) {
  round = [];
  winners = [];
  currentMatch = 0;

  for (let i = 0; i < chars.length; i += 2) {
    if (chars[i + 1]) round.push([chars[i], chars[i + 1]]);
    else round.push([chars[i]]);      // Cas impair : passe directement
  }

  totalMatchesInRound = round.length;
  showMatch();
}

// Mélange un tableau (Fisher-Yates non nécessaire ici, suffisant)
function shuffle(arr) {
  return arr.sort(() => Math.random() - 0.5);
}

/* ───────────────────────────────────────────────────────────────────
   5. AFFICHAGE D'UN MATCH
   Affiche les 2 cartes des persos + le séparateur VS + les infos
   ─────────────────────────────────────────────────────────────────── */

function showMatch() {
  const zone = document.getElementById('matchZone');
  zone.innerHTML = '';

  const match = round[currentMatch];

  // Plus de match → on passe au tour suivant
  if (!match) { nextRound(); return; }

  // Match à 1 seul perso (impaire) → gagnant automatique
  if (match.length === 1) {
    winners.push(match[0]);
    currentMatch++;
    showMatch();
    return;
  }

  // Met à jour l'en-tête (nom du tour + progression)
  const rName = ROUND_NAMES[roundNumber] || `Tour ${roundNumber + 1}`;
  document.getElementById('roundLabel').textContent =
    `Tour ${roundNumber + 1} · Match ${currentMatch + 1}/${totalMatchesInRound}`;
  document.getElementById('roundTitle').textContent = rName;
  document.getElementById('progressFill').style.width =
    (currentMatch / totalMatchesInRound * 100) + '%';

  // Info match restants
  const remaining = totalMatchesInRound - currentMatch - 1;
  document.getElementById('matchInfo').textContent =
    remaining > 0
      ? `${remaining} match${remaining > 1 ? 's' : ''} restant${remaining > 1 ? 's' : ''} dans ce tour`
      : 'Dernier match du tour !';

  // Crée les 2 cartes + le séparateur VS
  match.forEach((perso, index) => {
    const img = perso.img ? `../${perso.img}` : '../assets/personnages/default.png';

    const card = document.createElement('div');
    card.className = 'card';
    card.innerHTML = `
      <img src="${img}" alt="${perso.n}" loading="lazy">
      <div class="card-body">
        <h3>${perso.n}</h3>
        <button class="btn-choice" data-action="pick" data-index="${index}">⚔️ Choisir</button>
      </div>
    `;
    zone.appendChild(card);

    // Ajoute un "VS" entre les deux cartes
    if (index === 0) {
      const vs = document.createElement('div');
      vs.className = 'vs-label';
      vs.textContent = 'VS';
      zone.appendChild(vs);
    }
  });
}

/* ───────────────────────────────────────────────────────────────────
   6. CHOIX DU GAGNANT
   Le joueur clique sur "Choisir" → enregistre le gagnant
   ─────────────────────────────────────────────────────────────────── */

function pickWinner(index) {
  winners.push(round[currentMatch][index]);
  currentMatch++;

  if (currentMatch >= round.length) nextRound();
  else showMatch();
}

/* ───────────────────────────────────────────────────────────────────
   7. PASSAGE AU TOUR SUIVANT
   Si un seul gagnant → fin du tournoi
   Sinon → on recommence avec les gagnants
   ─────────────────────────────────────────────────────────────────── */

function nextRound() {
  if (winners.length === 1) { endTournament(winners[0]); return; }
  roundNumber++;
  buildRound(winners);
}

/* ───────────────────────────────────────────────────────────────────
   8. FIN DU TOURNOI
   Affiche le gagnant final
   ─────────────────────────────────────────────────────────────────── */

function endTournament(winner) {
  document.getElementById('gameBox').style.display = 'none';
  document.getElementById('resultBox').style.display = 'flex';

  const img = winner.img ? `../${winner.img}` : '../assets/personnages/default.png';
  document.getElementById('winnerDisplay').innerHTML = `
    <div class="card">
      <img src="${img}" alt="${winner.n}">
      <div class="card-body">
        <h3>${winner.n}</h3>
      </div>
    </div>
  `;
}

/* ───────────────────────────────────────────────────────────────────
   9. ÉCOUTEURS D'ÉVÉNEMENTS
   Délégation : un seul listener pour tous les boutons "Choisir"
   ─────────────────────────────────────────────────────────────────── */

document.addEventListener('click', (e) => {
  const btn = e.target.closest('[data-action="pick"]');
  if (!btn) return;
  pickWinner(parseInt(btn.dataset.index));
});

/* ───────────────────────────────────────────────────────────────────
   10. INITIALISATION
   ─────────────────────────────────────────────────────────────────── */

window.addEventListener('load', startTournament);