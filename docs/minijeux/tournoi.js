/* ══════════════════════════════════════════════════════
   BRACKET — GAME LOGIC
   même style que FMK
   ══════════════════════════════════════════════ */

let pool = [];
let round = [];
let winners = [];
let currentMatch = 0;

/* ── INIT TOURNOI ── */
function startTournament() {
  document.getElementById('gameBox').style.display = 'block';
  document.getElementById('resultBox').style.display = 'none';

  if (typeof CHARS === 'undefined') return;

  pool = shuffle([...CHARS]).slice(0, 16);

  round = [];
  winners = [];
  currentMatch = 0;

  for (let i = 0; i < 16; i += 2) {
    round.push([pool[i], pool[i + 1]]);
  }

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

  if (!match) {
    nextRound();
    return;
  }

  match.forEach((perso, index) => {

    const image = perso.img
      ? `../${perso.img}`
      : '../assets/personnages/default.png';

    const card = document.createElement('div');
    card.className = 'card';

    card.innerHTML = `
      <img src="${image}" alt="${perso.n}">
      <h3>${perso.n}</h3>

      <button class="btn-choice" data-action="pick" data-index="${index}">
        ⚔️ Choisir
      </button>
    `;

    zone.appendChild(card);
  });
}

/* ── CHOIX JOUEUR ── */
function pickWinner(index) {
  const match = round[currentMatch];
  winners.push(match[index]);

  currentMatch++;

  if (currentMatch >= round.length) {
    nextRound();
  } else {
    showMatch();
  }
}

/* ── ROUND SUIVANT ── */
function nextRound() {

  if (winners.length === 1) {
    return endTournament();
  }

  const newRound = [];

  for (let i = 0; i < winners.length; i += 2) {
    if (winners[i + 1]) {
      newRound.push([winners[i], winners[i + 1]]);
    } else {
      newRound.push([winners[i]]);
    }
  }

  round = newRound;
  winners = [];
  currentMatch = 0;

  showMatch();
}

/* ── FIN ── */
function endTournament() {
  const winner = winners[0] || round[0][0];

  document.getElementById('gameBox').style.display = 'none';
  document.getElementById('resultBox').style.display = 'flex';

  document.getElementById('winnerDisplay').innerHTML = `
    <div class="card">
      <img src="../${winner.img}">
      <h3>${winner.n}</h3>
    </div>
  `;
}

/* ── LISTENER GLOBAL (comme FMK) ── */
document.addEventListener('click', (e) => {

  const btn = e.target.closest('[data-action]');
  if (!btn) return;

  const action = btn.dataset.action;
  const index = parseInt(btn.dataset.index);

  if (action === 'pick') {
    pickWinner(index);
  }
});

/* ── INIT ── */
window.addEventListener('load', startTournament);
