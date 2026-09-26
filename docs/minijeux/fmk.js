/* ═══════════════════════════════════════════════════════════════════
   FMK — Fuck, Marry, Kill
   ───────────────────────────────────────────────────────────────────
   But du jeu :
     Un trio de personnages Bleach est tiré au hasard.
     Le joueur doit assigner à chacun : Fuck / Marry / Kill.

   Dépendances :
     - ../js/data.js   (variable globale CHARS)
     - minijeux.css    (styles des cartes et boutons)

   Sections :
     1. ÉTAT GLOBAL
     2. EXCLUSIONS
     3. GÉNÉRATION DU TRIO
     4. CHOIX DU JOUEUR
     5. AFFICHAGE DES CARTES
     6. VALIDATION
     7. ÉCOUTEURS D'ÉVÉNEMENTS
     8. INITIALISATION
   ═══════════════════════════════════════════════════════════════════ */

/* ───────────────────────────────────────────────────────────────────
   1. ÉTAT GLOBAL
   ─────────────────────────────────────────────────────────────────── */

let trioActuel = [];                                       // Les 3 persos affichés
let choix = { fuck: null, marry: null, kill: null };       // Choix du joueur

/* ───────────────────────────────────────────────────────────────────
   2. EXCLUSIONS
   Persos que l'on ne veut jamais voir apparaître dans ce jeu
   ─────────────────────────────────────────────────────────────────── */

const EXCLUSIONS = [
  "Chizuru Honsho", "Hiyori Sarugaki", "Ichigo Kurosaki", "Jinta Hanakari",
  "Karin Kurosaki", "Keigo Asano", "Lilynette Gingerbuck", "Loly Aivirrne",
  "Mizuiro Kojima", "Momo Hinamori", "Orihime Inoue", "Riruka Dokugamine",
  "Tatsuki Arisawa", "Uryuu Ishida", "Ururu Tsumugiya", "Yachiru Kusajishi",
  "Yukio Hans Vorarlberna", "Yuzu Kurosaki"
];

/* ───────────────────────────────────────────────────────────────────
   3. GÉNÉRATION DU TRIO
   Tire 3 persos au hasard, hors exclusions
   ─────────────────────────────────────────────────────────────────── */

function genererTrio() {
  // Reset l'état
  choix = { fuck: null, marry: null, kill: null };
  document.getElementById('btn-valider').style.display = 'none';
  document.getElementById('resultBox').style.display   = 'none';
  document.getElementById('gameBox').style.display     = 'block';
  trioActuel = [];

  // Vérifie que data.js est bien chargé
  if (typeof CHARS === 'undefined') return;

  // Filtre les persos exclus puis tire 3 au hasard
  const listeFiltree = CHARS.filter(p => !EXCLUSIONS.includes(p.n));
  for (let i = 0; i < 3; i++) {
    const idx = Math.floor(Math.random() * listeFiltree.length);
    trioActuel.push(listeFiltree.splice(idx, 1)[0]);
  }

  afficherTrio();
}

/* ───────────────────────────────────────────────────────────────────
   4. CHOIX DU JOUEUR
   Assigne une action à un perso (et libère l'ancien emplacement)
   ─────────────────────────────────────────────────────────────────── */

function faireUnChoix(action, nomPerso) {
  // Si le perso était déjà assigné ailleurs, on le retire
  for (const cle in choix) {
    if (choix[cle] === nomPerso) choix[cle] = null;
  }
  // Assigne le perso à la nouvelle action
  choix[action] = nomPerso;

  afficherTrio();

  // Si les 3 choix sont faits, on affiche le bouton Valider
  if (choix.fuck && choix.marry && choix.kill) {
    document.getElementById('btn-valider').style.display = 'inline-block';
  }
}

/* ───────────────────────────────────────────────────────────────────
   5. AFFICHAGE DES CARTES
   Génère dynamiquement les 3 cartes avec images + boutons
   ─────────────────────────────────────────────────────────────────── */

function afficherTrio() {
  const zone = document.getElementById('fmk-zone');
  zone.innerHTML = '';

  trioActuel.forEach((perso, index) => {
    // Chemin image (assets/... ou fallback)
    const image = perso.img
      ? `../${perso.img}`
      : '../assets/personnages/default.png';

    // Vérifie si chaque action est active pour ce perso
    const isFuck  = choix.fuck  === perso.n;
    const isMarry = choix.marry === perso.n;
    const isKill  = choix.kill  === perso.n;

    // Crée la carte
    const carte = document.createElement('div');
    carte.className = 'card';
    carte.innerHTML = `
      <img src="${image}" alt="${perso.n}" onerror="this.src='https://via.placeholder.com/200x200?text=No+Image'">
      <div class="card-body">
        <h3>${perso.n}</h3>
        <div class="buttons-list">
          <button class="btn-choice fuck ${isFuck ? 'active' : ''}" data-action="fuck" data-index="${index}">💋 Fuck</button>
          <button class="btn-choice marry ${isMarry ? 'active' : ''}" data-action="marry" data-index="${index}">💍 Marry</button>
          <button class="btn-choice kill ${isKill ? 'active' : ''}" data-action="kill" data-index="${index}">💀 Kill</button>
        </div>
      </div>
    `;
    zone.appendChild(carte);
  });
}

/* ───────────────────────────────────────────────────────────────────
   6. VALIDATION
   Affiche le récap des choix
   ─────────────────────────────────────────────────────────────────── */

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

/* ───────────────────────────────────────────────────────────────────
   7. ÉCOUTEURS D'ÉVÉNEMENTS
   Délégation : un seul listener pour tous les boutons de choix
   ─────────────────────────────────────────────────────────────────── */

document.addEventListener('click', e => {
  const btn = e.target.closest('[data-action]');
  if (!btn) return;
  const action = btn.dataset.action;
  const index  = parseInt(btn.dataset.index);
  if (!isNaN(index) && trioActuel[index]) {
    faireUnChoix(action, trioActuel[index].n);
  }
});

/* ───────────────────────────────────────────────────────────────────
   8. INITIALISATION
   ─────────────────────────────────────────────────────────────────── */

window.addEventListener('load', genererTrio);