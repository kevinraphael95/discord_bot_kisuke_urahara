/* ══ BRACKET — GAME LOGIC ══ */

let pool = [];
let round = [];
let winners = [];
let currentMatch = 0;
let roundNumber = 0;
let totalMatchesInRound = 0;

const ROUND_NAMES = ['Huitièmes de finale', 'Quarts de finale', 'Demi-finales', 'Finale'];

/* ── INIT ── */
function startTournament() {
  document.getElementById('gameBox').style.display = 'block';
  document.getElementById('resultBox').style.display = 'none';
  if (typeof CHARS === 'undefined') return;
  pool = shuffle([...CHARS]).slice(0, 16);
  roundNumber = 0;
  buildRound(pool);
}

function buildRound(chars) {
  round = [];
  winners = [];
  currentMatch = 0;
  for (let i = 0; i < chars.length; i += 2) {
    if (chars[i + 1]) round.push([chars[i], chars[i + 1]]);
    else round.push([chars[i]]);
  }
  totalMatchesInRound = round.length;
  showMatch();
}

/* ── SHUFFLE ── */
function shuffle(arr) {
  return arr.sort(() => Math.random() - 0.5);
}

/* ── AFFICHAGE MATCH ── */
function showMatch() {
  const zone = document.getElementById('matchZone');
  zone.innerHTML = '';

  const match = round[currentMatch];
  if (!match) { nextRound(); return; }

  // bye automatique
  if (match.length === 1) {
    winners.push(match[0]);
    currentMatch++;
    showMatch();
    return;
  }

  // header
  const rName = ROUND_NAMES[roundNumber] || `Tour ${roundNumber + 1}`;
  document.getElementById('roundLabel').textContent =
    `Tour ${roundNumber + 1} · Match ${currentMatch + 1}/${totalMatchesInRound}`;
  document.getElementById('roundTitle').textContent = rName;
  document.getElementById('progressFill').style.width =
    (currentMatch / totalMatchesInRound * 100) + '%';

  const remaining = totalMatchesInRound - currentMatch - 1;
  document.getElementById('matchInfo').textContent =
    remaining > 0
      ? `${remaining} match${remaining > 1 ? 's' : ''} restant${remaining > 1 ? 's' : ''} dans ce tour`
      : 'Dernier match du tour !';

  // cartes — nom au-dessus, image, bouton en bas
  match.forEach((perso, index) => {
    const img = perso.img ? `../${perso.img}` : '../assets/personnages/default.png';
    const card = document.createElement('div');
    card.className = 'card';
    card.innerHTML = `
      <div class="card-body">
        <h3>${perso.n}</h3>
      </div>
      <img src="${img}" alt="${perso.n}" loading="lazy">
      <div class="card-footer">
        <button class="btn-choice" data-action="pick" data-index="${index}">⚔️ Choisir</button>
      </div>
    `;
    zone.appendChild(card);

    // VS entre les deux
    if (index === 0) {
      const vs = document.createElement('div');
      vs.className = 'vs-label';
      vs.textContent = 'VS';
      zone.appendChild(vs);
    }
  });
}

/* ── CHOIX ── */
function pickWinner(index) {
  winners.push(round[currentMatch][index]);
  currentMatch++;
  if (currentMatch >= round.length) nextRound();
  else showMatch();
}

/* ── ROUND SUIVANT ── */
function nextRound() {
  if (winners.length === 1) { endTournament(winners[0]); return; }
  roundNumber++;
  buildRound(winners);
}

/* ── FIN ── */
function endTournament(winner) {
  document.getElementById('gameBox').style.display = 'none';
  document.getElementById('resultBox').style.display = 'flex';
  const img = winner.img ? `../${winner.img}` : '../assets/personnages/default.png';
  document.getElementById('winnerDisplay').innerHTML = `
    <div class="card">
      <div class="card-body">
        <h3>${winner.n}</h3>
      </div>
      <img src="${img}" alt="${winner.n}">
    </div>
  `;
}

/* ── LISTENER GLOBAL ── */
document.addEventListener('click', (e) => {
  const btn = e.target.closest('[data-action="pick"]');
  if (!btn) return;
  pickWinner(parseInt(btn.dataset.index));
});

/* ── AUTO START ── */
window.addEventListener('load', startTournament);
