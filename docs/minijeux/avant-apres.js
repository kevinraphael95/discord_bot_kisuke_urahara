const MAX_VOLUME = 74;
const $ = id => document.getElementById(id);

let imgA = null, imgB = null;
let usedImages = new Set();
let streak = 0, best = 0, loading = false;

window.addEventListener('load', () => {
  const s = JSON.parse(localStorage.getItem('bqc_tl_v1') || 'null');
  if (s) { best = s.best || 0; }
  updStats();
  startGame();
});

async function fetchHtml(url) {
  const res = await fetch(`https://corsproxy.io/?${encodeURIComponent(url)}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.text();
}

function setLoad(msg, pct) {
  $('loadMsg').textContent = msg;
  $('progFill').style.width = pct + '%';
}

async function fetchRandomPage(attempt = 0) {
  if (attempt > 15) throw new Error("Trop de tentatives");
  const num = Math.floor(Math.random() * MAX_VOLUME) + 1;
  const url = `https://sushiscan.fr/bleach-volume-${num}/`;
  let html;
  try { html = await fetchHtml(url); } catch { return fetchRandomPage(attempt + 1); }
  const match = html.match(/ts_reader\.run\((.+?)\)\s*;/s);
  if (!match) return fetchRandomPage(attempt + 1);
  let data;
  try { data = JSON.parse(match[1]); } catch { return fetchRandomPage(attempt + 1); }
  const images = data?.sources?.[0]?.images;
  if (!images?.length) return fetchRandomPage(attempt + 1);
  const pageIndex = Math.floor(Math.random() * (images.length - 1)) + 1;
  const imgUrl = images[pageIndex];
  if (usedImages.has(imgUrl)) return fetchRandomPage(attempt + 1);
  return { num, imgUrl, pageIndex };
}

async function fetchRandomPageInVolume(num, excludeIndex = -1, attempt = 0) {
  if (attempt > 15) throw new Error("Trop de tentatives");
  const url = `https://sushiscan.fr/bleach-volume-${num}/`;
  let html;
  try { html = await fetchHtml(url); } catch { return fetchRandomPageInVolume(num, excludeIndex, attempt + 1); }
  const match = html.match(/ts_reader\.run\((.+?)\)\s*;/s);
  if (!match) throw new Error("Parse fail");
  let data;
  try { data = JSON.parse(match[1]); } catch { throw new Error("JSON fail"); }
  const images = data?.sources?.[0]?.images;
  if (!images?.length) throw new Error("No images");
  let pageIndex;
  let tries = 0;
  do {
    pageIndex = Math.floor(Math.random() * (images.length - 1)) + 1;
    tries++;
    if (tries > 50) throw new Error("Pas assez de pages distinctes");
  } while (usedImages.has(images[pageIndex]) || pageIndex === excludeIndex);
  const imgUrl = images[pageIndex];
  usedImages.add(imgUrl);
  return { num, imgUrl, pageIndex };
}

async function loadImgEl(elId, data) {
  return new Promise((resolve, reject) => {
    const el = $(elId);
    const timeout = setTimeout(reject, 12000);
    el.onload  = () => { clearTimeout(timeout); resolve(); };
    el.onerror = () => { clearTimeout(timeout); reject(); };
    el.src = data.imgUrl;
  });
}

async function startGame() {
  if (loading) return;
  loading = true;
  showState('loading');
  setLoad('🎲 Tirage des pages…', 20);

  try {
    let a = await fetchRandomPage();
    usedImages.add(a.imgUrl);
    setLoad('🎲 Tirage de la deuxième page…', 50);
    let b = await fetchRandomPageInVolume(a.num, a.pageIndex);

    imgA = a; imgB = b;
    setLoad('🖼 Chargement images…', 80);
    await Promise.all([loadImgEl('imgA', imgA), loadImgEl('imgB', imgB)]);
    showState('game');
  } catch(e) {
    console.error(e);
    showState('error');
  }
  loading = false;
}

function answer(choice) {
  if (loading) return;
  const correct = (choice === 'before' && imgB.pageIndex < imgA.pageIndex) ||
                  (choice === 'after'  && imgB.pageIndex > imgA.pageIndex);

  if (correct) {
    streak++;
    if (streak > best) {
      best = streak;
      localStorage.setItem('bqc_tl_v1', JSON.stringify({ best }));
    }
    updStats();
    nextRound();
  } else {
    showResult();
  }
}

async function nextRound() {
  if (loading) return;
  loading = true;
  showState('loading');
  setLoad('🖼 Nouvelle page…', 30);

  try {
    imgA = imgB;
    $('imgA').src = imgA.imgUrl;

    let b = await fetchRandomPageInVolume(imgA.num, imgA.pageIndex);
    imgB = b;

    setLoad('🖼 Chargement…', 70);
    await loadImgEl('imgB', imgB);
    showState('game');
  } catch(e) {
    console.error(e);
    showState('error');
  }
  loading = false;
}

function showResult() {
  $('resStreak').textContent = streak;
  $('resBest').textContent = best > 0 ? `Record : ${best}` : '';
  streak = 0;
  updStats();
  localStorage.setItem('bqc_tl_v1', JSON.stringify({ best }));
  showState('result');
}

function restart() {
  usedImages = new Set();
  imgA = null; imgB = null;
  streak = 0;
  updStats();
  startGame();
}

function showState(state) {
  ['loadBox','gameBox','resultBox','errorBox'].forEach(id => {
    const el = $(id);
    if (el) el.style.display = 'none';
  });
  const map = { loading: 'loadBox', game: 'gameBox', result: 'resultBox', error: 'errorBox' };
  const target = $(map[state]);
  if (target) target.style.display = 'flex';
}

function updStats() {
  $('sStreak').textContent = streak;
  $('sBest').textContent   = best;
  const dots = $('streakDots');
  if (!dots) return;
  dots.innerHTML = '';
  const show = Math.max(streak, 5);
  for (let i = 0; i < show; i++) {
    const d = document.createElement('div');
    d.className = 'sdot' + (i < streak ? ' active' : '');
    dots.appendChild(d);
  }
}
