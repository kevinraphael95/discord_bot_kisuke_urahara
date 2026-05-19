let trioActuel = [];
let choix = { fuck: null, marry: null, kill: null };

// Liste des personnages à exclure du jeu
// Liste des personnages à exclure du jeu (mineurs)
const EXCLUSIONS = [
    "Chizuru Honsho", 
    "Ichigo Kurosaki", 
    "Jinta Hanakari", 
    "Karin Kurosaki", 
    "Keigo Asano", 
    "Mizuiro Kojima", 
    "Orihime Inoue", 
    "Riruka Dokugamine",
    "Tatsuki Arisawa", 
    "Uryuu Ishida", 
    "Ururu Tsumugiya", 
    "Yukio Hans Vorarlberna", 
    "Yuzu Kurosaki"
];

function genererTrio() {
    choix = { fuck: null, marry: null, kill: null };
    document.getElementById('btn-valider').style.display = 'none';
    document.getElementById('resultBox').style.display = 'none';
    document.getElementById('gameBox').style.display = 'block';
    trioActuel = [];
    
    if (typeof CHARS === 'undefined') return;

    // Filtrage des personnages
    let listeFiltree = CHARS.filter(p => !EXCLUSIONS.includes(p.n));

    for (let i = 0; i < 3; i++) {
        let indexAuHasard = Math.floor(Math.random() * listeFiltree.length);
        trioActuel.push(listeFiltree.splice(indexAuHasard, 1)[0]);
    }
    afficherTrio();
}

function faireUnChoix(action, nomPerso) {
    for (let cle in choix) { if (choix[cle] === nomPerso) choix[cle] = null; }
    for (let cle in choix) { if (cle === action) choix[cle] = null; }

    choix[action] = nomPerso;
    afficherTrio();

    if (choix.fuck && choix.marry && choix.kill) {
        document.getElementById('btn-valider').style.display = 'inline-block';
    }
}

function afficherTrio() {
    let zone = document.getElementById('fmk-zone');
    zone.innerHTML = '';

    trioActuel.forEach(perso => {
        let image = perso.img ? `../${perso.img}` : '../assets/personnages/default.png';
        let nomEchappe = perso.n.replace(/'/g, "\\'");

        let carte = document.createElement('div');
        carte.className = 'card';
        carte.innerHTML = `
            <img src="${image}" alt="${perso.n}" onerror="this.src='https://via.placeholder.com/200x200?text=No+Image'">
            <h3>${perso.n}</h3>
            <div class="buttons-list">
                <button class="btn-choice fuck ${choix.fuck === perso.n ? 'active' : ''}" onclick="faireUnChoix('fuck', '${nomEchappe}')">💋 Fuck</button>
                <button class="btn-choice marry ${choix.marry === perso.n ? 'active' : ''}" onclick="faireUnChoix('marry', '${nomEchappe}')">💍 Marry</button>
                <button class="btn-choice kill ${choix.kill === perso.n ? 'active' : ''}" onclick="faireUnChoix('kill', '${nomEchappe}')">💀 Kill</button>
            </div>
        `;
        zone.appendChild(carte);
    });
}

function validerChoix() {
    document.getElementById('gameBox').style.display = 'none';
    const summary = document.getElementById('fmkSummary');
    
    // Affichage propre sans pop-up
    summary.innerHTML = `
        <div style="padding: 20px; text-align: center;">
            <p>💋 <strong>Fuck :</strong> ${choix.fuck}</p>
            <p>💍 <strong>Marry :</strong> ${choix.marry}</p>
            <p>💀 <strong>Kill :</strong> ${choix.kill}</p>
        </div>
    `;
    
    document.getElementById('resultBox').style.display = 'block';
}

window.onload = genererTrio;
