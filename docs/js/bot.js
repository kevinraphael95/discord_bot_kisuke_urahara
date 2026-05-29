// guide.js — tabs, toggle catégories, filtre commandes

// ── Tabs ──────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  const tabs   = document.querySelectorAll('.gtab');
  const panels = document.querySelectorAll('.tab-panel');

  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      panels.forEach(p => p.classList.remove('active'));
      tab.classList.add('active');
      document.getElementById('tab-' + tab.dataset.tab).classList.add('active');
    });
  });

  // compter les commandes par catégorie
  document.querySelectorAll('.cat').forEach(cat => {
    const id    = cat.dataset.id;
    const count = cat.querySelectorAll('.cmd').length;
    const el    = document.getElementById('c-' + id);
    if (el) el.textContent = count;
  });
});

// ── Toggle catégorie ──────────────────────────────────
function toggle(hdr) {
  hdr.classList.toggle('open');
  hdr.nextElementSibling.classList.toggle('open');
}

// ── Filtre commandes ──────────────────────────────────
function filterCmds() {
  const q = document.getElementById('si').value.toLowerCase().trim();

  document.querySelectorAll('.cat').forEach(cat => {
    let visible = 0;
    cat.querySelectorAll('.cmd').forEach(cmd => {
      const text = cmd.textContent.toLowerCase();
      if (!q || text.includes(q)) {
        cmd.classList.remove('hidden');
        visible++;
      } else {
        cmd.classList.add('hidden');
      }
    });
    // masquer la catégorie entière si aucun résultat
    cat.classList.toggle('hidden', visible === 0);
    // forcer l'ouverture pendant la recherche
    if (q) {
      cat.querySelector('.cat-hdr').classList.add('open');
      cat.querySelector('.cmd-list').classList.add('open');
    }
  });
}
