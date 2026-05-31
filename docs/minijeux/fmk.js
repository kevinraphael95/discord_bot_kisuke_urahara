/* ══════════════════════════════════════════════════════
   FMK — GAME LOGIC
   ══════════════════════════════════════════════════════ */

let trioActuel = [];
let choix = { fuck: null, marry: null, kill: null };

const EXCLUSIONS = [
  "Chizuru Honsho", "Hiyori Sarugaki", "Ichigo Kurosaki", "Jinta Hanakari",
  "Karin Kurosaki", "Keigo Asano", "Lilynette Gingerbuck", "Loly Aivirrne",
  "Mizuiro Kojima", "Momo Hinamori", "Orihime Inoue", "Riruka Dokugamine",
  "Tatsuki Arisawa", "Uryuu Ishida", "Ururu Tsumugiya", "Yachiru Kusajishi",
  "Yukio Hans Vorarlberna", "Yuzu Kurosaki"
];

/* ── GÉNÉRATION DU TRIO ── */
function genererTrio() {
  choix = { fuck: null, marry: null, kill: null };
  document.getElementById('btn-valider').style.display = 'none';
  document.getElementById('resultBox').style.display   = 'none';
  document.getElementById('gameBox').style.display     = 'block';
  trioActuel = [];

  if (typeof CHARS === 'undefined') return;

  const listeFiltree = CHARS.filter(p => !EXCLUSIONS.includes(p.n));
  for (let i = 0; i < 3; i++) {
    const idx = Math.floor(Math.random() * listeFiltree.length);
    trioActuel.push(listeFiltree.splice(idx, 1)[0]);
  }

  afficherTrio();
}

/* ── CHOIX D'UN PERSONNAGE ── */
function faireUnChoix(action, nomPerso) {
  // Retirer le perso s'il était déjà assigné ailleurs
  for (const cle in choix) {
    if (choix[cle] === nomPerso) choix[cle] = null;
  }
  // Libérer le slot si déjà occupé
  choix[action] = null;
  choix[action] = nomPerso;

  afficherTrio();

  if (choix.fuck && choix.marry && choix.kill) {
    document.getElementById('btn-valider').style.display = 'inline-block';
  }
}

/* ── AFFICHAGE DES CARTES ── */
function afficherTrio() {
  const zone = document.getElementById('fmk-zone');
  zone.innerHTML = '';

  trioActuel.forEach((perso, index) => {
    const image = perso.img
      ? `../${perso.img}`
      : '../assets/personnages/default.png';

    const carte = document.createElement('div');
    carte.className = 'card';
    carte.innerHTML = `
      <img src="${image}" alt="${perso.n}" onerror="this.src='https://via.placeholder.com/200x200?text=No+Image'">
      <div class="card-body">
        <h3>${perso.n}</h3>
        <div class="buttons-list">
          <button class="btn-choice fuck ${choix.fuck === perso.n ? 'active' : ''}" data-action="fuck" data-index="${index}">💋 Fuck</button>
          <button class="btn-choice marry ${choix.marry === perso.n ? 'active' : ''}" data-action="marry" data-index="${index}">💍 Marry</button>
          <button class="btn-choice kill ${choix.kill === perso.n ? 'active' : ''}" data-action="kill" data-index="${index}">💀 Kill</button>
        </div>
      </div>
    `;
    zone.appendChild(carte);
  });
}

/* ── VALIDATION ── */
function validerChoix() {
  document.getElementById('gameBox').style.display = 'none';
  document.getElementById('fmkSummary').innerHTML = `
    <div style="padding:20px; text-align:center;">
      <p>💋 <strong>Fuck :</strong> ${choix.fuck}</p>
      <p>💍 <strong>Marry :</strong> ${choix.marry}</p>
      <p>💀 <strong>Kill :</strong> ${choix.kill}</p>
    </div>
  `;
  document.getElementById('resultBox').style.display = 'block';
}

/* ── LISTENER GLOBAL (remplace les onclick inline) ── */
document.addEventListener('click', e => {
  const btn = e.target.closest('[data-action]');
  if (!btn) return;
  const action = btn.dataset.action;
  const index  = parseInt(btn.dataset.index);
  if (!isNaN(index) && trioActuel[index]) {
    faireUnChoix(action, trioActuel[index].n);
  }
});

/* ── INIT ── */
window.addEventListener('load', genererTrio);
