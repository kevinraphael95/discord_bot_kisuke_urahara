let trioActuel = [];
let choix = { fuck: null, marry: null, kill: null };

function genererTrio() {
    // Reset des choix et du bouton de validation
    choix = { fuck: null, marry: null, kill: null };
    document.getElementById('btn-valider').style.display = 'none';
    trioActuel = [];
    
    // Sécurité au cas où data.js n'est pas trouvé
    if (typeof CHARS === 'undefined') {
        alert("Erreur : Impossible de charger les personnages depuis js/data.js");
        return;
    }

    let copieList = [...CHARS];
    // Pioche 3 personnages aléatoires uniques
    for (let i = 0; i < 3; i++) {
        let indexAuHasard = Math.floor(Math.random() * copieList.length);
        trioActuel.push(copieList.splice(indexAuHasard, 1)[0]);
    }
    afficherTrio();
}

function faireUnChoix(action, nomPerso) {
    // Si le perso sélectionné avait déjà une autre action, on la retire
    for (let cle in choix) {
        if (choix[cle] === nomPerso) choix[cle] = null;
    }
    // Si cette action était déjà prise par un autre perso, on la libère
    for (let cle in choix) {
        if (cle === action) choix[cle] = null;
    }

    // Assigner le choix actuel
    choix[action] = nomPerso;
    afficherTrio();

    // Si les 3 choix sont faits et valides, on affiche le bouton de validation
    if (choix.fuck && choix.marry && choix.kill) {
        document.getElementById('btn-valider').style.display = 'inline-block';
    }
}

function afficherTrio() {
    let zone = document.getElementById('fmk-zone');
    zone.innerHTML = '';

    trioActuel.forEach(perso => {
        // Ajustement du chemin de l'image (puisqu'on est dans le sous-dossier minijeux/)
        let image = perso.img ? `../${perso.img}` : '../assets/personnages/default.png';
        let nomEchappe = perso.n.replace(/'/g, "\\'");

        let carte = document.createElement('div');
        carte.className = 'card';
        carte.innerHTML = `
            <img src="${image}" alt="${perso.n}" onerror="this.src='https://via.placeholder.com/200x200?text=No+Image'">
            <h3>${perso.n}</h3>
            <span class="badge">${perso.r}</span>
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
    alert(`🎯 Choix enregistrés !\n\n💋 Fuck : ${choix.fuck}\n💍 Marry : ${choix.marry}\n💀 Kill : ${choix.kill}`);
    genererTrio();
}

// Lancement automatique du premier trio au chargement de la page
window.onload = genererTrio;
