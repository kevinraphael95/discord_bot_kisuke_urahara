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

  if (match.length === 1) {
    winners.push(match[0]);
    currentMatch++;
    showMatch();
    return;
  }

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

  match.forEach((perso, index) => {
    const img = perso.img ? `../${perso.img}` :
