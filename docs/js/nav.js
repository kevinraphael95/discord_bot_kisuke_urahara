/* ── nav.js — injecte la nav + menu mobile (compatible sous-dossiers) ── */
(function () {
  // Détecte si on est dans un sous-dossier (ex: /minijeux/)
  const isInSubdir = /\/minijeux\//.test(location.pathname) ||
                     /\/minijeux\//.test(location.href);
  const prefix = isInSubdir ? '../' : '';

  const NAV_HTML = `
    <div class="nav-inner">
      <a class="nav-logo" href="${prefix}index.html">
        <span class="nav-logo-mark"><span>K</span></span>
        Kisuke Urahara
      </a>
      <ul class="nav-links">
        <li><a href="${prefix}install.html">Installation</a></li>
        <li><a href="${prefix}commandes.html">Commandes</a></li>
        <li><a href="${prefix}guesser.html">Guesser</a></li>
        <li><a href="${prefix}minijeux.html">Mini-jeux</a></li>
      </ul>
      <div class="nav-actions">
        <button class="theme-btn" id="themeBtn" aria-label="Changer le thème"></button>
        <a class="btn btn-primary btn-sm nav-discord-btn" href="${prefix}404.html">Ajouter à Discord</a>
        <button class="nav-burger" id="navBurger" aria-label="Menu">
          <span></span><span></span><span></span>
        </button>
      </div>
    </div>
  `;

  const MOBILE_HTML = `
    <div class="nav-mobile" id="navMobile">
      <a href="${prefix}install.html">Installation</a>
      <a href="${prefix}commandes.html">Commandes</a>
      <a href="${prefix}guesser.html">Guesser</a>
      <a href="${prefix}minijeux.html">Mini-jeux</a>
      <a href="${prefix}404.html" class="nav-mobile-cta">Ajouter à Discord</a>
    </div>
  `;

  const nav = document.createElement('nav');
  nav.innerHTML = NAV_HTML;
  document.body.insertBefore(nav, document.body.firstChild);

  // Menu mobile (injecté après la nav)
  const mobile = document.createElement('div');
  mobile.innerHTML = MOBILE_HTML;
  const mobileMenu = mobile.firstElementChild;
  document.body.insertBefore(mobileMenu, nav.nextSibling);

  // Lien actif
  const current = location.pathname.split('/').pop() || 'index.html';
  nav.querySelectorAll('.nav-links a').forEach(a => {
    if (a.getAttribute('href') === prefix + current) a.classList.add('active');
  });
  mobileMenu.querySelectorAll('a').forEach(a => {
    if (a.getAttribute('href') === prefix + current) a.classList.add('active');
  });

  // Toggle menu mobile
  const burger = document.getElementById('navBurger');
  burger.addEventListener('click', () => {
    burger.classList.toggle('open');
    mobileMenu.classList.toggle('open');
  });

  // Fermer le menu si on clique sur un lien
  mobileMenu.querySelectorAll('a').forEach(a => {
    a.addEventListener('click', () => {
      burger.classList.remove('open');
      mobileMenu.classList.remove('open');
    });
  });
})();