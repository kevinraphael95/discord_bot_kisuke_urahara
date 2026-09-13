(function () {
  const pages = [
    { href: 'install.html', label: 'Installation' },
    { href: 'commandes.html', label: 'Commandes' },
    { href: 'guesser.html', label: 'Character Guesser' },
    { href: 'minijeux.html', label: 'Minijeux' },
    { href: 'kluboutside.html', label: 'Klub Outside' },
  ];

  const themes = [
    { id: 'shinigami', label: 'Shinigami', icon: '⚔️' },
    { id: 'quincy', label: 'Quincy', icon: '↗️' }
  ];

  // ── CALCUL DU PREFIX (GitHub Pages safe) ──
  const parts = location.pathname.split('/').filter(Boolean);

  const SUB_DIRS = ['minijeux'];
  const inSub = parts.length >= 2 && SUB_DIRS.includes(parts[parts.length - 2]);

  const prefix = inSub ? '../' : './';

  const current = parts[parts.length - 1] || 'index.html';

  // ── THEME ──
  const validThemes = ['shinigami', 'quincy'];
  const saved = localStorage.getItem('shinigami-theme');
  const savedTheme = validThemes.includes(saved) ? saved : 'shinigami';
  document.documentElement.setAttribute('data-theme', savedTheme);

  // ── ACTIVE PAGE ──
  function isActive(href) {
    return current === href;
  }

  // ── LINKS ──
  const navLinks = pages.map(p => {
    const active = isActive(p.href) ? ' class="active"' : '';
    return `<li><a href="${prefix}${p.href}"${active}>${p.label}</a></li>`;
  }).join('');

  const drawerLinks = pages.map(p => {
    const active = isActive(p.href) ? ' class="active"' : '';
    return `<a href="${prefix}${p.href}"${active} onclick="closeNav()">${p.label}</a>`;
  }).join('');

  // Theme : boutons plats inline, plus de menu flottant
  function renderThemeLinks(theme, containerClass) {
    return themes.map(t => {
      const active = t.id === theme ? ' active' : '';
      return `<button class="${containerClass}${active}" data-theme="${t.id}">${t.icon} ${t.label}</button>`;
    }).join('');
  }

  // ── INSERT NAV ──
  document.body.insertAdjacentHTML('afterbegin', `
<nav>
  <a class="nav-logo" href="${prefix}index.html">
    ⚡ Kisuke <span>Bot</span>
  </a>

  <ul class="nav-links">
    ${navLinks}
  </ul>

  <div class="nav-right">
    <div class="theme-links" id="themeLinks">
      ${renderThemeLinks(savedTheme, 'theme-link')}
    </div>

    <button class="ham" id="ham" onclick="toggleNav()"><span></span><span></span><span></span></button>
  </div>
</nav>

<div class="drawer" id="drawer">
  ${drawerLinks}
  <div class="drawer-theme-section">
    <div class="drawer-theme-btns" id="drawerThemeLinks">
      ${renderThemeLinks(savedTheme, 'drawer-theme-opt')}
    </div>
  </div>
</div>
`);

  // ── THEME LOGIC (un seul clic, plus de menu à ouvrir/fermer) ──
  document.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-theme]');
    if (!btn) return;

    const theme = btn.dataset.theme;
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('shinigami-theme', theme);

    document.querySelectorAll('.theme-link, .drawer-theme-opt').forEach(b => {
      b.classList.toggle('active', b.dataset.theme === theme);
    });
  });

  // ── DRAWER ──
  window.toggleNav = function () {
    document.getElementById('ham').classList.toggle('open');
    document.getElementById('drawer').classList.toggle('open');
  };

  window.closeNav = function () {
    document.getElementById('ham').classList.remove('open');
    document.getElementById('drawer').classList.remove('open');
  };

})();
