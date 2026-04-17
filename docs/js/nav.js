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
    const active = (current === p.href || (current === '' && p.href === 'index.html')) ? ' class="active"' : '';
    return `<li><a href="${p.href}"${active}>${p.label}</a></li>`;
  }).join('\n    ');
  const drawerLinks = pages.map(p => {
    const active = (current === p.href || (current === '' && p.href === 'index.html')) ? ' class="active"' : '';
    return `<a href="${p.href}"${active} onclick="closeNav()">${p.label}</a>`;
  }).join('\n  ');
  const themeOptions = themes.map(t =>
    `<button class="theme-opt" data-theme="${t.id}" title="${t.label}">${t.icon}</button>`
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
    <div class="theme-switcher" id="themeSwitcher">
      <button class="theme-toggle" id="themeToggle" title="Changer le thème">🎨</button>
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
  document.getElementById('themeToggle').addEventListener('click', function(e) {
    e.stopPropagation();
    document.getElementById('themeMenu').classList.toggle('open');
  });
  function updateThemeButtons(themeId) {
    document.querySelectorAll('.theme-opt, .drawer-theme-opt').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.theme === themeId);
    });
  }
  updateThemeButtons(savedTheme);
  document.addEventListener('click', function (e) {
    const btn = e.target.closest('[data-theme]');
    if (btn) {
      const t = btn.dataset.theme;
      document.documentElement.setAttribute('data-theme', t);
      localStorage.setItem('kisuke-theme', t);
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

  // ── EASTER EGG : Konami Code → Archives secrètes ─────
  const KONAMI = ['ArrowUp','ArrowUp','ArrowDown','ArrowDown','ArrowLeft','ArrowRight','ArrowLeft','ArrowRight'];
  let konamiIdx = 0;
  document.addEventListener('keydown', function(e) {
    if (e.key === KONAMI[konamiIdx]) {
      konamiIdx++;
      if (konamiIdx === KONAMI.length) {
        konamiIdx = 0;
        openEasterEgg();
      }
    } else {
      konamiIdx = 0;
    }
  });

  function openEasterEgg() {
    if (document.getElementById('egg-overlay')) return;
    const overlay = document.createElement('div');
    overlay.id = 'egg-overlay';
    overlay.style.cssText = `
      position:fixed;inset:0;z-index:9999;background:rgba(0,0,0,.92);
      display:flex;flex-direction:column;align-items:center;justify-content:center;gap:1.5rem;
      animation:rise .4s ease;
    `;
    overlay.innerHTML = `
      <div style="font-family:'Shippori Mincho',serif;font-size:1.6rem;color:#f87171;letter-spacing:.1em;">☠ ARCHIVES SECRÈTES ☠</div>
      <div style="font-size:.75rem;color:#8e8a84;letter-spacing:.2em;">↑↑↓↓←→←→</div>
      <div style="display:flex;flex-direction:column;gap:.7rem;margin-top:1rem;">
        <a href="scans.html" style="background:#130606;border:1px solid #991b1b;color:#f87171;padding:.8rem 2rem;font-family:'DM Sans',sans-serif;font-size:.85rem;font-weight:600;letter-spacing:.1em;text-decoration:none;text-align:center;text-transform:uppercase;">📖 Lire les scans</a>
      </div>
      <button onclick="document.getElementById('egg-overlay').remove()" style="margin-top:.5rem;background:none;border:none;color:#484440;font-size:.75rem;cursor:pointer;letter-spacing:.1em;">[ FERMER ]</button>
    `;
    document.body.appendChild(overlay);
    overlay.addEventListener('click', function(e) {
      if (e.target === overlay) overlay.remove();
    });
  }

})();
