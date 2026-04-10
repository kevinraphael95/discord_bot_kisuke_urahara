// data.js — Bleach Guessr
// Organisé par catégories, à jour après la Thousand-Year Blood War
const CHARS = [

  // ============================================================
  // PROTAGONISTES & KARAKURA
  // ============================================================
  {n:"Ichigo Kurosaki",       r:"Humain",   sx:"M", arc:"Agent of Shinigami",       af:"Karakura",    d:5, st:"Vivant",    hc:"Orange", bday:"15/07", w:28, l:6,  draw:2},
  {n:"Orihime Inoue",         r:"Humain",   sx:"F", arc:"Agent of Shinigami",       af:"Karakura",    d:2, st:"Vivant",    hc:"Roux",   bday:"03/09", w:2,  l:5,  draw:1},
  {n:"Yasutora Sado",         r:"Humain",   sx:"M", arc:"Agent of Shinigami",       af:"Karakura",    d:3, st:"Vivant",    hc:"Noir",   bday:"07/04", w:6,  l:4,  draw:0},
  {n:"Uryuu Ishida",          r:"Quincy",   sx:"M", arc:"Agent of Shinigami",       af:"Karakura",    d:4, st:"Vivant",    hc:"Noir",   bday:"06/11", w:8,  l:4,  draw:1},
  {n:"Isshin Kurosaki",       r:"Shinigami",sx:"M", arc:"Agent of Shinigami",       af:"Karakura",    d:5, st:"Vivant",    hc:"Noir",   bday:"10/12", w:5,  l:1,  draw:0},
  {n:"Kon",                   r:"Mod-Soul", sx:"M", arc:"Agent of Shinigami",       af:"Karakura",    d:1, st:"Vivant",    hc:"Blond",  bday:"??/??", w:1,  l:3,  draw:0},
  {n:"Ganju Shiba",           r:"Humain",   sx:"M", arc:"Soul Society",             af:"Indépendant", d:2, st:"Vivant",    hc:"Noir",   bday:"02/11", w:2,  l:2,  draw:0},
  {n:"Kukaku Shiba",          r:"Humain",   sx:"F", arc:"Soul Society",             af:"Indépendant", d:3, st:"Vivant",    hc:"Noir",   bday:"01/09", w:1,  l:0,  draw:0},

  // ============================================================
  // URAHARA SHOTEN
  // ============================================================
  {n:"Kisuke Urahara",        r:"Shinigami",sx:"M", arc:"Agent of Shinigami",       af:"Indépendant", d:5, st:"Vivant",    hc:"Blond",  bday:"31/12", w:10, l:1,  draw:1},
  {n:"Yoruichi Shihoin",      r:"Shinigami",sx:"F", arc:"Agent of Shinigami",       af:"Indépendant", d:5, st:"Vivant",    hc:"Violet", bday:"01/01", w:8,  l:1,  draw:0},
  {n:"Tessai Tsukabishi",     r:"Shinigami",sx:"M", arc:"Agent of Shinigami",       af:"Indépendant", d:4, st:"Vivant",    hc:"Noir",   bday:"??/??", w:2,  l:0,  draw:0},
  {n:"Jinta Hanakari",        r:"Humain",   sx:"M", arc:"Agent of Shinigami",       af:"Indépendant", d:1, st:"Vivant",    hc:"Rouge",  bday:"??/??", w:0,  l:1,  draw:0},
  {n:"Ururu Tsumugiya",       r:"Humain",   sx:"F", arc:"Agent of Shinigami",       af:"Indépendant", d:2, st:"Vivant",    hc:"Noir",   bday:"??/??", w:1,  l:1,  draw:0},

  // ============================================================
  // GOTEI 13 — CAPITAINES (postes finaux après TYBW)
  // Div 1 Kyoraku | 2 Soi Fon | 3 Rose | 4 Isane | 5 Shinji
  // Div 6 Byakuya | 8 Lisa | 9 Kensei | 10 Hitsugaya
  // Div 11 Zaraki | 12 Mayuri | 13 Rukia
  // (Div 7 : Iba Tetsuzaemon — hors scope)
  // ============================================================
  {n:"Shunsui Kyoraku",       r:"Shinigami",sx:"M", arc:"Soul Society",             af:"Gotei 13",    d:5, st:"Vivant",    hc:"Brun",   bday:"11/07", w:6,  l:1,  draw:1}, // Cap-Commandant Div 1
  {n:"Soi Fon",               r:"Shinigami",sx:"F", arc:"Soul Society",             af:"Gotei 13",    d:4, st:"Vivant",    hc:"Noir",   bday:"11/02", w:5,  l:2,  draw:1}, // Cap Div 2
  {n:"Rose Otoribashi",       r:"Vizard",   sx:"M", arc:"Fake Karakura",            af:"Gotei 13",    d:4, st:"Vivant",    hc:"Blond",  bday:"16/01", w:2,  l:2,  draw:0}, // Cap Div 3 (remplace Gin)
  {n:"Isane Kotetsu",         r:"Shinigami",sx:"F", arc:"Soul Society",             af:"Gotei 13",    d:3, st:"Vivant",    hc:"Gris",   bday:"08/08", w:1,  l:1,  draw:0}, // Cap Div 4 (remplace Unohana)
  {n:"Shinji Hirako",         r:"Vizard",   sx:"M", arc:"Arrancar",                 af:"Gotei 13",    d:4, st:"Vivant",    hc:"Blond",  bday:"15/05", w:3,  l:2,  draw:0}, // Cap Div 5 (remplace Aizen)
  {n:"Byakuya Kuchiki",       r:"Shinigami",sx:"M", arc:"Soul Society",             af:"Gotei 13",    d:5, st:"Vivant",    hc:"Noir",   bday:"31/01", w:8,  l:3,  draw:0}, // Cap Div 6
  {n:"Lisa Yadomaru",         r:"Vizard",   sx:"F", arc:"Fake Karakura",            af:"Gotei 13",    d:4, st:"Vivant",    hc:"Noir",   bday:"03/07", w:2,  l:2,  draw:0}, // Cap Div 8 (remplace Kyoraku)
  {n:"Kensei Muguruma",       r:"Vizard",   sx:"M", arc:"Fake Karakura",            af:"Gotei 13",    d:4, st:"Vivant",    hc:"Gris",   bday:"30/07", w:3,  l:2,  draw:0}, // Cap Div 9 (remplace Tousen)
  {n:"Toshiro Hitsugaya",     r:"Shinigami",sx:"M", arc:"Soul Society",             af:"Gotei 13",    d:5, st:"Vivant",    hc:"Blanc",  bday:"20/12", w:7,  l:3,  draw:0}, // Cap Div 10
  {n:"Kenpachi Zaraki",       r:"Shinigami",sx:"M", arc:"Soul Society",             af:"Gotei 13",    d:5, st:"Vivant",    hc:"Noir",   bday:"19/11", w:9,  l:2,  draw:1}, // Cap Div 11
  {n:"Mayuri Kurotsuchi",     r:"Shinigami",sx:"M", arc:"Soul Society",             af:"Gotei 13",    d:4, st:"Vivant",    hc:"Noir",   bday:"30/03", w:6,  l:1,  draw:0}, // Cap Div 12
  {n:"Rukia Kuchiki",         r:"Shinigami",sx:"F", arc:"Agent of Shinigami",       af:"Gotei 13",    d:4, st:"Vivant",    hc:"Noir",   bday:"14/01", w:9,  l:3,  draw:0}, // Cap Div 13 (remplace Ukitake)

  // ============================================================
  // GOTEI 13 — ANCIENS CAPITAINES
  // ============================================================
  {n:"Genryusai Yamamoto",    r:"Shinigami",sx:"M", arc:"Soul Society",             af:"Gotei 13",    d:5, st:"Mort",      hc:"Blanc",  bday:"21/01", w:5,  l:1,  draw:0}, // Cap Div 1 — tué par Yhwach
  {n:"Retsu Unohana",         r:"Shinigami",sx:"F", arc:"Soul Society",             af:"Gotei 13",    d:5, st:"Mort",      hc:"Noir",   bday:"21/04", w:3,  l:1,  draw:0}, // Cap Div 4 — tuée par Zaraki
  {n:"Sosuke Aizen",          r:"Shinigami",sx:"M", arc:"Soul Society",             af:"Gotei 13",    d:5, st:"Vivant",    hc:"Brun",   bday:"29/05", w:12, l:1,  draw:0}, // Cap Div 5 — emprisonné
  {n:"Sajin Komamura",        r:"Shinigami",sx:"M", arc:"Soul Society",             af:"Gotei 13",    d:4, st:"Incertain", hc:"Roux",   bday:"23/08", w:4,  l:3,  draw:0}, // Cap Div 7 — redevenu mortel
  {n:"Kaname Tousen",         r:"Shinigami",sx:"M", arc:"Soul Society",             af:"Gotei 13",    d:4, st:"Mort",      hc:"Noir",   bday:"13/10", w:3,  l:2,  draw:0}, // Cap Div 9 — tué par Hisagi
  {n:"Gin Ichimaru",          r:"Shinigami",sx:"M", arc:"Soul Society",             af:"Gotei 13",    d:5, st:"Mort",      hc:"Argent", bday:"10/09", w:4,  l:1,  draw:0}, // Cap Div 3 — tué par Aizen
  {n:"Jushiro Ukitake",       r:"Shinigami",sx:"M", arc:"Soul Society",             af:"Gotei 13",    d:4, st:"Mort",      hc:"Blanc",  bday:"21/12", w:2,  l:1,  draw:1}, // Cap Div 13 — mort au TYBW
  {n:"Ginrei Kuchiki",        r:"Shinigami",sx:"M", arc:"Soul Society",             af:"Gotei 13",    d:4, st:"Mort",      hc:"Blanc",  bday:"??/??", w:1,  l:0,  draw:0}, // Ancien cap Div 6

  // ============================================================
  // GOTEI 13 — VICE-CAPITAINES
  // ============================================================
  {n:"Chojiro Sasakibe",      r:"Shinigami",sx:"M", arc:"Soul Society",             af:"Gotei 13",    d:3, st:"Mort",      hc:"Brun",   bday:"04/11", w:0,  l:1,  draw:0}, // Vice-cap Div 1 — tué au TYBW
  {n:"Marenoshin Omaeda",     r:"Shinigami",sx:"M", arc:"Soul Society",             af:"Gotei 13",    d:2, st:"Vivant",    hc:"Noir",   bday:"05/05", w:1,  l:2,  draw:0}, // Vice-cap Div 2
  {n:"Izuru Kira",            r:"Shinigami",sx:"M", arc:"Soul Society",             af:"Gotei 13",    d:3, st:"Incertain", hc:"Blond",  bday:"27/03", w:3,  l:3,  draw:0}, // Vice-cap Div 3 — état incertain après TYBW
  {n:"Momo Hinamori",         r:"Shinigami",sx:"F", arc:"Soul Society",             af:"Gotei 13",    d:3, st:"Vivant",    hc:"Brun",   bday:"03/06", w:2,  l:3,  draw:0}, // Vice-cap Div 5
  {n:"Renji Abarai",          r:"Shinigami",sx:"M", arc:"Soul Society",             af:"Gotei 13",    d:4, st:"Vivant",    hc:"Rouge",  bday:"31/08", w:7,  l:5,  draw:0}, // Vice-cap Div 6
  {n:"Nanao Ise",             r:"Shinigami",sx:"F", arc:"Soul Society",             af:"Gotei 13",    d:3, st:"Vivant",    hc:"Noir",   bday:"07/07", w:2,  l:1,  draw:0}, // Vice-cap Div 8
  {n:"Shuhei Hisagi",         r:"Shinigami",sx:"M", arc:"Soul Society",             af:"Gotei 13",    d:3, st:"Vivant",    hc:"Noir",   bday:"14/08", w:3,  l:3,  draw:0}, // Vice-cap Div 9
  {n:"Rangiku Matsumoto",     r:"Shinigami",sx:"F", arc:"Soul Society",             af:"Gotei 13",    d:3, st:"Vivant",    hc:"Blond",  bday:"29/09", w:3,  l:3,  draw:0}, // Vice-cap Div 10
  {n:"Yachiru Kusajishi",     r:"Shinigami",sx:"F", arc:"Soul Society",             af:"Gotei 13",    d:4, st:"Incertain", hc:"Rose",   bday:"12/02", w:2,  l:0,  draw:1}, // Vice-cap Div 11 — disparaît (esprit zanpakuto)
  {n:"Nemu Kurotsuchi",       r:"Mod-Soul", sx:"F", arc:"Soul Society",             af:"Gotei 13",    d:3, st:"Mort",      hc:"Noir",   bday:"30/03", w:2,  l:2,  draw:0}, // Vice-cap Div 12 — morte au TYBW

  // ============================================================
  // GOTEI 13 — AUTRES MEMBRES NOTABLES
  // ============================================================
  {n:"Ikkaku Madarame",       r:"Shinigami",sx:"M", arc:"Soul Society",             af:"Gotei 13",    d:3, st:"Vivant",    hc:"Chauve", bday:"08/11", w:4,  l:3,  draw:0},
  {n:"Yumichika Ayasegawa",   r:"Shinigami",sx:"M", arc:"Soul Society",             af:"Gotei 13",    d:3, st:"Vivant",    hc:"Noir",   bday:"19/09", w:3,  l:1,  draw:0},
  {n:"Hanataro Yamada",       r:"Shinigami",sx:"M", arc:"Soul Society",             af:"Gotei 13",    d:1, st:"Vivant",    hc:"Noir",   bday:"01/04", w:1,  l:1,  draw:0},

  // ============================================================
  // VIZARDS (non promus capitaines à la fin)
  // ============================================================
  {n:"Hiyori Sarugaki",       r:"Vizard",   sx:"F", arc:"Arrancar",                 af:"Indépendant", d:3, st:"Vivant",    hc:"Blond",  bday:"08/08", w:2,  l:2,  draw:0},
  {n:"Love Aikawa",           r:"Vizard",   sx:"M", arc:"Fake Karakura",            af:"Gotei 13",    d:4, st:"Vivant",    hc:"Noir",   bday:"21/06", w:2,  l:2,  draw:0},
  {n:"Mashiro Kuna",          r:"Vizard",   sx:"F", arc:"Fake Karakura",            af:"Indépendant", d:3, st:"Vivant",    hc:"Vert",   bday:"28/05", w:2,  l:1,  draw:0},
  {n:"Hachigen Ushoda",       r:"Vizard",   sx:"M", arc:"Fake Karakura",            af:"Indépendant", d:4, st:"Vivant",    hc:"Rose",   bday:"??/??", w:2,  l:1,  draw:0},

  // ============================================================
  // ESPADA (par numéro tatoué : 1 → 10)
  // ============================================================
  {n:"Coyote Starrk",         r:"Arrancar", sx:"M", arc:"Arrancar",                 af:"Espada",      d:5, st:"Mort",      hc:"Brun",   bday:"??/??", w:4,  l:1,  draw:0}, // Espada 1
  {n:"Baraggan Louisenbairn", r:"Arrancar", sx:"M", arc:"Fake Karakura",            af:"Espada",      d:5, st:"Mort",      hc:"Chauve", bday:"??/??", w:3,  l:1,  draw:0}, // Espada 2
  {n:"Tier Harribel",         r:"Arrancar", sx:"F", arc:"Fake Karakura",            af:"Espada",      d:5, st:"Vivant",    hc:"Blond",  bday:"??/??", w:3,  l:1,  draw:0}, // Espada 3
  {n:"Ulquiorra Cifer",       r:"Arrancar", sx:"M", arc:"Arrancar",                 af:"Espada",      d:5, st:"Mort",      hc:"Noir",   bday:"??/??", w:5,  l:1,  draw:0}, // Espada 4
  {n:"Nnoitra Gilga",         r:"Arrancar", sx:"M", arc:"Hueco Mundo",              af:"Espada",      d:5, st:"Mort",      hc:"Noir",   bday:"??/??", w:4,  l:1,  draw:0}, // Espada 5
  {n:"Grimmjow Jaegerjaquez", r:"Arrancar", sx:"M", arc:"Arrancar",                 af:"Espada",      d:5, st:"Vivant",    hc:"Bleu",   bday:"??/??", w:4,  l:2,  draw:0}, // Espada 6
  {n:"Zommari Rureaux",       r:"Arrancar", sx:"M", arc:"Hueco Mundo",              af:"Espada",      d:4, st:"Mort",      hc:"Chauve", bday:"??/??", w:2,  l:1,  draw:0}, // Espada 7
  {n:"Szayelaporro Grantz",   r:"Arrancar", sx:"M", arc:"Hueco Mundo",              af:"Espada",      d:4, st:"Mort",      hc:"Rose",   bday:"??/??", w:3,  l:1,  draw:0}, // Espada 8
  {n:"Aaroniero Arruruerie",  r:"Arrancar", sx:"M", arc:"Hueco Mundo",              af:"Espada",      d:4, st:"Mort",      hc:"Noir",   bday:"??/??", w:2,  l:1,  draw:0}, // Espada 9
  {n:"Yammy Llargo",          r:"Arrancar", sx:"M", arc:"Arrancar",                 af:"Espada",      d:5, st:"Mort",      hc:"Noir",   bday:"??/??", w:3,  l:1,  draw:0}, // Espada 10 (0 en Resurreccion)

  // ============================================================
  // EX-ESPADA & ARRANCAR NOTABLES
  // ============================================================
  {n:"Nelliel Tu Odelschwanck",r:"Arrancar",sx:"F", arc:"Hueco Mundo",              af:"Hueco Mundo", d:5, st:"Vivant",    hc:"Vert",   bday:"??/??", w:4,  l:1,  draw:0}, // Ex-Espada 3
  {n:"Luppi Antenor",         r:"Arrancar", sx:"M", arc:"Arrancar",                 af:"Espada",      d:3, st:"Mort",      hc:"Noir",   bday:"??/??", w:1,  l:1,  draw:0}, // Espada 6 provisoire
  {n:"Wonderweiss Margela",   r:"Arrancar", sx:"M", arc:"Fake Karakura",            af:"Espada",      d:4, st:"Mort",      hc:"Blond",  bday:"??/??", w:2,  l:1,  draw:0},

  // ============================================================
  // FRACCIÓN DE HARRIBEL (Espada 3)
  // ============================================================
  {n:"Franceska Mila Rose",   r:"Arrancar", sx:"F", arc:"Arrancar",                 af:"Espada",      d:3, st:"Vivant",    hc:"Noir",   bday:"??/??", w:1,  l:1,  draw:0},
  {n:"Apache",                r:"Arrancar", sx:"F", arc:"Arrancar",                 af:"Espada",      d:3, st:"Vivant",    hc:"Noir",   bday:"??/??", w:1,  l:1,  draw:0},
  {n:"Sun-Sun",               r:"Arrancar", sx:"F", arc:"Arrancar",                 af:"Espada",      d:3, st:"Vivant",    hc:"Vert",   bday:"??/??", w:1,  l:1,  draw:0},

  // ============================================================
  // ARRANCAR DIVERS (Números, Privaron Espada, autres)
  // ============================================================
  {n:"Loly Aivirrne",         r:"Arrancar", sx:"F", arc:"Arrancar",                 af:"Espada",      d:2, st:"Vivant",    hc:"Noir",   bday:"??/??", w:0,  l:2,  draw:0},
  {n:"Menoly Mallia",         r:"Arrancar", sx:"F", arc:"Arrancar",                 af:"Espada",      d:2, st:"Incertain", hc:"Blond",  bday:"??/??", w:0,  l:2,  draw:0},
  {n:"Shawlong Koufang",      r:"Arrancar", sx:"M", arc:"Arrancar",                 af:"Espada",      d:3, st:"Mort",      hc:"Bleu",   bday:"??/??", w:1,  l:1,  draw:0},
  {n:"Findorr Calius",        r:"Arrancar", sx:"M", arc:"Fake Karakura",            af:"Espada",      d:3, st:"Mort",      hc:"Blond",  bday:"??/??", w:1,  l:1,  draw:0},
  {n:"Charlotte Cuuhlhourne", r:"Arrancar", sx:"M", arc:"Fake Karakura",            af:"Espada",      d:3, st:"Mort",      hc:"Blond",  bday:"??/??", w:1,  l:1,  draw:0},
  {n:"Dordoni Alessandro",    r:"Arrancar", sx:"M", arc:"Hueco Mundo",              af:"Hueco Mundo", d:3, st:"Mort",      hc:"Brun",   bday:"??/??", w:2,  l:2,  draw:0}, // Privaron Espada
  {n:"Cirucci Sanderwicci",   r:"Arrancar", sx:"F", arc:"Hueco Mundo",              af:"Hueco Mundo", d:3, st:"Mort",      hc:"Violet", bday:"??/??", w:1,  l:1,  draw:0}, // Privaron Espada
  {n:"Gantenbainne Mosqueda", r:"Arrancar", sx:"M", arc:"Hueco Mundo",              af:"Hueco Mundo", d:3, st:"Mort",      hc:"Blanc",  bday:"??/??", w:1,  l:1,  draw:0}, // Privaron Espada
  {n:"Pesche Guatiche",       r:"Arrancar", sx:"M", arc:"Hueco Mundo",              af:"Hueco Mundo", d:2, st:"Vivant",    hc:"Chauve", bday:"??/??", w:0,  l:1,  draw:0}, // Compagnon de Nel
  {n:"Dondochakka Birstanne", r:"Arrancar", sx:"M", arc:"Hueco Mundo",              af:"Hueco Mundo", d:2, st:"Vivant",    hc:"Noir",   bday:"??/??", w:0,  l:1,  draw:0}, // Compagnon de Nel

  // ============================================================
  // HOLLOWS
  // ============================================================
  {n:"Grand Fisher",          r:"Hollow",   sx:"M", arc:"Agent of Shinigami",       af:"Hueco Mundo", d:3, st:"Mort",      hc:"Roux",   bday:"??/??", w:2,  l:1,  draw:0},

  // ============================================================
  // FULLBRING — XCUTION
  // ============================================================
  {n:"Kugo Ginjo",            r:"Fullbring",sx:"M", arc:"Fullbring",                af:"Xcution",     d:4, st:"Mort",      hc:"Brun",   bday:"??/??", w:4,  l:2,  draw:0},
  {n:"Shukuro Tsukishima",    r:"Fullbring",sx:"M", arc:"Fullbring",                af:"Xcution",     d:4, st:"Mort",      hc:"Brun",   bday:"??/??", w:4,  l:1,  draw:0},
  {n:"Riruka Dokugamine",     r:"Fullbring",sx:"F", arc:"Fullbring",                af:"Xcution",     d:3, st:"Vivant",    hc:"Rouge",  bday:"??/??", w:1,  l:1,  draw:0},
  {n:"Yukio Hans Vorarlberna",r:"Fullbring",sx:"M", arc:"Fullbring",                af:"Xcution",     d:3, st:"Vivant",    hc:"Brun",   bday:"??/??", w:1,  l:1,  draw:0},
  {n:"Jackie Tristan",        r:"Fullbring",sx:"F", arc:"Fullbring",                af:"Xcution",     d:3, st:"Vivant",    hc:"Noir",   bday:"??/??", w:1,  l:1,  draw:0},
  {n:"Giriko Kutsuzawa",      r:"Fullbring",sx:"M", arc:"Fullbring",                af:"Xcution",     d:3, st:"Mort",      hc:"Blond",  bday:"??/??", w:1,  l:1,  draw:0},
  {n:"Moe Shishigawara",      r:"Fullbring",sx:"M", arc:"Fullbring",                af:"Xcution",     d:2, st:"Vivant",    hc:"Brun",   bday:"??/??", w:1,  l:1,  draw:0},

  // ============================================================
  // WANDENREICH
  // Roi → Schutzstaffel → Sternritter par lettre A→Z
  // ============================================================

  // Roi des Quincy
  {n:"Yhwach",                r:"Quincy",   sx:"M", arc:"Thousand-Year Blood War",  af:"Wandenreich", d:5, st:"Mort",      hc:"Noir",   bday:"??/??", w:8,  l:1,  draw:0},

  // Sternritter B — The Balance (Grand Maître / bras droit)
  {n:"Jugram Haschwalth",     r:"Quincy",   sx:"M", arc:"Thousand-Year Blood War",  af:"Wandenreich", d:5, st:"Mort",      hc:"Blond",  bday:"??/??", w:5,  l:1,  draw:0},

  // Schutzstaffel (Garde rapprochée — 4 Sternritter d'élite)
  {n:"Pernida Parnkgjas",     r:"Quincy",   sx:"M", arc:"Thousand-Year Blood War",  af:"Wandenreich", d:5, st:"Mort",      hc:"Chauve", bday:"??/??", w:3,  l:1,  draw:0}, // C — The Compulsory
  {n:"Askin Nakk Le Vaar",    r:"Quincy",   sx:"M", arc:"Thousand-Year Blood War",  af:"Wandenreich", d:5, st:"Mort",      hc:"Brun",   bday:"??/??", w:3,  l:1,  draw:0}, // D — The Deathdealing
  {n:"Gerard Valkyrie",       r:"Quincy",   sx:"M", arc:"Thousand-Year Blood War",  af:"Wandenreich", d:5, st:"Incertain", hc:"Blanc",  bday:"??/??", w:3,  l:1,  draw:0}, // M — The Miracle
  {n:"Lille Barro",           r:"Quincy",   sx:"M", arc:"Thousand-Year Blood War",  af:"Wandenreich", d:5, st:"Mort",      hc:"Blanc",  bday:"??/??", w:3,  l:1,  draw:0}, // X — The X-Axis

  // Sternritter E → Z (par lettre)
  {n:"Bambietta Basterbine",  r:"Quincy",   sx:"F", arc:"Thousand-Year Blood War",  af:"Wandenreich", d:4, st:"Mort",      hc:"Noir",   bday:"??/??", w:2,  l:1,  draw:0}, // E — The Explode
  {n:"As Nodt",               r:"Quincy",   sx:"M", arc:"Thousand-Year Blood War",  af:"Wandenreich", d:5, st:"Mort",      hc:"Noir",   bday:"??/??", w:3,  l:1,  draw:0}, // F — The Fear
  {n:"Liltotto Lamperd",      r:"Quincy",   sx:"F", arc:"Thousand-Year Blood War",  af:"Wandenreich", d:4, st:"Vivant",    hc:"Blond",  bday:"??/??", w:3,  l:1,  draw:0}, // G — The Glutton
  {n:"Bazz-B",                r:"Quincy",   sx:"M", arc:"Thousand-Year Blood War",  af:"Wandenreich", d:4, st:"Mort",      hc:"Rouge",  bday:"??/??", w:2,  l:2,  draw:0}, // H — The Heat
  {n:"Cang Du",               r:"Quincy",   sx:"M", arc:"Thousand-Year Blood War",  af:"Wandenreich", d:4, st:"Mort",      hc:"Blanc",  bday:"??/??", w:2,  l:1,  draw:0}, // I — The Iron
  {n:"Quilge Opie",           r:"Quincy",   sx:"M", arc:"Thousand-Year Blood War",  af:"Wandenreich", d:4, st:"Mort",      hc:"Blond",  bday:"??/??", w:2,  l:1,  draw:0}, // J — The Jail
  {n:"BG9",                   r:"Quincy",   sx:"M", arc:"Thousand-Year Blood War",  af:"Wandenreich", d:4, st:"Mort",      hc:"Chauve", bday:"??/??", w:2,  l:1,  draw:0}, // K — The Puppet
  {n:"PePe Waccabrada",       r:"Quincy",   sx:"M", arc:"Thousand-Year Blood War",  af:"Wandenreich", d:4, st:"Mort",      hc:"Blanc",  bday:"??/??", w:2,  l:1,  draw:0}, // L — The Love
  {n:"Mask De Masculine",     r:"Quincy",   sx:"M", arc:"Thousand-Year Blood War",  af:"Wandenreich", d:4, st:"Mort",      hc:"Noir",   bday:"??/??", w:2,  l:1,  draw:0}, // S — The Superstar
  {n:"Candice Catnipp",       r:"Quincy",   sx:"F", arc:"Thousand-Year Blood War",  af:"Wandenreich", d:4, st:"Vivant",    hc:"Vert",   bday:"??/??", w:2,  l:1,  draw:0}, // T — The Thunderbolt
  {n:"NaNaNa Najahkoop",      r:"Quincy",   sx:"M", arc:"Thousand-Year Blood War",  af:"Wandenreich", d:3, st:"Mort",      hc:"Brun",   bday:"??/??", w:1,  l:1,  draw:0}, // U — The Underbelly
  {n:"Gremmy Thoumeaux",      r:"Quincy",   sx:"M", arc:"Thousand-Year Blood War",  af:"Wandenreich", d:5, st:"Mort",      hc:"Blanc",  bday:"??/??", w:2,  l:1,  draw:0}, // V — The Visionary
  {n:"Nianzol Weizol",        r:"Quincy",   sx:"M", arc:"Thousand-Year Blood War",  af:"Wandenreich", d:4, st:"Mort",      hc:"Blanc",  bday:"??/??", w:2,  l:1,  draw:0}, // W — The Wind
  {n:"Robert Accutrone",      r:"Quincy",   sx:"M", arc:"Thousand-Year Blood War",  af:"Wandenreich", d:3, st:"Mort",      hc:"Blanc",  bday:"??/??", w:1,  l:1,  draw:0}, // N — The Needle (tué par Kyoraku)
  {n:"Driscoll Berci",        r:"Quincy",   sx:"M", arc:"Thousand-Year Blood War",  af:"Wandenreich", d:3, st:"Mort",      hc:"Chauve", bday:"??/??", w:1,  l:1,  draw:0}, // O — The Overkill (tué par Yamamoto)
  {n:"Meninas McAllon",       r:"Quincy",   sx:"F", arc:"Thousand-Year Blood War",  af:"Wandenreich", d:4, st:"Vivant",    hc:"Rose",   bday:"??/??", w:2,  l:1,  draw:0}, // P — The Power
  {n:"Berenice Gabrielli",    r:"Quincy",   sx:"F", arc:"Thousand-Year Blood War",  af:"Wandenreich", d:3, st:"Mort",      hc:"Brun",   bday:"??/??", w:1,  l:1,  draw:0}, // Q — The Question (tuée par Zaraki)
  {n:"Jerome Guizbatt",       r:"Quincy",   sx:"M", arc:"Thousand-Year Blood War",  af:"Wandenreich", d:3, st:"Mort",      hc:"Noir",   bday:"??/??", w:1,  l:1,  draw:0}, // R — The Roar (tué par Zaraki)
  {n:"Royd Lloyd",            r:"Quincy",   sx:"M", arc:"Thousand-Year Blood War",  af:"Wandenreich", d:4, st:"Mort",      hc:"Chauve", bday:"??/??", w:2,  l:1,  draw:0}, // Y — The Yourself (tué par Yamamoto)
  {n:"Loyd Lloyd",            r:"Quincy",   sx:"M", arc:"Thousand-Year Blood War",  af:"Wandenreich", d:3, st:"Mort",      hc:"Chauve", bday:"??/??", w:1,  l:1,  draw:0}, // Y — The Yourself (tué par Zaraki)
  {n:"Giselle Gewelle",       r:"Quincy",   sx:"F", arc:"Thousand-Year Blood War",  af:"Wandenreich", d:4, st:"Vivant",    hc:"Noir",   bday:"??/??", w:2,  l:1,  draw:0}, // Z — The Zombie

];
