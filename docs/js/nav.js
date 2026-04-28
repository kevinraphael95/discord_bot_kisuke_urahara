(function () {
  const pages = [
    { href: 'commandes.html', label: 'Commandes' },
    { href: 'reiatsu.html',   label: 'Reiatsu' },
    { href: 'guesser.html',   label: 'Character Guesser' },
    { href: 'scanguess.html',   label: '????' },
    { href: 'install.html',   label: 'Installation' },
  ];
  const themes = [
    { id: 'shinigami',    label: 'Shinigami',    icon: '⚔️' },
    { id: 'quincy',       label: 'Quincy',       icon: '↗️' }
  ];

  const savedTheme = localStorage.getItem('shinigami-theme') || 'shinigami';
  document.documentElement.setAttribute('data-theme', savedTheme);

  const current = location.pathname.split('/').pop() || 'index.html';

  const navLinks = pages.map(p => {
    const active = (current === p.href || (current === '' && p.href === 'index.html')) ? ' class="active"' : '';
    return `<li><a href="${p.href}"${active}>${p.label}</a></li>`;
  }).join('\n    ');

  const drawerLinks = pages.map(p => {
    const active = (current === p.href || (current === '' && p.href === 'index.html')) ? ' class="active"' : '';
    return `<a href="${p.href}"${active} onclick="closeNav()">${p.label}</a>`;
  }).join('\n  ');

  const themeOptions = themes.map(t =>
    `<button class="theme-opt" data-theme="${t.id}" title="${t.label}">${t.icon} ${t.label}</button>`
  ).join('');

  const drawerThemeOptions = themes.map(t =>
    `<button class="drawer-theme-opt" data-theme="${t.id}">${t.icon} ${t.label}</button>`
  ).join('');

  const activeTheme = themes.find(t => t.id === savedTheme) || themes[0];

  document.body.insertAdjacentHTML('afterbegin', `
<nav>
  <a class="nav-logo" href="index.html">⚡ Kisuke <span>Bot</span></a>
  <ul class="nav-links">
    ${navLinks}
  </ul>
  <div class="nav-right">
    <div class="theme-switcher" id="themeSwitcher">
      <button class="theme-toggle" id="themeToggle">${activeTheme.icon} ${activeTheme.label}</button>
      <div class="theme-menu" id="themeMenu">
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
    <div class="drawer-theme-label">Thème visuel</div>
    <div class="drawer-theme-btns">
      ${drawerThemeOptions}
    </div>
  </div>
</div>
`);

  document.getElementById('themeToggle').addEventListener('click', function (e) {
    e.stopPropagation();
    document.getElementById('themeMenu').classList.toggle('open');
  });

  function updateThemeButtons(themeId) {
    document.querySelectorAll('.theme-opt, .drawer-theme-opt').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.theme === themeId);
    });
    const active = themes.find(t => t.id === themeId);
    if (active) {
      document.getElementById('themeToggle').textContent = `${active.icon} ${active.label}`;
    }
  }

  updateThemeButtons(savedTheme);

  document.addEventListener('click', function (e) {
    const btn = e.target.closest('[data-theme]');
    if (btn) {
      const t = btn.dataset.theme;
      document.documentElement.setAttribute('data-theme', t);
      localStorage.setItem('shinigami-theme', t);
      updateThemeButtons(t);
      document.getElementById('themeMenu').classList.remove('open');
    }
    if (!e.target.closest('#themeSwitcher')) {
      const m = document.getElementById('themeMenu');
      if (m) m.classList.remove('open');
    }
  });

  window.toggleThemeMenu = function () {
    document.getElementById('themeMenu').classList.toggle('open');
  };
  window.toggleNav = function () {
    document.getElementById('ham').classList.toggle('open');
    document.getElementById('drawer').classList.toggle('open');
  };
  window.closeNav = function () {
    document.getElementById('ham').classList.remove('open');
    document.getElementById('drawer').classList.remove('open');
  };
})();
