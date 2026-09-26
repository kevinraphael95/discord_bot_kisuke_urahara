/* ── nav.js — injecte les liens de la nav (compatible sous-dossier) ── */
(function () {
  const isInSubdir = /\/minijeux\//.test(location.pathname);
  const prefix = isInSubdir ? '../' : '';

  const LINKS = {
    index:     prefix + 'index.html',
    install:   prefix + 'install.html',
    commandes: prefix + 'commandes.html',
    guesser:   prefix + 'guesser.html',
    minijeux:  prefix + 'minijeux.html',
    discord:   prefix + '404.html'
  };

  document.querySelectorAll('[data-nav]').forEach(a => {
    const key = a.dataset.nav;
    if (LINKS[key]) a.setAttribute('href', LINKS[key]);
  });

  const current = location.pathname.split('/').pop() || 'index.html';
  document.querySelectorAll('.nav-links a, .nav-mobile a').forEach(a => {
    if (a.getAttribute('href') === prefix + current) a.classList.add('active');
  });

  const burger = document.getElementById('navBurger');
  const mobileMenu = document.getElementById('navMobile');
  if (burger && mobileMenu) {
    burger.addEventListener('click', () => {
      burger.classList.toggle('open');
      mobileMenu.classList.toggle('open');
    });
    mobileMenu.querySelectorAll('a').forEach(a => {
      a.addEventListener('click', () => {
        burger.classList.remove('open');
        mobileMenu.classList.remove('open');
      });
    });
  }
})();