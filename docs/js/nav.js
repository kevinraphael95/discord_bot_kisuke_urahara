(function () {
  const pages = [
    { href: 'commandes.html', label: 'Commandes' },
    { href: 'reiatsu.html',   label: 'Reiatsu' },
    { href: 'guesser.html',   label: 'Character Guesser' },
    { href: 'install.html',   label: 'Installation' },
  ];

  const themes = [
    { id: 'soul-society', label: 'Soul Society', icon: '⚔️' },
    { id: 'hueco-mundo',  label: 'Hueco Mundo',  icon: '🌑' },
    { id: 'hollow',       label: 'Hollow',       icon: '💀' },
    { id: 'gotei',        label: 'Gotei 13',     icon: '🌿' }
  ];

  const savedTheme = localStorage.getItem('kisuke-theme') || 'soul-society';
  document.documentElement.setAttribute('data-theme', savedTheme);

  const current = location.pathname.split('/').pop() || 'index.html';

  const navLinks = pages.map(p => {
    const active = (current === p.href) ? ' class="active"' : '';
    return `<li><a href="${p.href}"${active}>${p.label}</a></li>`;
  }).join('\n');

  const drawerLinks = pages.map(p => {
    const active = (current === p.href) ? ' class="active"' : '';
    return `<a href="${p.href}"${active} onclick="closeNav()">${p.label}</a>`;
  }).join('\n');

  const themeOptions = themes.map(t =>
    `<button class="theme-opt" data-theme="${t.id}">${t.icon}</button>`
  ).join('');

  const drawerThemeOptions = themes.map(t =>
    `<button class="drawer-theme-opt" data-theme="${t.id}">${t.icon} ${t.label}</button>`
  ).join('');

  document.body.insertAdjacentHTML('afterbegin', `
<nav>
  <a class="nav-logo" href="index.html">⚡ Kisuke <span>Bot</span></a>

  <ul class="nav-links">
    ${navLinks}
  </ul>

  <div class="nav-right">
    <div class="theme-switcher">
      <button id="themeToggle">🎨</button>
      <div id="themeMenu">${themeOptions}</div>
    </div>
    <button class="ham" onclick="toggleNav()">☰</button>
  </div>
</nav>

<div id="drawer">
  ${drawerLinks}
  <div>${drawerThemeOptions}</div>
</div>
`);

  // 🔥 KONAMI CODE (MODIFIÉ)
  const KONAMI = ['ArrowUp','ArrowUp','ArrowDown','ArrowDown','ArrowLeft','ArrowRight','ArrowLeft','ArrowRight'];
  let i = 0;

  document.addEventListener('keydown', (e) => {
    if (e.key === KONAMI[i]) {
      i++;
      if (i === KONAMI.length) {
        i = 0;

        // 👉 DIRECT SCANS
        window.location.href = "scans.html";
      }
    } else {
      i = 0;
    }
  });

  window.toggleNav = function () {
    document.getElementById('drawer').classList.toggle('open');
  };

  window.closeNav = function () {
    document.getElementById('drawer').classList.remove('open');
  };

})();
