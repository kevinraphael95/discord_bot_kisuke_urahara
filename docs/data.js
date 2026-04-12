// data.js — Bleach Guessr
// Arcs :
// "Le Shinigami Remplaçant (1)"          arc 1  — ch. 1–70
// "Soul Society : L'Invasion (2.1)"        arc 2a — ch. 71–117
// "Soul Society : Le Sauvetage (2.2)"      arc 2b — ch. 118–182
// "Arrancar : Invasion du monde des humains (3.1)"      arc 3a — ch. 183–286
// "Arrancar : Invasion du Hueco Mundo (3.2)"           arc 3b — ch. 287–423
// "Arrancar : Bataille de Karakura (3.3)"  arc 3c — ch. 424–479
// "Arc Fullbringers (4)"                 arc 4  — ch. 480–523
// "Guerre Sanglante de Mille Ans (5)"    arc 5  — ch. 524–686

const CHARS = [

  // ============================================================
  // PROTAGONISTES, FAMILLE DE ICHIGO & HUMAINS DE KARAKURA
  // ============================================================
  {n:"Ichigo Kurosaki",       r:"Humain",   sx:"M", arc:"Le Shinigami Remplaçant (1)",       af:"Karakura",    d:5, st:"Vivant",    hc:"Roux",   bday:"15/07", w:28, l:6,  draw:2},
  {n:"Orihime Inoue",         r:"Humain",   sx:"F", arc:"Le Shinigami Remplaçant (1)",       af:"Karakura",    d:2, st:"Vivant",    hc:"Roux",   bday:"03/09", w:2,  l:5,  draw:1},
  {n:"Yasutora Sado",         r:"Humain",   sx:"M", arc:"Le Shinigami Remplaçant (1)",       af:"Karakura",    d:3, st:"Vivant",    hc:"Noir",   bday:"07/04", w:6,  l:4,  draw:0},
  {n:"Uryuu Ishida",          r:"Quincy",   sx:"M", arc:"Le Shinigami Remplaçant (1)",       af:"Karakura",    d:4, st:"Vivant",    hc:"Noir",   bday:"06/11", w:8,  l:4,  draw:1},
  {n:"Isshin Kurosaki",       r:"Shinigami",sx:"M", arc:"Le Shinigami Remplaçant (1)",       af:"Karakura",    d:5, st:"Vivant",    hc:"Noir",   bday:"10/12", w:5,  l:1,  draw:0},
  {n:"Kon",                   r:"Mod-Soul", sx:"M", arc:"Le Shinigami Remplaçant (1)",       af:"Karakura",    d:1, st:"Vivant",    hc:"Blond",  bday:"??/??", w:1,  l:3,  draw:0},
  {n:"Don Kanonji",           r:"Humain",   sx:"M", arc:"Le Shinigami Remplaçant (1)",       af:"Karakura",    d:1, st:"Vivant",    hc:"Brun",   bday:"23/03", w:0, l:0, draw:0},
  {n:"Ganju Shiba",           r:"Humain",   sx:"M", arc:"Soul Society : L'Invasion (2.1)",   af:"Indépendant", d:2, st:"Vivant",    hc:"Noir",   bday:"02/11", w:2,  l:2,  draw:0},
  {n:"Kukaku Shiba",          r:"Humain",   sx:"F", arc:"Soul Society : L'Invasion (2.1)",   af:"Indépendant", d:3, st:"Vivant",    hc:"Noir",   bday:"01/09", w:1,  l:0,  draw:0},
  {n:"Masaki Kurosaki",       r:"Humain",   sx:"F", arc:"Le Shinigami Remplaçant (1)",       af:"Karakura",    d:4, st:"Mort",      hc:"Noir",   bday:"09/06", w:0, l:0, draw:0},
  {n:"Karin Kurosaki",        r:"Humain",   sx:"F", arc:"Le Shinigami Remplaçant (1)",       af:"Karakura",    d:1, st:"Vivant",    hc:"Noir",   bday:"06/06", w:0, l:0, draw:0},
  {n:"Yuzu Kurosaki",         r:"Humain",   sx:"F", arc:"Le Shinigami Remplaçant (1)",       af:"Karakura",    d:1, st:"Vivant",    hc:"Noir",   bday:"06/06", w:0, l:0, draw:0},
  {n:"Tatsuki Arisawa",       r:"Humain",   sx:"F", arc:"Le Shinigami Remplaçant (1)",       af:"Karakura",    d:3, st:"Vivant",    hc:"Brun",   bday:"17/07", w:1, l:0, draw:0},
  {n:"Keigo Asano",           r:"Humain",   sx:"M", arc:"Le Shinigami Remplaçant (1)",       af:"Karakura",    d:1, st:"Vivant",    hc:"Brun",   bday:"01/04", w:0, l:0, draw:0},
  {n:"Mizuiro Kojima",        r:"Humain",   sx:"M", arc:"Le Shinigami Remplaçant (1)",       af:"Karakura",    d:1, st:"Vivant",    hc:"Noir",   bday:"??/??", w:0, l:0, draw:0},
  {n:"Chizuru Honsho",        r:"Humain",   sx:"F", arc:"Le Shinigami Remplaçant (1)",       af:"Karakura",    d:1, st:"Vivant",    hc:"Brun",   bday:"??/??", w:0, l:0, draw:0},
  
  // ============================================================
  // URAHARA SHOP
  // ============================================================
  {n:"Kisuke Urahara",        r:"Shinigami",sx:"M", arc:"Le Shinigami Remplaçant (1)",       af:"Indépendant", d:5, st:"Vivant",    hc:"Blond",  bday:"31/12", w:10, l:1,  draw:1},
  {n:"Yoruichi Shihoin",      r:"Shinigami",sx:"F", arc:"Le Shinigami Remplaçant (1)",       af:"Indépendant", d:5, st:"Vivant",    hc:"Violet", bday:"01/01", w:8,  l:1,  draw:0},
  {n:"Tessai Tsukabishi",     r:"Shinigami",sx:"M", arc:"Le Shinigami Remplaçant (1)",       af:"Indépendant", d:4, st:"Vivant",    hc:"Noir",   bday:"??/??", w:2,  l:0,  draw:0},
  {n:"Jinta Hanakari",        r:"Humain",   sx:"M", arc:"Le Shinigami Remplaçant (1)",       af:"Indépendant", d:1, st:"Vivant",    hc:"Rouge",  bday:"??/??", w:0,  l:1,  draw:0},
  {n:"Ururu Tsumugiya",       r:"Humain",   sx:"F", arc:"Le Shinigami Remplaçant (1)",       af:"Indépendant", d:2, st:"Vivant",    hc:"Noir",   bday:"??/??", w:1,  l:1,  draw:0},

  // ============================================================
  // DIVISION ZÉRO — ROYAL GUARD
  // ============================================================
  {n:"Ichibei Hyosube",       r:"Shinigami",sx:"M", arc:"Guerre Sanglante de Mille Ans (5)", af:"Division Zero", d:5, st:"Vivant",    hc:"Blanc",  bday:"??/??", w:4,  l:0,  draw:0},
  {n:"Oetsu Nimaiya",         r:"Shinigami",sx:"M", arc:"Guerre Sanglante de Mille Ans (5)", af:"Division Zero", d:5, st:"Vivant",    hc:"Noir",   bday:"??/??", w:3,  l:0,  draw:0},
  {n:"Tenjiro Kirinji",       r:"Shinigami",sx:"M", arc:"Guerre Sanglante de Mille Ans (5)", af:"Division Zero", d:5, st:"Vivant",    hc:"Rouge",  bday:"??/??", w:2,  l:0,  draw:0},
  {n:"Kirio Hikifune",        r:"Shinigami",sx:"F", arc:"Guerre Sanglante de Mille Ans (5)", af:"Division Zero", d:5, st:"Vivant",    hc:"Noir",   bday:"??/??", w:2,  l:0,  draw:0},
  {n:"Shutara Senjumaru",     r:"Shinigami",sx:"F", arc:"Guerre Sanglante de Mille Ans (5)", af:"Division Zero", d:5, st:"Vivant",    hc:"Blanc",  bday:"??/??", w:2,  l:0,  draw:0},

  // ============================================================
  // GOTEI 13 — CAPITAINES
  // ============================================================
  {n:"Shunsui Kyoraku",       r:"Shinigami",sx:"M", arc:"Soul Society : L'Invasion (2.1)",     af:"Gotei 13",    d:5, st:"Vivant",    hc:"Brun",   bday:"11/07", w:6,  l:1,  draw:1},
  {n:"Soi Fon",               r:"Shinigami",sx:"F", arc:"Soul Society : L'Invasion (2.1)",     af:"Gotei 13",    d:4, st:"Vivant",    hc:"Noir",   bday:"11/02", w:5,  l:2,  draw:1},
  {n:"Rose Otoribashi",       r:"Vizard",   sx:"M", arc:"Arrancar : Bataille de Karakura (3.3)",af:"Gotei 13",   d:4, st:"Vivant",    hc:"Blond",  bday:"16/01", w:2,  l:2,  draw:0},
  {n:"Isane Kotetsu",         r:"Shinigami",sx:"F", arc:"Soul Society : L'Invasion (2.1)",     af:"Gotei 13",    d:3, st:"Vivant",    hc:"Gris",   bday:"08/08", w:1,  l:1,  draw:0},
  {n:"Shinji Hirako",         r:"Vizard",   sx:"M", arc:"Arrancar : Invasion du monde des humains (3.1)",   af:"Gotei 13",    d:4, st:"Vivant",    hc:"Blond",  bday:"15/05", w:3,  l:2,  draw:0},
  {n:"Byakuya Kuchiki",       r:"Shinigami",sx:"M", arc:"Le Shinigami Remplaçant (1)",         af:"Gotei 13",    d:5, st:"Vivant",    hc:"Noir",   bday:"31/01", w:8,  l:3,  draw:0},
  {n:"Lisa Yadomaru",         r:"Vizard",   sx:"F", arc:"Arrancar : Bataille de Karakura (3.3)",af:"Gotei 13",   d:4, st:"Vivant",    hc:"Noir",   bday:"03/07", w:2,  l:2,  draw:0},
  {n:"Kensei Muguruma",       r:"Vizard",   sx:"M", arc:"Arrancar : Bataille de Karakura (3.3)",af:"Gotei 13",   d:4, st:"Vivant",    hc:"Gris",   bday:"30/07", w:3,  l:2,  draw:0},
  {n:"Toshiro Hitsugaya",     r:"Shinigami",sx:"M", arc:"Soul Society : L'Invasion (2.1)",     af:"Gotei 13",    d:5, st:"Vivant",    hc:"Blanc",  bday:"20/12", w:7,  l:3,  draw:0},
  {n:"Kenpachi Zaraki",       r:"Shinigami",sx:"M", arc:"Soul Society : L'Invasion (2.1)",     af:"Gotei 13",    d:5, st:"Vivant",    hc:"Noir",   bday:"19/11", w:9,  l:2,  draw:1},
  {n:"Mayuri Kurotsuchi",     r:"Shinigami",sx:"M", arc:"Soul Society : L'Invasion (2.1)",     af:"Gotei 13",    d:4, st:"Vivant",    hc:"Noir",   bday:"30/03", w:6,  l:1,  draw:0},
  {n:"Rukia Kuchiki",         r:"Shinigami",sx:"F", arc:"Le Shinigami Remplaçant (1)",         af:"Gotei 13",    d:4, st:"Vivant",    hc:"Noir",   bday:"14/01", w:9,  l:3,  draw:0},

  // ============================================================
  // GOTEI 13 — ANCIENS CAPITAINES
  // ============================================================
  {n:"Genryusai Yamamoto",    r:"Shinigami",sx:"M", arc:"Soul Society : L'Invasion (2.1)",     af:"Gotei 13",    d:5, st:"Mort",      hc:"Blanc",  bday:"21/01", w:5,  l:1,  draw:0},
  {n:"Retsu Unohana",         r:"Shinigami",sx:"F", arc:"Soul Society : L'Invasion (2.1)",     af:"Gotei 13",    d:5, st:"Mort",      hc:"Noir",   bday:"21/04", w:3,  l:1,  draw:0},
  {n:"Sosuke Aizen",          r:"Shinigami",sx:"M", arc:"Soul Society : L'Invasion (2.1)",     af:"Indépendant", d:5, st:"Vivant",    hc:"Brun",   bday:"29/05", w:12, l:1,  draw:0},
  {n:"Sajin Komamura",        r:"Shinigami",sx:"M", arc:"Soul Society : L'Invasion (2.1)",     af:"Gotei 13",    d:4, st:"Incertain", hc:"Roux",   bday:"23/08", w:4,  l:3,  draw:0},
  {n:"Kaname Tousen",         r:"Shinigami",sx:"M", arc:"Soul Society : L'Invasion (2.1)",     af:"Indépendant", d:4, st:"Mort",      hc:"Noir",   bday:"13/10", w:3,  l:2,  draw:0},
  {n:"Gin Ichimaru",          r:"Shinigami",sx:"M", arc:"Soul Society : L'Invasion (2.1)",     af:"Indépendant", d:5, st:"Mort",      hc:"Argent", bday:"10/09", w:4,  l:1,  draw:0},
  {n:"Jushiro Ukitake",       r:"Shinigami",sx:"M", arc:"Soul Society : L'Invasion (2.1)",     af:"Gotei 13",    d:4, st:"Mort",      hc:"Blanc",  bday:"21/12", w:2,  l:1,  draw:1},
  {n:"Ginrei Kuchiki",        r:"Shinigami",sx:"M", arc:"Soul Society : L'Invasion (2.1)",     af:"Gotei 13",    d:4, st:"Mort",      hc:"Blanc",  bday:"??/??", w:1,  l:0,  draw:0},

  // ============================================================
  // GOTEI 13 — VICE-CAPITAINES TYBW
  // ============================================================
  {n:"Nanao Ise",             r:"Shinigami",sx:"F", arc:"Soul Society : L'Invasion (2.1)",     af:"Gotei 13",    d:3, st:"Vivant",    hc:"Noir",   bday:"07/07", w:2,  l:1,  draw:0},
  {n:"Genshiro Okikiba",      r:"Shinigami",sx:"M", arc:"Guerre Sanglante de Mille Ans (5)",   af:"Gotei 13",    d:2, st:"Vivant",    hc:"Noir",   bday:"??/??", w:1,  l:0,  draw:0},
  {n:"Marenoshin Omaeda",     r:"Shinigami",sx:"M", arc:"Soul Society : L'Invasion (2.1)",     af:"Gotei 13",    d:2, st:"Vivant",    hc:"Noir",   bday:"05/05", w:1,  l:2,  draw:0},
  {n:"Izuru Kira",            r:"Shinigami",sx:"M", arc:"Soul Society : L'Invasion (2.1)",     af:"Gotei 13",    d:3, st:"Incertain", hc:"Blond",  bday:"27/03", w:3,  l:3,  draw:0},
  {n:"Kiyone Kotetsu",        r:"Shinigami",sx:"F", arc:"Soul Society : Le Sauvetage (2.2)",   af:"Gotei 13",    d:2, st:"Vivant",    hc:"Vert",   bday:"??/??", w:1,  l:1,  draw:0},
  {n:"Momo Hinamori",         r:"Shinigami",sx:"F", arc:"Soul Society : L'Invasion (2.1)",     af:"Gotei 13",    d:3, st:"Vivant",    hc:"Brun",   bday:"03/06", w:2,  l:3,  draw:0},
  {n:"Renji Abarai",          r:"Shinigami",sx:"M", arc:"Le Shinigami Remplaçant (1)",         af:"Gotei 13",    d:4, st:"Vivant",    hc:"Rouge",  bday:"31/08", w:7,  l:5,  draw:0},
  {n:"Atau Rindo",            r:"Shinigami",sx:"M", arc:"Guerre Sanglante de Mille Ans (5)",   af:"Gotei 13",    d:2, st:"Vivant",    hc:"Noir",   bday:"??/??", w:0,  l:0,  draw:0},
  {n:"Yuyu Yayahara",         r:"Shinigami",sx:"F", arc:"Guerre Sanglante de Mille Ans (5)",   af:"Gotei 13",    d:2, st:"Vivant",    hc:"Noir",   bday:"??/??", w:0,  l:0,  draw:0},
  {n:"Shuhei Hisagi",         r:"Shinigami",sx:"M", arc:"Soul Society : L'Invasion (2.1)",     af:"Gotei 13",    d:3, st:"Vivant",    hc:"Noir",   bday:"14/08", w:3,  l:3,  draw:0},
  {n:"Rangiku Matsumoto",     r:"Shinigami",sx:"F", arc:"Soul Society : L'Invasion (2.1)",     af:"Gotei 13",    d:3, st:"Vivant",    hc:"Blond",  bday:"29/09", w:3,  l:3,  draw:0},
  {n:"Ikkaku Madarame",       r:"Shinigami",sx:"M", arc:"Soul Society : Le Sauvetage (2.2)",   af:"Gotei 13",    d:3, st:"Vivant",    hc:"Chauve", bday:"08/11", w:4,  l:3,  draw:0},
  {n:"Akon",                  r:"Shinigami",sx:"M", arc:"Guerre Sanglante de Mille Ans (5)",   af:"Gotei 13",    d:2, st:"Vivant",    hc:"Violet", bday:"??/??", w:1,  l:0,  draw:0},
  {n:"Sentaro Kotsubaki",     r:"Shinigami",sx:"M", arc:"Soul Society : Le Sauvetage (2.2)",   af:"Gotei 13",    d:2, st:"Vivant",    hc:"Brun",   bday:"??/??", w:1,  l:1,  draw:0},

  // ============================================================
  // GOTEI 13 — ANCIENS VICE-CAPITAINES
  // ============================================================
  {n:"Chojiro Sasakibe",      r:"Shinigami",sx:"M", arc:"Soul Society : L'Invasion (2.1)",     af:"Gotei 13",    d:3, st:"Mort",      hc:"Brun",   bday:"04/11", w:0,  l:1,  draw:0},
  {n:"Yachiru Kusajishi",     r:"Shinigami",sx:"F", arc:"Soul Society : Le Sauvetage (2.2)",   af:"Gotei 13",    d:4, st:"Incertain", hc:"Rose",   bday:"12/02", w:2,  l:0,  draw:1},
  {n:"Nemu Kurotsuchi",       r:"Mod-Soul", sx:"F", arc:"Soul Society : L'Invasion (2.1)",     af:"Gotei 13",    d:3, st:"Mort",      hc:"Noir",   bday:"30/03", w:2,  l:2,  draw:0},

  // ============================================================
  // GOTEI 13 — AUTRES MEMBRES NOTABLES
  // ============================================================
  {n:"Yumichika Ayasegawa",   r:"Shinigami",sx:"M", arc:"Soul Society : Le Sauvetage (2.2)",   af:"Gotei 13",    d:3, st:"Vivant",    hc:"Noir",   bday:"19/09", w:3,  l:1,  draw:0},
  {n:"Hanataro Yamada",       r:"Shinigami",sx:"M", arc:"Soul Society : Le Sauvetage (2.2)",   af:"Gotei 13",    d:1, st:"Vivant",    hc:"Noir",   bday:"01/04", w:1,  l:1,  draw:0},

  // ============================================================
  // VIZARDS (non promus capitaines à la fin)
  // ============================================================
  {n:"Hiyori Sarugaki",       r:"Vizard",   sx:"F", arc:"Arrancar : Invasion du monde des humains (3.1)",   af:"Indépendant", d:3, st:"Vivant",    hc:"Blond",  bday:"08/08", w:2,  l:2,  draw:0},
  {n:"Love Aikawa",           r:"Vizard",   sx:"M", arc:"Arrancar : Bataille de Karakura (3.3)",af:"Gotei 13",   d:4, st:"Vivant",    hc:"Noir",   bday:"21/06", w:2,  l:2,  draw:0},
  {n:"Mashiro Kuna",          r:"Vizard",   sx:"F", arc:"Arrancar : Bataille de Karakura (3.3)",af:"Indépendant",d:3, st:"Vivant",    hc:"Vert",   bday:"28/05", w:2,  l:1,  draw:0},
  {n:"Hachigen Ushoda",       r:"Vizard",   sx:"M", arc:"Arrancar : Bataille de Karakura (3.3)",af:"Indépendant",d:4, st:"Vivant",    hc:"Rose",   bday:"??/??", w:2,  l:1,  draw:0},

  // ============================================================
  // ESPADA (par numéro tatoué : 1 → 10)
  // ============================================================
  {n:"Coyote Starrk",         r:"Arrancar", sx:"M", arc:"Arrancar : Invasion du monde des humains (3.1)",   af:"Espada",      d:5, st:"Mort",      hc:"Brun",   bday:"??/??", w:4,  l:1,  draw:0},
  {n:"Lilynette Gingerbuck",  r:"Arrancar", sx:"F", arc:"Arrancar : Invasion du monde des humains (3.1)",   af:"Espada",      d:4, st:"Mort",      hc:"Blond",  bday:"??/??", w:2,  l:1,  draw:0},
  {n:"Baraggan Louisenbairn", r:"Arrancar", sx:"M", arc:"Arrancar : Bataille de Karakura (3.3)",            af:"Espada",     d:5, st:"Mort",      hc:"Chauve", bday:"??/??", w:3,  l:1,  draw:0},
  {n:"Tier Harribel",         r:"Arrancar", sx:"F", arc:"Arrancar : Bataille de Karakura (3.3)",            af:"Espada",     d:5, st:"Vivant",    hc:"Blond",  bday:"??/??", w:3,  l:1,  draw:0},
  {n:"Ulquiorra Cifer",       r:"Arrancar", sx:"M", arc:"Arrancar : Invasion du monde des humains (3.1)",   af:"Espada",      d:5, st:"Mort",      hc:"Noir",   bday:"??/??", w:5,  l:1,  draw:0},
  {n:"Nnoitra Gilga",         r:"Arrancar", sx:"M", arc:"Arrancar : Invasion du Hueco Mundo (3.2)",         af:"Espada",      d:5, st:"Mort",      hc:"Noir",   bday:"??/??", w:4,  l:1,  draw:0},
  {n:"Grimmjow Jaegerjaquez", r:"Arrancar", sx:"M", arc:"Arrancar : Invasion du monde des humains (3.1)",   af:"Espada",      d:5, st:"Vivant",    hc:"Bleu",   bday:"??/??", w:4,  l:2,  draw:0},
  {n:"Zommari Rureaux",       r:"Arrancar", sx:"M", arc:"Arrancar : Invasion du Hueco Mundo (3.2)",         af:"Espada",      d:4, st:"Mort",      hc:"Chauve", bday:"??/??", w:2,  l:1,  draw:0},
  {n:"Szayelaporro Grantz",   r:"Arrancar", sx:"M", arc:"Arrancar : Invasion du Hueco Mundo (3.2)",         af:"Espada",      d:4, st:"Mort",      hc:"Rose",   bday:"??/??", w:3,  l:1,  draw:0},
  {n:"Aaroniero Arruruerie",  r:"Arrancar", sx:"M", arc:"Arrancar : Invasion du Hueco Mundo (3.2)",         af:"Espada",      d:4, st:"Mort",      hc:"Noir",   bday:"??/??", w:2,  l:1,  draw:0},
  {n:"Yammy Llargo",          r:"Arrancar", sx:"M", arc:"Arrancar : Invasion du monde des humains (3.1)",   af:"Espada",      d:5, st:"Mort",      hc:"Noir",   bday:"??/??", w:3,  l:1,  draw:0},

  // ============================================================
  // EX-ESPADA & ARRANCAR NOTABLES
  // ============================================================
  {n:"Nelliel Tu Odelschwanck",r:"Arrancar",sx:"F", arc:"Arrancar : Invasion du Hueco Mundo (3.2)",         af:"Hueco Mundo", d:5, st:"Vivant",    hc:"Vert",   bday:"??/??", w:4,  l:1,  draw:0},
  {n:"Luppi Antenor",         r:"Arrancar", sx:"M", arc:"Arrancar : Invasion du monde des humains (3.1)",   af:"Espada",      d:3, st:"Mort",      hc:"Noir",   bday:"??/??", w:1,  l:1,  draw:0},
  {n:"Wonderweiss Margela",   r:"Arrancar", sx:"M", arc:"Arrancar : Bataille de Karakura (3.3)",af:"Espada",     d:4, st:"Mort",      hc:"Blond",  bday:"??/??", w:2,  l:1,  draw:0},

  // ============================================================
  // FRACCIÓN DE HARRIBEL (Espada 3)
  // ============================================================
  {n:"Franceska Mila Rose",   r:"Arrancar", sx:"F", arc:"Arrancar : Invasion du monde des humains (3.1)",   af:"Espada",      d:3, st:"Vivant",    hc:"Noir",   bday:"??/??", w:1,  l:1,  draw:0},
  {n:"Apache",                r:"Arrancar", sx:"F", arc:"Arrancar : Invasion du monde des humains (3.1)",   af:"Espada",      d:3, st:"Vivant",    hc:"Noir",   bday:"??/??", w:1,  l:1,  draw:0},
  {n:"Sun-Sun",               r:"Arrancar", sx:"F", arc:"Arrancar : Invasion du monde des humains (3.1)",   af:"Espada",      d:3, st:"Vivant",    hc:"Vert",   bday:"??/??", w:1,  l:1,  draw:0},

  // ============================================================
  // ARRANCAR DIVERS (Números, Privaron Espada, autres)
  // ============================================================
  {n:"Loly Aivirrne",         r:"Arrancar", sx:"F", arc:"Arrancar : Invasion du Hueco Mundo (3.2)",        af:"Espada",      d:2, st:"Vivant",    hc:"Noir",   bday:"??/??", w:0,  l:2,  draw:0},
  {n:"Menoly Mallia",         r:"Arrancar", sx:"F", arc:"Arrancar : Invasion du Hueco Mundo (3.2)",        af:"Espada",      d:2, st:"Incertain", hc:"Blond",  bday:"??/??", w:0,  l:2,  draw:0},
  {n:"Shawlong Koufang",      r:"Arrancar", sx:"M", arc:"Arrancar : Invasion du monde des humains (3.1)",  af:"Espada",      d:3, st:"Mort",      hc:"Noir",   bday:"??/??", w:1,  l:1,  draw:0},
  {n:"Findorr Calius",        r:"Arrancar", sx:"M", arc:"Arrancar : Bataille de Karakura (3.3)",af:"Espada",     d:3, st:"Mort",      hc:"Blond",  bday:"??/??", w:1,  l:1,  draw:0},
  {n:"Charlotte Cuuhlhourne", r:"Arrancar", sx:"M", arc:"Arrancar : Bataille de Karakura (3.3)",af:"Espada",     d:3, st:"Mort",      hc:"Blond",  bday:"??/??", w:1,  l:1,  draw:0},
  {n:"Dordoni Alessandro",    r:"Arrancar", sx:"M", arc:"Arrancar : Invasion du Hueco Mundo (3.2)",        af:"Hueco Mundo", d:3, st:"Mort",      hc:"Brun",   bday:"??/??", w:2,  l:2,  draw:0},
  {n:"Cirucci Sanderwicci",   r:"Arrancar", sx:"F", arc:"Arrancar : Invasion du Hueco Mundo (3.2)",        af:"Hueco Mundo", d:3, st:"Mort",      hc:"Violet", bday:"??/??", w:1,  l:1,  draw:0},
  {n:"Gantenbainne Mosqueda", r:"Arrancar", sx:"M", arc:"Arrancar : Invasion du Hueco Mundo (3.2)",        af:"Hueco Mundo", d:3, st:"Mort",      hc:"Blanc",  bday:"??/??", w:1,  l:1,  draw:0},
  {n:"Pesche Guatiche",       r:"Arrancar", sx:"M", arc:"Arrancar : Invasion du Hueco Mundo (3.2)",        af:"Hueco Mundo", d:2, st:"Vivant",    hc:"Chauve", bday:"??/??", w:0,  l:1,  draw:0},
  {n:"Dondochakka Birstanne", r:"Arrancar", sx:"M", arc:"Arrancar : Invasion du Hueco Mundo (3.2)",        af:"Hueco Mundo", d:2, st:"Vivant",    hc:"Noir",   bday:"??/??", w:0,  l:1,  draw:0},

  // ============================================================
  // HOLLOWS
  // ============================================================
  {n:"Grand Fisher",          r:"Hollow",   sx:"M", arc:"Le Shinigami Remplaçant (1)",       af:"Hueco Mundo", d:3, st:"Mort",      hc:"Noir",   bday:"??/??", w:2,  l:1,  draw:0},
  {n:"Acidwire",              r:"Hollow",   sx:"M", arc:"Le Shinigami Remplaçant (1)",       af:"Hueco Mundo", d:1, st:"Mort",      hc:"Noir",   bday:"??/??", w:0,  l:1,  draw:0},
  {n:"Shrieker",              r:"Hollow",   sx:"M", arc:"Le Shinigami Remplaçant (1)",       af:"Hueco Mundo", d:2, st:"Mort",      hc:"Chauve", bday:"??/??", w:1,  l:1,  draw:0},
  {n:"Metastacia",            r:"Hollow",   sx:"M", arc:"Soul Society : Le Sauvetage (2.2)", af:"Hueco Mundo", d:3, st:"Mort",      hc:"Chauve", bday:"??/??", w:1,  l:1,  draw:0},
  {n:"Runuganga",             r:"Hollow",   sx:"M", arc:"Arrancar : Invasion du Hueco Mundo (3.2)",        af:"Hueco Mundo", d:2, st:"Mort",      hc:"Chauve", bday:"??/??", w:0,  l:1,  draw:0},
  {n:"Fishbone D",            r:"Hollow",   sx:"M", arc:"Le Shinigami Remplaçant (1)",       af:"Hueco Mundo", d:1, st:"Mort",      hc:"Chauve", bday:"??/??", w:0,  l:1,  draw:0},
  {n:"Bulbous G",             r:"Hollow",   sx:"M", arc:"Le Shinigami Remplaçant (1)",       af:"Hueco Mundo", d:2, st:"Mort",      hc:"Chauve", bday:"??/??", w:0,  l:1,  draw:0},
  {n:"Hexapodus",             r:"Hollow",   sx:"M", arc:"Le Shinigami Remplaçant (1)",       af:"Hueco Mundo", d:2, st:"Mort",      hc:"Chauve", bday:"??/??", w:0,  l:1,  draw:0},

  // ============================================================
  // FULLBRING — XCUTION
  // ============================================================
  {n:"Kugo Ginjo",            r:"Fullbring",sx:"M", arc:"Arc Fullbringers (4)",              af:"Xcution",     d:4, st:"Mort",      hc:"Brun",   bday:"??/??", w:4,  l:2,  draw:0},
  {n:"Shukuro Tsukishima",    r:"Fullbring",sx:"M", arc:"Arc Fullbringers (4)",              af:"Xcution",     d:4, st:"Mort",      hc:"Brun",   bday:"??/??", w:4,  l:1,  draw:0},
  {n:"Riruka Dokugamine",     r:"Fullbring",sx:"F", arc:"Arc Fullbringers (4)",              af:"Xcution",     d:3, st:"Vivant",    hc:"Rouge",  bday:"??/??", w:1,  l:1,  draw:0},
  {n:"Yukio Hans Vorarlberna",r:"Fullbring",sx:"M", arc:"Arc Fullbringers (4)",              af:"Xcution",     d:3, st:"Vivant",    hc:"Brun",   bday:"??/??", w:1,  l:1,  draw:0},
  {n:"Jackie Tristan",        r:"Fullbring",sx:"F", arc:"Arc Fullbringers (4)",              af:"Xcution",     d:3, st:"Vivant",    hc:"Noir",   bday:"??/??", w:1,  l:1,  draw:0},
  {n:"Giriko Kutsuzawa",      r:"Fullbring",sx:"M", arc:"Arc Fullbringers (4)",              af:"Xcution",     d:3, st:"Mort",      hc:"Noir",  bday:"??/??", w:1,  l:1,  draw:0},
  {n:"Moe Shishigawara",      r:"Fullbring",sx:"M", arc:"Arc Fullbringers (4)",              af:"Xcution",     d:2, st:"Vivant",    hc:"Brun",   bday:"??/??", w:1,  l:1,  draw:0},

  // ============================================================
  // WANDENREICH
  // ============================================================
  {n:"Yhwach",                r:"Quincy",   sx:"M", arc:"Guerre Sanglante de Mille Ans (5)", af:"Wandenreich", d:5, st:"Mort",      hc:"Noir",   bday:"??/??", w:8,  l:1,  draw:0},
  {n:"Jugram Haschwalth",     r:"Quincy",   sx:"M", arc:"Guerre Sanglante de Mille Ans (5)", af:"Wandenreich", d:5, st:"Mort",      hc:"Blond",  bday:"??/??", w:5,  l:1,  draw:0},
  {n:"Pernida Parnkgjas",     r:"Quincy",   sx:"M", arc:"Guerre Sanglante de Mille Ans (5)", af:"Wandenreich", d:5, st:"Mort",      hc:"Chauve", bday:"??/??", w:3,  l:1,  draw:0},
  {n:"Askin Nakk Le Vaar",    r:"Quincy",   sx:"M", arc:"Guerre Sanglante de Mille Ans (5)", af:"Wandenreich", d:5, st:"Mort",      hc:"Brun",   bday:"??/??", w:3,  l:1,  draw:0},
  {n:"Gerard Valkyrie",       r:"Quincy",   sx:"M", arc:"Guerre Sanglante de Mille Ans (5)", af:"Wandenreich", d:5, st:"Incertain", hc:"Blanc",  bday:"??/??", w:3,  l:1,  draw:0},
  {n:"Lille Barro",           r:"Quincy",   sx:"M", arc:"Guerre Sanglante de Mille Ans (5)", af:"Wandenreich", d:5, st:"Mort",      hc:"Blanc",  bday:"??/??", w:3,  l:1,  draw:0},
  {n:"Bambietta Basterbine",  r:"Quincy",   sx:"F", arc:"Guerre Sanglante de Mille Ans (5)", af:"Wandenreich", d:4, st:"Mort",      hc:"Noir",   bday:"??/??", w:2,  l:1,  draw:0},
  {n:"As Nodt",               r:"Quincy",   sx:"M", arc:"Guerre Sanglante de Mille Ans (5)", af:"Wandenreich", d:5, st:"Mort",      hc:"Noir",   bday:"??/??", w:3,  l:1,  draw:0},
  {n:"Liltotto Lamperd",      r:"Quincy",   sx:"F", arc:"Guerre Sanglante de Mille Ans (5)", af:"Wandenreich", d:4, st:"Vivant",    hc:"Blond",  bday:"??/??", w:3,  l:1,  draw:0},
  {n:"Bazz-B",                r:"Quincy",   sx:"M", arc:"Guerre Sanglante de Mille Ans (5)", af:"Wandenreich", d:4, st:"Mort",      hc:"Rouge",  bday:"??/??", w:2,  l:2,  draw:0},
  {n:"Cang Du",               r:"Quincy",   sx:"M", arc:"Guerre Sanglante de Mille Ans (5)", af:"Wandenreich", d:4, st:"Mort",      hc:"Blanc",  bday:"??/??", w:2,  l:1,  draw:0},
  {n:"Quilge Opie",           r:"Quincy",   sx:"M", arc:"Guerre Sanglante de Mille Ans (5)", af:"Wandenreich", d:4, st:"Mort",      hc:"Blond",  bday:"??/??", w:2,  l:1,  draw:0},
  {n:"BG9",                   r:"Quincy",   sx:"M", arc:"Guerre Sanglante de Mille Ans (5)", af:"Wandenreich", d:4, st:"Mort",      hc:"Chauve", bday:"??/??", w:2,  l:1,  draw:0},
  {n:"PePe Waccabrada",       r:"Quincy",   sx:"M", arc:"Guerre Sanglante de Mille Ans (5)", af:"Wandenreich", d:4, st:"Mort",      hc:"Chauve", bday:"??/??", w:2,  l:1,  draw:0},
  {n:"Robert Accutrone",      r:"Quincy",   sx:"M", arc:"Guerre Sanglante de Mille Ans (5)", af:"Wandenreich", d:3, st:"Mort",      hc:"Blanc",  bday:"??/??", w:1,  l:1,  draw:0},
  {n:"Driscoll Berci",        r:"Quincy",   sx:"M", arc:"Guerre Sanglante de Mille Ans (5)", af:"Wandenreich", d:3, st:"Mort",      hc:"Chauve", bday:"??/??", w:1,  l:1,  draw:0},
  {n:"Meninas McAllon",       r:"Quincy",   sx:"F", arc:"Guerre Sanglante de Mille Ans (5)", af:"Wandenreich", d:4, st:"Vivant",    hc:"Rose",   bday:"??/??", w:2,  l:1,  draw:0},
  {n:"Berenice Gabrielli",    r:"Quincy",   sx:"F", arc:"Guerre Sanglante de Mille Ans (5)", af:"Wandenreich", d:3, st:"Mort",      hc:"Brun",   bday:"??/??", w:1,  l:1,  draw:0},
  {n:"Jerome Guizbatt",       r:"Quincy",   sx:"M", arc:"Guerre Sanglante de Mille Ans (5)", af:"Wandenreich", d:3, st:"Mort",      hc:"Noir",   bday:"??/??", w:1,  l:1,  draw:0},
  {n:"Mask De Masculine",     r:"Quincy",   sx:"M", arc:"Guerre Sanglante de Mille Ans (5)", af:"Wandenreich", d:4, st:"Mort",      hc:"Noir",   bday:"??/??", w:2,  l:1,  draw:0},
  {n:"Candice Catnipp",       r:"Quincy",   sx:"F", arc:"Guerre Sanglante de Mille Ans (5)", af:"Wandenreich", d:4, st:"Vivant",    hc:"Vert",   bday:"??/??", w:2,  l:1,  draw:0},
  {n:"NaNaNa Najahkoop",      r:"Quincy",   sx:"M", arc:"Guerre Sanglante de Mille Ans (5)", af:"Wandenreich", d:3, st:"Mort",      hc:"Brun",   bday:"??/??", w:1,  l:1,  draw:0},
  {n:"Gremmy Thoumeaux",      r:"Quincy",   sx:"M", arc:"Guerre Sanglante de Mille Ans (5)", af:"Wandenreich", d:5, st:"Mort",      hc:"Blanc",  bday:"??/??", w:2,  l:1,  draw:0},
  {n:"Nianzol Weizol",        r:"Quincy",   sx:"M", arc:"Guerre Sanglante de Mille Ans (5)", af:"Wandenreich", d:4, st:"Mort",      hc:"Blanc",  bday:"??/??", w:2,  l:1,  draw:0},
  {n:"Royd Lloyd",            r:"Quincy",   sx:"M", arc:"Guerre Sanglante de Mille Ans (5)", af:"Wandenreich", d:4, st:"Mort",      hc:"Chauve", bday:"??/??", w:2,  l:1,  draw:0},
  {n:"Loyd Lloyd",            r:"Quincy",   sx:"M", arc:"Guerre Sanglante de Mille Ans (5)", af:"Wandenreich", d:3, st:"Mort",      hc:"Chauve", bday:"??/??", w:1,  l:1,  draw:0},
  {n:"Giselle Gewelle",       r:"Quincy",   sx:"F", arc:"Guerre Sanglante de Mille Ans (5)", af:"Wandenreich", d:4, st:"Vivant",    hc:"Noir",   bday:"??/??", w:2,  l:1,  draw:0},

];
