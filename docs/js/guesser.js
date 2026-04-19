const COLS=[
  {k:'r',lb:'RACE'},{k:'sx',lb:'SEXE'},{k:'arc',lb:'ARC'},
  {k:'af',lb:'AFFIL.'},{k:'d',lb:'FORCE'},{k:'st',lb:'STATUT'},
  {k:'hc',lb:'CHEVEUX'},{k:'bday',lb:'ANNIV.'},{k:'wl',lb:'COMBATS'},
];
const MAX=8;
const $=id=>document.getElementById(id);

function seededShuffle(arr,seed){const a=arr.slice();let s=seed>>>0;for(let i=a.length-1;i>0;i--){s=(Math.imul(s,1664525)+1013904223)>>>0;const j=s%(i+1);[a[i],a[j]]=[a[j],a[i]];}return a;}
function dayNum(){const s=new Date('2025-01-01');const t=new Date();t.setHours(0,0,0,0);return Math.floor((t-s)/86400000);}
function todayChar(){const d=dayNum();return seededShuffle(CHARS,d^0xBEA6)[d%CHARS.length];}
function todayKey(){const d=new Date();return d.getFullYear()+'-'+(d.getMonth()+1)+'-'+d.getDate();}

// Convertit "DD/MM" en numéro de jour dans l'année (1-366) pour comparaison
function bdayToDay(bday){
  if(!bday||bday==='??/??')return null;
  const p=bday.split('/');
  if(p.length<2)return null;
  const d=parseInt(p[0],10),mo=parseInt(p[1],10);
  if(isNaN(d)||isNaN(mo))return null;
  // Jours cumulés par mois (année non-bissextile)
  const cum=[0,31,59,90,120,151,181,212,243,273,304,334];
  return cum[mo-1]+d;
}

const ARC_ORDER = [
  'Le Shinigami Remplaçant (1)',
  "Soul Society : L'Invasion (2.1)",
  'Soul Society : Le Sauvetage (2.2)',
  'Arrancar : Invasion du monde des humains (3.1)',
  'Arrancar : Invasion du Hueco Mundo (3.2)',
  'Arrancar : Bataille de Karakura (3.3)',
  'Arc Fullbringers (4)',
  'Guerre Sanglante de Mille Ans (5)',
  'NO BREATHES FROM HELL (6)',
];

function cmp(m,t){
  const dd=Math.abs(m.d-t.d),dw=Math.abs(m.w-t.w);
  const sameBd=m.bday===t.bday;
  const sameMo=m.bday!=='??/??' && t.bday!=='??/??' && m.bday.slice(3)===t.bday.slice(3);

  // Direction anniversaire : ▲ = le vrai anniv est plus tard dans l'année, ▼ = plus tôt
  let bdDir='';
  const mDay=bdayToDay(m.bday), tDay=bdayToDay(t.bday);
  if(!sameBd && mDay!==null && tDay!==null){
    bdDir = mDay < tDay ? '▲' : '▼';
  }

  return[
    {v:m.r,   s:m.r===t.r?'correct':'wrong',a:''},
    {v:m.sx,  s:m.sx===t.sx?'correct':'wrong',a:''},
    {v:m.arc, s:(()=>{
      if(m.arc===t.arc) return 'correct';
      const mi=ARC_ORDER.indexOf(m.arc), ti=ARC_ORDER.indexOf(t.arc);
      return (mi>=0&&ti>=0&&Math.abs(mi-ti)===1)?'close':'wrong';
    })(), a:(()=>{
      if(m.arc===t.arc) return '';
      const mi=ARC_ORDER.indexOf(m.arc), ti=ARC_ORDER.indexOf(t.arc);
      if(mi<0||ti<0) return '';
      return mi<ti?'▲':'▼';
    })()},
    {v:m.af,  s:m.af===t.af?'correct':'wrong',a:''},
    {v:'★'.repeat(m.d)+'☆'.repeat(5-m.d),s:m.d===t.d?'correct':dd===1?'close':'wrong',a:m.d<t.d?'▲':m.d>t.d?'▼':''},
    {v:m.st,  s:m.st===t.st?'correct':'wrong',a:''},
    {v:m.hc,  s:m.hc===t.hc?'correct':'wrong',a:''},
    {v:m.bday,s:sameBd?'correct':sameMo?'close':'wrong',a:sameBd?'':bdDir},
    {v:m.w+'V/'+m.l+'D',s:m.w===t.w&&m.l===t.l?'correct':dw<=2?'close':'wrong',a:m.w<t.w?'▲':m.w>t.w?'▼':''},
  ];
}

function mkRow(m,f,tgt){
  const row=document.createElement('div');row.className='row';
  const nc=document.createElement('div');nc.className='cell '+(m.n===tgt.n?'correct':'wrong');nc.textContent=m.n;row.appendChild(nc);
  f.forEach(x=>{const c=document.createElement('div');c.className='cell '+x.s;c.innerHTML=x.v+(x.a?'<span style="font-size:7px;margin-left:2px">'+x.a+'</span>':'');row.appendChild(c);});
  $('gr').prepend(row);
}
function mkCard(m,f,tgt){
  const win=m.n===tgt.n;
  const card=document.createElement('div');card.className='card '+(win?'ok':'ko');
  const top=document.createElement('div');top.className='ctop';
  const nm=document.createElement('div');nm.className='cname '+(win?'correct':'wrong');nm.textContent=m.n;
  const badge=document.createElement('div');badge.className='cbadge';badge.innerHTML=m.r+'<br>'+m.arc;
  top.appendChild(nm);top.appendChild(badge);card.appendChild(top);
  const g=document.createElement('div');g.className='cgrid';
  COLS.forEach((col,i)=>{
    const x=f[i];
    const cc=document.createElement('div');cc.className='cc '+x.s;
    const lb=document.createElement('div');lb.className='cl';lb.textContent=col.lb;
    const vl=document.createElement('div');vl.className='cv';
    vl.innerHTML=x.v+(x.a?'<span style="font-size:.5rem;opacity:.8"> '+x.a+'</span>':'');
    cc.appendChild(lb);cc.appendChild(vl);g.appendChild(cc);
  });
  card.appendChild(g);$('gc').prepend(card);
}
function clr(){$('gr').innerHTML='';$('gc').innerHTML='';}

let mode='daily';
let tgt=todayChar(),dG=[],dOver=false,dSel=-1;
let sStr=0,sBst=0,sKil=0;
let sQ=[],sQi=0,sCur=null,sG=[],sSel=-1,sOver=false,sRec=0;

function switchMode(m){
  mode=m;
  $('btnD').classList.toggle('active',m==='daily');
  $('btnS').classList.toggle('active',m==='survival');
  $('dbar').style.display=m==='daily'?'flex':'none';
  $('sbar').classList.toggle('on',m==='survival');
  $('htitle').textContent=m==='daily'?'RÈGLES — QUOTIDIEN':'RÈGLES — SURVIE';
  $('hd').style.display=m==='daily'?'':'none';
  $('hs').style.display=m==='survival'?'':'none';
  $('flash').classList.remove('on');
  document.body.classList.toggle('survival-mode',m==='survival');
  if(m==='daily'){
    $('send').classList.remove('on');clr();
    dG.forEach(x=>{mkRow(x.m,x.f,tgt);mkCard(x.m,x.f,tgt);});
    updDots();
    if(dOver) showDRes(dG.some(x=>x.m.n===tgt.n));
    else $('rb').classList.remove('on');
    $('gi').disabled=dOver;$('gbtn').disabled=dOver;
    if(!dOver) foc();
  } else {
    $('rb').classList.remove('on');
    if(sOver){clr();showSEnd();}
    else{
      clr();
      if(!sCur) sInit();
      else sG.forEach(x=>{mkRow(x.m,x.f,sCur);mkCard(x.m,x.f,sCur);});
      updSUI();$('gi').disabled=false;$('gbtn').disabled=false;foc();
    }
  }
}
function foc(){setTimeout(()=>$('gi').focus(),60);}

function saveD(won){try{localStorage.setItem('bleachg25v2',JSON.stringify({date:todayKey(),guesses:dG.map(x=>({n:x.m.n})),over:dOver,won}));}catch(e){}}
function loadD(){
  try{
    const s=JSON.parse(localStorage.getItem('bleachg25v2'));
    if(!s||s.date!==todayKey())return;
    for(const sv of (s.guesses||[])){const fr=CHARS.find(x=>x.n===sv.n);if(!fr)continue;dG.push({m:fr,f:cmp(fr,tgt)});}
    dOver=s.over||false;
    if(mode==='daily'){dG.forEach(x=>{mkRow(x.m,x.f,tgt);mkCard(x.m,x.f,tgt);});updDots();if(dOver)showDRes(s.won);}
  }catch(e){}
}
function updDots(){
  const r=$('dots');r.innerHTML='';
  for(let i=0;i<MAX;i++){
    const d=document.createElement('div');d.className='dot';
    if(i<dG.length){const w=dG[i].m.n===tgt.n;d.classList.add(w?'win':(dOver&&i===dG.length-1?'lose':'used'));}
    r.appendChild(d);
  }
  $('cnt').innerHTML='<span>'+dG.length+'/'+MAX+'</span>';
}
function showDRes(won){
  const b=$('rb');b.classList.add('on',won?'win':'lose');
  $('rttl').textContent=won?'⚔ BIEN JOUÉ !':'💀 ÉCHEC';
  $('rchar').textContent='Personnage : '+tgt.n;
  $('rdesc').textContent=won?tgt.n+' trouvé en '+dG.length+' essai'+(dG.length>1?'s':'')+'.'
    :tgt.n+' · '+tgt.r+' · '+tgt.st+' · Cheveux : '+tgt.hc+' · '+tgt.w+'V/'+tgt.l+'D · '+tgt.bday;
  $('gi').disabled=true;$('gbtn').disabled=true;
  tick();setInterval(tick,1000);
}
function tick(){
  const now=new Date(),tom=new Date(now);tom.setDate(tom.getDate()+1);tom.setHours(0,0,0,0);
  const d=tom-now;
  $('nt').textContent=String(Math.floor(d/3600000)).padStart(2,'0')+':'+String(Math.floor((d%3600000)/60000)).padStart(2,'0')+':'+String(Math.floor((d%60000)/1000)).padStart(2,'0');
}
function share(){
  let t='Bleach Character Guesser '+todayKey()+'\n'+dG.length+'/'+MAX+'\n\n';
  dG.forEach(x=>{t+=x.f.map(f=>f.s==='correct'?'🟩':f.s==='close'?'🟨':'🟥').join('')+'\n';});
  t+='\n🎮 Jouer sur https://kevinraphael95.github.io/discord_bot_kisuke_urahara/guesser.html';
  try{navigator.clipboard.writeText(t);}catch(e){}
  const b=document.querySelector('.xbtn');b.textContent='✓ Copié !';setTimeout(()=>b.textContent='📋 Copier le résultat',2000);
}

function loadRec(){try{const s=JSON.parse(localStorage.getItem('bleachg_surv'));if(s)sRec=s.best||0;}catch(e){}}
function saveRec(){try{localStorage.setItem('bleachg_surv',JSON.stringify({best:sRec}));}catch(e){}}
function rndQ(){const a=CHARS.slice();for(let i=a.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[a[i],a[j]]=[a[j],a[i]];}return a;}
function sInit(){sStr=0;sBst=0;sKil=0;sQ=rndQ();sQi=0;sOver=false;$('send').classList.remove('on');sNext();}
function sNext(){if(sQi>=sQ.length){sQ=rndQ();sQi=0;}sCur=sQ[sQi++];sG=[];clr();$('flash').classList.remove('on');$('gi').disabled=false;$('gbtn').disabled=false;foc();updSUI();}
function updSUI(){
  $('sstreak').textContent=sStr;$('sbest').textContent=sRec;
  const el=$('sdots');el.innerHTML='';
  for(let i=0;i<MAX;i++){const d=document.createElement('div');d.className='sdot';if(i<sG.length)d.classList.add(sG[i]&&sG[i].m.n===sCur.n?'win':'used');el.appendChild(d);}
}
function showFlash(type,msg){
  const f=$('flash');f.className='flash on '+(type==='ok'?'ok':'ko');f.textContent=msg;
  clearTimeout(f._t);f._t=setTimeout(()=>f.classList.remove('on'),2500);
}
function sGameOver(name){
  sOver=true;if(sStr>sRec){sRec=sStr;saveRec();}
  showFlash('ko','☠ '+name+' — Game Over !');
  $('gi').disabled=true;$('gbtn').disabled=true;
  setTimeout(()=>showSEnd(),1500);
}
function sCorrect(){
  sKil++;sStr++;if(sStr>sBst)sBst=sStr;if(sStr>sRec){sRec=sStr;saveRec();}
  showFlash('ok','✓ '+sCur.n+' trouvé'+(sStr>=3?' 🔥 ×'+sStr:''));
  $('gi').disabled=true;$('gbtn').disabled=true;updSUI();
  setTimeout(()=>sNext(),1900);
}
function showSEnd(){
  clr();$('send').classList.add('on');
  $('sedesc').innerHTML='Série de <em>'+sStr+'</em> — '+sKil+' personnage'+(sKil>1?'s':'')+'.';
  $('sek').textContent=sKil;$('seb').textContent=sBst;$('ser').textContent=sRec;
  $('gi').disabled=true;$('gbtn').disabled=true;updSUI();
}
function sRestart(){sInit();}
function sShare(){
  const t='Bleach Character Guesser — Survie\nSérie : '+sStr+'\nTrouvés : '+sKil+'\nRecord : '+sRec+'\n\n🎮 Jouer sur https://kevinraphael95.github.io/discord_bot_kisuke_urahara/guesser.html';
  try{navigator.clipboard.writeText(t);}catch(e){}
  const b=document.querySelector('.xbtn2');b.textContent='✓ Copié !';setTimeout(()=>b.textContent='📋 Copier le score',2000);
}

function sub(){mode==='daily'?subD():subS();}
function subD(){
  if(dOver)return;
  const inp=$('gi');const v=inp.value.trim();if(!v)return;
  const m=CHARS.find(x=>x.n.toLowerCase()===v.toLowerCase());
  if(!m){shake(inp,'Introuvable…');return;}
  if(dG.find(x=>x.m.n===m.n)){shake(inp,'Déjà essayé !');return;}
  const f=cmp(m,tgt);dG.push({m,f});
  mkRow(m,f,tgt);mkCard(m,f,tgt);updDots();
  inp.value='';$('acl').innerHTML='';
  const won=m.n===tgt.n;
  if(won||dG.length>=MAX){dOver=true;saveD(won);setTimeout(()=>showDRes(won),400);}else saveD(false);
}
function subS(){
  if(sOver||!sCur)return;
  const inp=$('gi');const v=inp.value.trim();if(!v)return;
  const m=CHARS.find(x=>x.n.toLowerCase()===v.toLowerCase());
  if(!m){shake(inp,'Introuvable…');return;}
  if(sG.find(x=>x.m.n===m.n)){shake(inp,'Déjà essayé !');return;}
  const f=cmp(m,sCur);sG.push({m,f});
  mkRow(m,f,sCur);mkCard(m,f,sCur);
  inp.value='';$('acl').innerHTML='';updSUI();
  if(m.n===sCur.n)sCorrect();
  else if(sG.length>=MAX)sGameOver(sCur.n);
}
function shake(inp,msg){
  inp.style.borderColor='var(--ko-bd)';inp.placeholder=msg;
  inp.animate([{transform:'translateX(-4px)'},{transform:'translateX(4px)'},{transform:'translateX(0)'}],{duration:240});
  setTimeout(()=>{inp.style.borderColor='';inp.placeholder='Entrez un personnage Bleach…';},1500);
}

function onIn(){
  const v=$('gi').value.toLowerCase().trim();
  const l=$('acl');l.innerHTML='';
  if(mode==='daily')dSel=-1;else sSel=-1;
  if(!v)return;
  const done=new Set((mode==='daily'?dG:sG).map(x=>x.m.n));
  CHARS.filter(x=>x.n.toLowerCase().includes(v)&&!done.has(x.n)).slice(0,8).forEach(x=>{
    const i=document.createElement('div');i.className='aci';
    i.innerHTML=x.n+'<span class="acb">'+x.r+' · '+x.st+'</span>';
    i.onclick=()=>{$('gi').value=x.n;l.innerHTML='';sub();};l.appendChild(i);
  });

  // ── EASTER EGGS — détection à la frappe ──────────
  if(v==='gay') triggerGay();

  if(v==='fromage') triggerFromage();
  
}
function onKD(e){
  const l=$('acl');const items=l.querySelectorAll('.aci');
  let sel=mode==='daily'?dSel:sSel;
  if(!items.length) return;
  if(e.key==='ArrowDown'){e.preventDefault();sel=Math.min(sel+1,items.length-1);items.forEach((x,i)=>x.classList.toggle('sel',i===sel));if(items[sel]){$('gi').value=items[sel].firstChild.textContent.trim();items[sel].scrollIntoView({block:"nearest", behavior:"smooth"});}}
  else if(e.key==='ArrowUp'){e.preventDefault();sel=Math.max(sel-1,-1);items.forEach((x,i)=>x.classList.toggle('sel',i===sel));if(sel>=0&&items[sel]){$('gi').value=items[sel].firstChild.textContent.trim();items[sel].scrollIntoView({block:"nearest", behavior:"smooth"});}}
  else if(e.key==='Enter'){e.preventDefault();l.innerHTML='';sub();}
  else if(e.key==='Escape')l.innerHTML='';
  if(mode==='daily')dSel=sel;else sSel=sel;
}
document.addEventListener('click',e=>{if(!e.target.closest('.acw'))$('acl').innerHTML='';});
function toggleHelp(){$('hpanel').classList.toggle('on');}


// ── KONAMI CODE EASTER EGG ────────────────────────────
(function(){
  const KONAMI = ['ArrowUp','ArrowUp','ArrowDown','ArrowDown','ArrowLeft','ArrowRight','ArrowLeft','ArrowRight'];
  const API = 'https://api.github.com/repos/kevinraphael95/bleachmusics/contents/';
  const BASE = 'https://raw.githubusercontent.com/kevinraphael95/bleachmusics/main/';

  let buf = [];
  let player = null;
  let toast = null;
  let tracks = [];

  document.addEventListener('keydown', function(e){
    if(e.target === $('gi')) return;
    buf.push(e.key);
    if(buf.length > KONAMI.length) buf.shift();
    if(buf.join(',') === KONAMI.join(',')){
      buf = [];
      triggerKonami();
    }
  });

  async function triggerKonami(){
    if(tracks.length === 0){
      try {
        const res = await fetch(API);
        const files = await res.json();
        tracks = files
          .filter(f => f.name.endsWith('.mp3'))
          .map(f => f.name);
      } catch(e){
        tracks = [];
      }
    }

    if(tracks.length === 0) return;

    const name = tracks[Math.floor(Math.random() * tracks.length)];
    const url = BASE + encodeURIComponent(name);

    if(player){
      player.pause();
      player.currentTime = 0;
    }

    player = new Audio(url);
    player.volume = 0.10;
    player.loop = false;
    player.play().catch(()=>{});

    showToast(name.replace('.mp3',''), player);
  }

  function showToast(title, audio){
    if(toast) toast.remove();
    toast = document.createElement('div');
    toast.style.cssText = `
      position:fixed; bottom:1.5rem; right:1.5rem;
      background:var(--panel); border:1px solid var(--gold-line);
      padding:.85rem 1.1rem; z-index:9999;
      box-shadow:0 0 32px var(--gold-glow);
      animation:rise .4s ease forwards;
      display:flex; flex-direction:column; gap:.5rem;
      min-width:220px; max-width:280px;
      font-family:'DM Sans',sans-serif;
    `;
    toast.innerHTML = `
      <div style="font-size:.6rem;letter-spacing:.2em;color:var(--gold);text-transform:uppercase;font-weight:600">⚡ Easter Egg</div>
      <div style="font-size:.8rem;color:var(--white);line-height:1.3">${title}</div>
      <div style="display:flex;gap:.5rem;align-items:center">
        <input type="range" min="0" max="1" step="0.05" value="0.10"
          style="flex:1;accent-color:var(--gold);cursor:pointer">
        <button class="konami-stop"
          style="background:none;border:1px solid var(--border);color:var(--muted);
                 cursor:pointer;font-size:.7rem;padding:.2rem .5rem;border-radius:2px">
          ■ Stop
        </button>
      </div>
    `;

    toast.querySelector('input[type=range]').addEventListener('input', function(){
      audio.volume = this.value;
    });

    toast.querySelector('.konami-stop').addEventListener('click', function(){
      audio.pause();
      audio.currentTime = 0;
      toast.remove();
      toast = null;
      player = null;
    });

    document.body.appendChild(toast);
  }
})();



// ── FROMAGE EASTER EGG ────────────────────────────────
(function(){
  const DURATION    = 13000;
  const EMOJI_COUNT = 22;
  const EMOJIS      = ['🧀','🫕','🧀','🫙','🧀','🥐','🧀'];

  let running = false;
  let timers  = [];

  function injectStyles(){
    if(document.getElementById('fromage-style')) return;
    const st = document.createElement('style');
    st.id = 'fromage-style';
    st.textContent = `
      @keyframes fromageFly {
        0%   { transform: translateX(-80px) translateY(var(--fy)) rotate(var(--fr)) scale(.8); opacity:0; }
        7%   { opacity:1; }
        90%  { opacity:1; }
        100% { transform: translateX(calc(100vw + 80px)) translateY(var(--fy)) rotate(var(--fr)) scale(1.1); opacity:0; }
      }
      .fromage-emoji {
        position:fixed; top:0; left:0; z-index:8888;
        pointer-events:none; font-size:2.4rem; line-height:1;
        filter: drop-shadow(0 2px 6px rgba(0,0,0,.5));
        animation: fromageFly var(--fd) linear forwards;
      }
    `;
    document.head.appendChild(st);
  }

  window.triggerFromage = function(){
    if(running) return;
    running = true;
    injectStyles();

    for(let i = 0; i < EMOJI_COUNT; i++){
      const delay = (DURATION * 0.85 / EMOJI_COUNT) * i;
      const t = setTimeout(()=>{
        const el = document.createElement('div');
        el.className = 'fromage-emoji';
        el.textContent = EMOJIS[Math.floor(Math.random() * EMOJIS.length)];
        const yPct = 3  + Math.random() * 82;
        const rot  = -20 + Math.random() * 40;
        const dur  = 2600 + Math.random() * 2400;
        el.style.setProperty('--fy', yPct + 'vh');
        el.style.setProperty('--fr', rot  + 'deg');
        el.style.setProperty('--fd', dur  + 'ms');
        document.body.appendChild(el);
        setTimeout(()=>el.remove(), dur + 200);
      }, delay);
      timers.push(t);
    }

    const endT = setTimeout(()=>{ timers = []; running = false; }, DURATION + 600);
    timers.push(endT);
  };
})();




// ── GAY PRIDE EASTER EGG ──────────────────────────────
(function(){
  const DURATION   = 13000; // durée totale de l'animation (ms)
  const FLAG_COUNT = 18;    // nombre de drapeaux qui traversent l'écran

  // Drapeau arc-en-ciel 6 bandes en SVG inline
  const FLAG_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 72 44" width="72" height="44">
    <rect y="0"  width="72" height="7.3" fill="#FF0018"/>
    <rect y="7.3"  width="72" height="7.3" fill="#FFA52C"/>
    <rect y="14.6" width="72" height="7.3" fill="#FFFF41"/>
    <rect y="21.9" width="72" height="7.3" fill="#008018"/>
    <rect y="29.2" width="72" height="7.3" fill="#0000F9"/>
    <rect y="36.5" width="72" height="7.5" fill="#86007D"/>
  </svg>`;

  let running = false;
  let timers  = [];

  // Injecte les keyframes une seule fois
  function injectStyles(){
    if(document.getElementById('gay-pride-style')) return;
    const st = document.createElement('style');
    st.id = 'gay-pride-style';
    st.textContent = `
      @keyframes gayFly {
        0%   { transform: translateX(-100px) translateY(var(--gy)) rotate(var(--gr)) scale(.9); opacity:0; }
        6%   { opacity:1; }
        92%  { opacity:1; }
        100% { transform: translateX(calc(100vw + 100px)) translateY(var(--gy)) rotate(var(--gr)) scale(1.08); opacity:0; }
      }
      @keyframes gayOverlay {
        0%,8% { opacity:0; } 20% { opacity:1; } 80% { opacity:1; } 100% { opacity:0; }
      }
      .gay-flag {
        position:fixed; top:0; left:0; z-index:8888;
        pointer-events:none; will-change:transform;
        filter: drop-shadow(0 3px 10px rgba(0,0,0,.5));
        animation: gayFly var(--gd) linear forwards;
      }
      .gay-overlay {
        position:fixed; inset:0; z-index:8887; pointer-events:none;
        background: linear-gradient(135deg,
          rgba(255,0,24,.06) 0%, rgba(255,165,44,.06) 17%,
          rgba(255,255,65,.06) 33%, rgba(0,128,24,.06) 50%,
          rgba(0,0,249,.06) 67%, rgba(134,0,125,.06) 100%);
        animation: gayOverlay var(--gTotal) linear forwards;
      }
    `;
    document.head.appendChild(st);
  }

  window.triggerGay = function(){
    if(running) return;
    running = true;
    injectStyles();

    // Overlay de teinte arc-en-ciel léger
    const overlay = document.createElement('div');
    overlay.className = 'gay-overlay';
    overlay.style.setProperty('--gTotal', DURATION + 'ms');
    document.body.appendChild(overlay);

    // Spawne les drapeaux de façon échelonnée
    for(let i = 0; i < FLAG_COUNT; i++){
      const delay = (DURATION * 0.85 / FLAG_COUNT) * i;
      const t = setTimeout(()=>{
        const flag = document.createElement('div');
        flag.className = 'gay-flag';
        const yPct = 3 + Math.random() * 82;           // hauteur aléatoire
        const rot  = -12 + Math.random() * 24;          // rotation légère
        const dur  = 2800 + Math.random() * 2200;       // vitesse variable
        flag.style.setProperty('--gy', yPct + 'vh');
        flag.style.setProperty('--gr', rot + 'deg');
        flag.style.setProperty('--gd', dur + 'ms');
        flag.innerHTML = FLAG_SVG;
        document.body.appendChild(flag);
        setTimeout(()=>flag.remove(), dur + 200);
      }, delay);
      timers.push(t);
    }

    // Nettoyage final
    const endT = setTimeout(()=>{
      overlay.remove();
      timers = [];
      running = false;
    }, DURATION + 600);
    timers.push(endT);
  };
})();


// ── INIT ────────────────────────────
loadRec();
updDots();
loadD();
if(!dOver) foc();
