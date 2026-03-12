/* ── NAV CENTRALISÉE ─────────────────────────────────── */
(function () {
  const pages = [
    { href: 'index.html',     label: 'Accueil' },
    { href: 'commandes.html', label: 'Commandes' },
    { href: 'reiatsu.html',   label: 'Reiatsu' },
    { href: 'guesser.html',   label: 'Guesser' },
    { href: 'install.html',   label: 'Installation' },
  ];

  // Détecte la page active
  const current = location.pathname.split('/').pop() || 'index.html';

  // Construit les liens nav
  const navLinks = pages.map(p => {
    const active = (current === p.href || (current === '' && p.href === 'index.html')) ? ' class="active"' : '';
    return `<li><a href="${p.href}"${active}>${p.label}</a></li>`;
  }).join('\n    ');

  // Construit les liens drawer
  const drawerLinks = pages.map(p => {
    const active = (current === p.href || (current === '' && p.href === 'index.html')) ? ' class="active"' : '';
    return `<a href="${p.href}"${active} onclick="closeNav()">${p.label}</a>`;
  }).join('\n  ');

  // Injecte la nav
  document.body.insertAdjacentHTML('afterbegin', `
<nav>
  <a class="nav-logo" href="index.html">⚡ Kisuke <span>Bot</span></a>
  <ul class="nav-links">
    ${navLinks}
  </ul>
  <button class="ham" id="ham" onclick="toggleNav()"><span></span><span></span><span></span></button>
</nav>

<div class="drawer" id="drawer">
  ${drawerLinks}
</div>
`);

  // Fonctions hamburger
  window.toggleNav = function () {
    document.getElementById('ham').classList.toggle('open');
    document.getElementById('drawer').classList.toggle('open');
  };
  window.closeNav = function () {
    document.getElementById('ham').classList.remove('open');
    document.getElementById('drawer').classList.remove('open');
  };
})();
