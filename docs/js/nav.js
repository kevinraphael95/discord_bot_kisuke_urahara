(function () {
  const pages = [
    { href: 'commandes.html', label: 'Commandes' },
    { href: 'reiatsu.html', label: 'Reiatsu' },
    { href: 'guesser.html', label: 'Character Guesser' },
    { href: 'minijeux.html', label: 'Minijeux' },
    { href: 'install.html', label: 'Installation' },
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
  const savedTheme = localStorage.getItem('shinigami-theme') || 'shinigami';
  document.documentElement.setAttribute('data-theme', savedTheme);

  const activeTheme = themes.find(t => t.id === savedTheme) || themes[0];

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

  const themeOptions = themes.map(t =>
    `<button class="theme-opt" data-theme="${t.id}">${t.icon} ${t.label}</button>`
  ).join('');

  const drawerThemeOptions = themes.map(t =>
    `<button class="drawer-theme-opt" data-theme="${t.id}">${t.icon} ${t.label}</button>`
  ).join('');

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
    <div class="theme-switcher">
      <button id="themeToggle" class="theme-toggle">
        ${activeTheme.icon} ${activeTheme.label}
      </button>

      <div id="themeMenu" class="theme-menu">
        <div class="theme-menu-title">Thème</div>
        ${themeOptions}
      </div>
    </div>

    <button class="ham" id="ham" onclick="toggleNav()"><span></span><span></span><span></span></button>
  </div>
</nav>

<div class="drawer" id="drawer">
  ${drawerLinks}
  <div class="drawer-theme-section">
    ${drawerThemeOptions}
  </div>
</div>
`);

  // ── THEME LOGIC ──
  const themeToggle = document.getElementById('themeToggle');
  const themeMenu = document.getElementById('themeMenu');

  themeToggle.addEventListener('click', (e) => {
    e.stopPropagation();
    themeMenu.classList.toggle('open');
  });

  document.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-theme]');

    if (btn) {
      const theme = btn.dataset.theme;

      document.documentElement.setAttribute('data-theme', theme);
      localStorage.setItem('shinigami-theme', theme);

      const t = themes.find(x => x.id === theme);
      themeToggle.textContent = `${t.icon} ${t.label}`;

      themeMenu.classList.remove('open');
    }

    if (!e.target.closest('.theme-switcher')) {
      themeMenu.classList.remove('open');
    }
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

// ── PAGE TRANSITIONS ──
document.addEventListener('click', (e) => {
  const link = e.target.closest('a[href]');
  if (!link) return;
  const href = link.getAttribute('href');
  // Ignorer les liens externes, ancres, et nouveaux onglets
  if (!href || href.startsWith('#') || href.startsWith('http') || link.target === '_blank') return;
  e.preventDefault();
  document.body.classList.add('page-out');
  setTimeout(() => { window.location.href = href; }, 260);
});

  

})();
