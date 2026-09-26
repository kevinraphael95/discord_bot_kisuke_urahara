/* ── theme.js — gestion auto + manuel du thème ── */
(function () {
  const root = document.documentElement;
  const btn = document.getElementById('themeBtn');

  function updateBtn() {
    if (!btn) return;
    btn.dataset.themeState = root.getAttribute('data-theme');
  }

  function applyTheme(theme) {
    root.setAttribute('data-theme', theme);
    updateBtn();
  }

  // Thème initial (déjà appliqué dans le <head> anti-flash, on resync au cas où)
  const saved = localStorage.getItem('theme');
  const system = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  applyTheme(saved || system);

  // Bouton
  if (btn) {
    btn.addEventListener('click', () => {
      const next = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      applyTheme(next);
      localStorage.setItem('theme', next);
    });
  }

  // Suit l'OS si l'utilisateur n'a jamais choisi
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
    if (!localStorage.getItem('theme')) {
      applyTheme(e.matches ? 'dark' : 'light');
    }
  });
})();