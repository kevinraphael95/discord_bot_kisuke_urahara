const MAX_FILE = 10;
const DATA_DIR = 'data/kluboutside/';
const IMG_DIR = 'assets/kluboutside/';
const IMG_EXTS = ['png', 'jpg', 'jpeg', 'webp'];

let allQuestions = {};
let keys = [];
let currentIndex = 0;

async function loadAll() {
  const merged = {};

  for (let i = 1; i <= MAX_FILE; i++) {
    try {
      const response = await fetch(`${DATA_DIR}ko${i}.json`);

      if (!response.ok) break;

      const data = await response.json();

      Object.assign(merged, data.Questions || {});
    } catch {
      break;
    }
  }

  return merged;
}

async function findImage(key) {
  for (const ext of IMG_EXTS) {
    const url = `${IMG_DIR}ko${key}.${ext}`;

    try {
      const response = await fetch(url, { method: 'HEAD' });

      if (response.ok) {
        return url;
      }
    } catch {}
  }

  return null;
}

async function renderCard(index) {
  currentIndex = index;

  const key = keys[index];
  const question = allQuestions[key];

  const card = document.getElementById('koCard');

  document.querySelectorAll('.ko-item').forEach((element, i) => {
    element.classList.toggle('active', i === index);
  });

  const activeElement = document.querySelector('.ko-item.active');

  if (activeElement) {
    activeElement.scrollIntoView({
      block: 'nearest'
    });
  }

  card.innerHTML = `
    <div class="ko-empty">
      Chargement…
    </div>
  `;

  const imgUrl = await findImage(key);

  card.innerHTML = `
    <div class="ko-card-num">
      Question n°${key} · ${index + 1} / ${keys.length}
    </div>

    <div class="ko-card-date">
      📅 ${question.date || '—'}
    </div>

    <div class="ko-card-question">
      ${escHtml(question.question || '—')}
    </div>

    <div class="ko-card-answer">
      ${escHtml(question.réponse || '—')}
    </div>

    ${
      imgUrl
        ? `<img class="ko-card-img"
                src="${imgUrl}"
                alt="Illustration question ${key}">`
        : ''
    }

    <div class="ko-card-nav">
      <button
        class="ko-nav-btn"
        id="koPrev"
        ${index === 0 ? 'disabled' : ''}
      >
        ◀ Précédent
      </button>

      <button
        class="ko-nav-btn"
        id="koNext"
        ${index === keys.length - 1 ? 'disabled' : ''}
      >
        Suivant ▶
      </button>
    </div>
  `;

  document
    .getElementById('koPrev')
    ?.addEventListener('click', () => renderCard(currentIndex - 1));

  document
    .getElementById('koNext')
    ?.addEventListener('click', () => renderCard(currentIndex + 1));
}

function escHtml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\n/g, '<br>');
}

function buildList(filter = '') {
  const list = document.getElementById('koList');

  list.innerHTML = '';

  const search = filter.toLowerCase();

  keys.forEach((key, i) => {
    const question = allQuestions[key];

    const text = (question.question || '').toLowerCase();

    if (
      search &&
      !text.includes(search) &&
      !key.includes(search)
    ) {
      return;
    }

    const item = document.createElement('div');

    item.className =
      'ko-item' + (i === currentIndex ? ' active' : '');

    item.textContent =
      `#${key} — ${question.question?.slice(0, 60) || ''}…`;

    item.addEventListener('click', () => {
      renderCard(i);
    });

    list.appendChild(item);
  });
}

(async () => {
  allQuestions = await loadAll();

  keys = Object.keys(allQuestions).sort(
    (a, b) => parseInt(a) - parseInt(b)
  );

  if (!keys.length) {
    document.getElementById('koCard').innerHTML = `
      <div class="ko-empty">
        Aucune question trouvée.
      </div>
    `;

    return;
  }

  buildList();

  renderCard(0);

  document
    .getElementById('koSearch')
    .addEventListener('input', event => {
      buildList(event.target.value);
    });

  document
    .getElementById('koRandom')
    .addEventListener('click', () => {
      const index = Math.floor(
        Math.random() * keys.length
      );

      renderCard(index);

      buildList(
        document.getElementById('koSearch').value
      );
    });
})();
