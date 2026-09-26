/* ── commandes.js — recherche + compteurs + accordéon ── */

(function () {
  // ── Compteurs par catégorie ──
  document.querySelectorAll('.cat').forEach(cat => {
    const count = cat.querySelectorAll('.cmd').length;
    const badge = cat.querySelector('.cat-count');
    if (badge) badge.textContent = count;
  });

  // ── Toggle accordéon ──
  document.querySelectorAll('.cat-header').forEach(hdr => {
    hdr.addEventListener('click', () => {
      hdr.classList.toggle('open');
      hdr.nextElementSibling.classList.toggle('open');
    });
  });

  // ── Recherche ──
  const input = document.getElementById('searchInput');
  if (!input) return;

  input.addEventListener('input', () => {
    const q = input.value.toLowerCase().trim();
    document.querySelectorAll('.cat').forEach(cat => {
      let visible = 0;
      cat.querySelectorAll('.cmd').forEach(cmd => {
        const name = cmd.querySelector('.cmd-name')?.textContent.toLowerCase() || '';
        const desc = cmd.querySelector('.cmd-desc')?.textContent.toLowerCase() || '';
        const match = !q || name.includes(q) || desc.includes(q);
        cmd.style.display = match ? '' : 'none';
        if (match) visible++;
      });
      cat.style.display = (!q || visible > 0) ? '' : 'none';
      if (q) {
        cat.querySelector('.cat-header')?.classList.add('open');
        cat.querySelector('.cmd-list')?.classList.add('open');
      }
    });
  });
})();