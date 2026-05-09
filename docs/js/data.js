// data.js — Bleach Guessr
// Arcs :
// "Le Shinigami Remplaçant (1)"                     — ch. 1–70
// Jusqu'à la fin de l'entrainement avec Urahara et la traversée du portail pour rentrer dans la Soul Society
// "Soul Society : L'Invasion (2.1)"                 — ch. 71–117
// Jusqu'au premier combat contre byakuya sur le pont et l'arrivé de Yoruichi qui va entrainer Ichigo
// "Soul Society : Le Sauvetage (2.2)"               — ch. 118–182
// Ichigo est rentré chez lui le monde des humains Rukia est sauvée
// "Arrancar : Invasion du monde des humains (3.1)"  — ch. 183–229
// ???
// "Arrancar : Invasion du Hueco Mundo (3.2)"        — ch. 230–315
// Infiltration du Hueco Mundo jusqu'au départ d'Aizen vers Karakura
// "Arrancar : Bataille de Karakura (3.3)"           — ch. 316–423
// Fake Karakura Town, combat final contre Aizen
// "Arc Fullbringers (4)"                            — ch. 424–479
// Les fullbringers
// "Guerre Sanglante de Mille Ans (5)"               — ch. 480–686
// La guerre sanglante c'est sanglant
// NO BREATHES FROM HELL (6)                         — ch. xxx
// ouai ouai

const CHARS = [

  // ============================================================
  // FAMILLE DE ICHIGO
  // ============================================================
  {n:"Isshin Kurosaki",       r:"Shinigami", sx:"M", arc:"Le Shinigami Remplaçant (1)",       af:"Karakura",    d:5, st:"Vivant",    hc:"Noir",   bday:"10/12", w:5,  l:1,  draw:0, img:"assets/personnages/isshin-kurosaki.png"},
  {n:"Masaki Kurosaki",       r:"Quincy",    sx:"F", arc:"Le Shinigami Remplaçant (1)",       af:"Karakura",    d:4, st:"Mort",      hc:"Brun",   bday:"09/06", w:0,  l:0,  draw:0, img:"assets/personnages/masaki-kurosaki.png"},
  {n:"Ichigo Kurosaki",       r:"Humain",    sx:"M", arc:"Le Shinigami Remplaçant (1)",       af:"Karakura",    d:5, st:"Vivant",    hc:"Roux",   bday:"15/07", w:28, l:6,  draw:2, img:"assets/personnages/ichigo-kurosaki.png"},
  {n:"Karin Kurosaki",        r:"Humain",    sx:"F", arc:"Le Shinigami Remplaçant (1)",       af:"Karakura",    d:1, st:"Vivant",    hc:"Noir",   bday:"06/05", w:0,  l:0,  draw:0, img:"assets/personnages/karin-kurosaki.png"},
  {n:"Yuzu Kurosaki",         r:"Humain",    sx:"F", arc:"Le Shinigami Remplaçant (1)",       af:"Karakura",    d:1, st:"Vivant",    hc:"Blond",   bday:"06/05", w:0,  l:0,  draw:0, img:"assets/personnages/yuzu-kurosaki.png"},
  {n:"Kon",                   r:"Mod-Soul/Âme artificielle", sx:"M", arc:"Le Shinigami Remplaçant (1)",       af:"Karakura",    d:1, st:"Vivant",    hc:"Blond",  bday:"30/12", w:1,  l:3,  draw:0, img:"assets/personnages/kon.jpg"},

  // ============================================================
  // AMIS
  // ============================================================
  {n:"Orihime Inoue",         r:"Fullbring", sx:"F", arc:"Le Shinigami Remplaçant (1)",       af:"Karakura",    d:3, st:"Vivant",    hc:"Roux",   bday:"03/09", w:2,  l:5,  draw:1, img:"assets/personnages/orihime-inoue.png"},
  {n:"Yasutora Sado",         r:"Fullbring", sx:"M", arc:"Le Shinigami Remplaçant (1)",       af:"Karakura",    d:3, st:"Vivant",    hc:"Brun",   bday:"07/04", w:6,  l:4,  draw:0, img:"assets/personnages/yasutora-sado.png"},
  {n:"Uryuu Ishida",          r:"Quincy",    sx:"M", arc:"Le Shinigami Remplaçant (1)",       af:"Karakura",    d:4, st:"Vivant",    hc:"Noir",   bday:"06/11", w:8,  l:4,  draw:1, img:"assets/personnages/uryu-ishida.png"},
  
  // ============================================================
  // HUMAINS DE KARAKURA
  // ============================================================
  {n:"Don Kanonji",           r:"Humain",    sx:"M", arc:"Le Shinigami Remplaçant (1)",       af:"Karakura",    d:1, st:"Vivant",    hc:"Brun",   bday:"23/03", w:0,  l:0,  draw:0, img:"assets/personnages/don-kanonji.png"},
  {n:"Tatsuki Arisawa",       r:"Humain",    sx:"F", arc:"Le Shinigami Remplaçant (1)",       af:"Karakura",    d:3, st:"Vivant",    hc:"Noir",   bday:"17/07", w:1,  l:0,  draw:0, img:"assets/personnages/tatsuki-arisawa.png"},
  {n:"Keigo Asano",           r:"Humain",    sx:"M", arc:"Le Shinigami Remplaçant (1)",       af:"Karakura",    d:1, st:"Vivant",    hc:"Brun",   bday:"01/04", w:0,  l:0,  draw:0, img:"assets/personnages/keigo-asano.png"},
  {n:"Mizuiro Kojima",        r:"Humain",    sx:"M", arc:"Le Shinigami Remplaçant (1)",       af:"Karakura",    d:1, st:"Vivant",    hc:"Noir",   bday:"23/05", w:0,  l:0,  draw:0, img:"assets/personnages/mizuiro-kojima.png"},
  {n:"Chizuru Honsho",        r:"Humain",    sx:"F", arc:"Le Shinigami Remplaçant (1)",       af:"Karakura",    d:1, st:"Vivant",    hc:"Rouge",   bday:"13/04", w:0,  l:0,  draw:0, img:"assets/personnages/chizuru-honsho.png"},

  // ============================================================
  // ÂMES
  // ============================================================
  {n:"Ganju Shiba",           r:"Humain",    sx:"M", arc:"Soul Society : L'Invasion (2.1)",   af:"Indépendant", d:2, st:"Vivant",    hc:"Noir",   bday:"15/10", w:2,  l:2,  draw:0, img:"assets/personnages/ganju-shiba.webp"},
  {n:"Kukaku Shiba",          r:"Humain",    sx:"F", arc:"Soul Society : L'Invasion (2.1)",   af:"Indépendant", d:3, st:"Vivant",    hc:"Noir",   bday:"01/09", w:1,  l:0,  draw:0, img:"assets/personnages/shiba-kukaku.webp"},

  // ============================================================
  // URAHARA SHOP
  // ============================================================
  {n:"Kisuke Urahara",        r:"Shinigami",                   sx:"M", arc:"Le Shinigami Remplaçant (1)",       af:"Indépendant", d:5, st:"Vivant",    hc:"Blond",  bday:"10/05", w:10, l:1,  draw:1, img:"assets/personnages/kisuke-urahara.png"},
  {n:"Yoruichi Shihoin",      r:"Shinigami",                   sx:"F", arc:"Le Shinigami Remplaçant (1)",       af:"Indépendant", d:5, st:"Vivant",    hc:"Violet", bday:"11/02", w:8,  l:1,  draw:0, img:"assets/personnages/yoruichi-shihoin.png"},
  {n:"Tessai Tsukabishi",     r:"Shinigami",                   sx:"M", arc:"Le Shinigami Remplaçant (1)",       af:"Indépendant", d:4, st:"Vivant",    hc:"Noir",   bday:"12/05", w:2,  l:0,  draw:0, img:"assets/personnages/tessai-tsukabishi.png"},
  {n:"Jinta Hanakari",        r:"Mod-Soul/Âme artificielle",   sx:"M", arc:"Le Shinigami Remplaçant (1)",       af:"Indépendant", d:1, st:"Vivant",    hc:"Rouge",  bday:"04/04", w:0,  l:1,  draw:0, img:"assets/personnages/jinta-hanakari.png"},
  {n:"Ururu Tsumugiya",       r:"Mod-Soul/Âme artificielle",   sx:"F", arc:"Le Shinigami Remplaçant (1)",       af:"Indépendant", d:2, st:"Vivant",    hc:"Noir",   bday:"09/09", w:1,  l:1,  draw:0, img:"assets/personnages/ururu-tsumugiya.png"},

  // ============================================================
  // DIVISION ZÉRO — ROYAL GUARD
  // ============================================================
  {n:"Ichibei Hyosube",       r:"Shinigami",sx:"M", arc:"Guerre Sanglante de Mille Ans (5)", af:"Division Zero", d:5, st:"Vivant",    hc:"Chauve",  bday:"01/01", w:4,  l:0,  draw:0, img:"assets/personnages/ichibe-hyosube.png"},
  {n:"Oetsu Nimaiya",         r:"Shinigami",sx:"M", arc:"Guerre Sanglante de Mille Ans (5)", af:"Division Zero", d:5, st:"Vivant",    hc:"Noir",    bday:"18/08", w:3,  l:0,  draw:0, img:"assets/personnages/oetsu-nimaiya.png"},
  {n:"Tenjiro Kirinji",       r:"Shinigami",sx:"M", arc:"Guerre Sanglante de Mille Ans (5)", af:"Division Zero", d:5, st:"Vivant",    hc:"Noir",    bday:"31/05", w:2,  l:0,  draw:0, img:"assets/personnages/tenjiro-kirinji.png"},
  {n:"Kirio Hikifune",        r:"Shinigami",sx:"F", arc:"Guerre Sanglante de Mille Ans (5)", af:"Division Zero", d:5, st:"Vivant",    hc:"Violet",  bday:"16/12", w:2,  l:0,  draw:0, img:"assets/personnages/kirio-hikifune.png"},
  {n:"Shutara Senjumaru",     r:"Shinigami",sx:"F", arc:"Guerre Sanglante de Mille Ans (5)", af:"Division Zero", d:5, st:"Vivant",    hc:"Noir",    bday:"01/11", w:2,  l:0,  draw:0, img:"assets/personnages/senjumaru-shutara.png"},

  // ============================================================
  // GOTEI 13 — CAPITAINES
  // ============================================================
  {n:"Shunsui Kyoraku",       r:"Shinigami",sx:"M", arc:"Soul Society : L'Invasion (2.1)",                 af:"Gotei 13",    d:5, st:"Vivant",    hc:"Brun",   bday:"11/07", w:6,  l:1,  draw:1, img:"assets/personnages/shunsui-kyoraku.png"},
  {n:"Soi Fon",               r:"Shinigami",sx:"F", arc:"Soul Society : L'Invasion (2.1)",                 af:"Gotei 13",    d:4, st:"Vivant",    hc:"Noir",   bday:"11/02", w:5,  l:2,  draw:1, img:"assets/personnages/sui-feng.png"},
  {n:"Rose Otoribashi",       r:"Vizard",   sx:"M", arc:"Arrancar : Bataille de Karakura (3.3)",           af:"Gotei 13",    d:4, st:"Vivant",    hc:"Blond",  bday:"17/03", w:2,  l:2,  draw:0, img:"assets/personnages/rojuro-otoribashi.png"},
  {n:"Isane Kotetsu",         r:"Shinigami",sx:"F", arc:"Soul Society : L'Invasion (2.1)",                 af:"Gotei 13",    d:3, st:"Vivant",    hc:"Gris",   bday:"02/08", w:1,  l:1,  draw:0, img:"assets/personnages/isane-kotetsu.png"},
  {n:"Shinji Hirako",         r:"Vizard",   sx:"M", arc:"Arrancar : Invasion du monde des humains (3.1)",  af:"Gotei 13",    d:4, st:"Vivant",    hc:"Blond",  bday:"10/05", w:3,  l:2,  draw:0, img:"assets/personnages/shinji-hirako.png"},
  {n:"Byakuya Kuchiki",       r:"Shinigami",sx:"M", arc:"Le Shinigami Remplaçant (1)",                     af:"Gotei 13",    d:5, st:"Vivant",    hc:"Noir",   bday:"31/01", w:8,  l:3,  draw:0, img:"assets/personnages/byakuya-kuchiki.png"},
  {n:"Tetsuzaemon Iba",       r:"Shinigami",sx:"M", arc:"Soul Society : L'Invasion (2.1)",                 af:"Gotei 13",    d:4, st:"Vivant",    hc:"Noir",   bday:"18/07", w:0,  l:0,  draw:1, img:"assets/personnages/tetsuzaemon-iba.png"},
  {n:"Lisa Yadomaru",         r:"Vizard",   sx:"F", arc:"Arrancar : Bataille de Karakura (3.3)",           af:"Gotei 13",    d:4, st:"Vivant",    hc:"Noir",   bday:"03/02", w:2,  l:2,  draw:0, img:"assets/personnages/lisa-yadomaru.png"},
  {n:"Kensei Muguruma",       r:"Vizard",   sx:"M", arc:"Arrancar : Bataille de Karakura (3.3)",           af:"Gotei 13",    d:4, st:"Vivant",    hc:"Gris",   bday:"30/07", w:3,  l:2,  draw:0, img:"assets/personnages/kensei-muguruma.png"},
  {n:"Toshiro Hitsugaya",     r:"Shinigami",sx:"M", arc:"Soul Society : L'Invasion (2.1)",                 af:"Gotei 13",    d:5, st:"Vivant",    hc:"Blanc",  bday:"20/12", w:7,  l:3,  draw:0, img:"assets/personnages/toshiro-hitsugaya.png"},
  {n:"Kenpachi Zaraki",       r:"Shinigami",sx:"M", arc:"Soul Society : L'Invasion (2.1)",                 af:"Gotei 13",    d:5, st:"Vivant",    hc:"Noir",   bday:"19/11", w:9,  l:2,  draw:1, img:"assets/personnages/kenpachi-zaraki.png"},
  {n:"Mayuri Kurotsuchi",     r:"Shinigami",sx:"M", arc:"Soul Society : L'Invasion (2.1)",                 af:"Gotei 13",    d:4, st:"Vivant",    hc:"Noir",   bday:"30/03", w:6,  l:1,  draw:0, img:"assets/personnages/mayuri-kurotsuchi.png"},
  {n:"Rukia Kuchiki",         r:"Shinigami",sx:"F", arc:"Le Shinigami Remplaçant (1)",                     af:"Gotei 13",    d:4, st:"Vivant",    hc:"Noir",   bday:"14/01", w:9,  l:3,  draw:0, img:"assets/personnages/rukia-kuchiki.png"},

  // ============================================================
  // GOTEI 13 — ANCIENS CAPITAINES
  // ============================================================
  {n:"Genryusai Yamamoto",    r:"Shinigami", sx:"M", arc:"Soul Society : L'Invasion (2.1)",  af:"Gotei 13",    d:5, st:"Mort",      hc:"Chauve", bday:"21/01", w:5,  l:1,  draw:0, img:"assets/personnages/genryusai-shigekuni-yamamoto.png"},
  {n:"Retsu Unohana",         r:"Shinigami", sx:"F", arc:"Soul Society : L'Invasion (2.1)",  af:"Gotei 13",    d:5, st:"Mort",      hc:"Noir",   bday:"21/04", w:3,  l:1,  draw:0, img:"assets/personnages/retsu-unohana.png"},
  {n:"Sosuke Aizen",          r:"Shinigami", sx:"M", arc:"Soul Society : L'Invasion (2.1)",  af:"Indépendant", d:5, st:"Vivant",    hc:"Brun",   bday:"29/05", w:12, l:1,  draw:0, img:"assets/personnages/sosuke-aizen.png"},
  {n:"Sajin Komamura",        r:"Shinigami", sx:"M", arc:"Soul Society : L'Invasion (2.1)",  af:"Gotei 13",    d:4, st:"Incertain", hc:"Brun",   bday:"23/08", w:4,  l:3,  draw:0, img:"assets/personnages/sajin-komamura.png"},
  {n:"Kaname Tousen",         r:"Shinigami", sx:"M", arc:"Soul Society : L'Invasion (2.1)",  af:"Indépendant", d:4, st:"Mort",      hc:"Brun",   bday:"13/10", w:3,  l:2,  draw:0, img:"assets/personnages/kaname-tousen.webp"},
  {n:"Gin Ichimaru",          r:"Shinigami", sx:"M", arc:"Soul Society : L'Invasion (2.1)",  af:"Indépendant", d:5, st:"Mort",      hc:"Gris",   bday:"10/09", w:4,  l:1,  draw:0, img:"assets/personnages/gin-ichimaru.png"},
  {n:"Jushiro Ukitake",       r:"Shinigami", sx:"M", arc:"Soul Society : L'Invasion (2.1)",  af:"Gotei 13",    d:4, st:"Mort",      hc:"Blanc",  bday:"21/12", w:2,  l:1,  draw:1, img:"assets/personnages/jushiro-ukitake.png"},
 
  // ============================================================
  // GOTEI 13 — VICE-CAPITAINES
  // ============================================================
  {n:"Nanao Ise",             r:"Shinigami", sx:"F", arc:"Soul Society : L'Invasion (2.1)",       af:"Gotei 13",    d:3, st:"Vivant",    hc:"Noir",   bday:"07/07", w:2,  l:1,  draw:0, img:"assets/personnages/nanao-ise.png"},
  {n:"Genshiro Okikiba",      r:"Shinigami", sx:"M", arc:"Guerre Sanglante de Mille Ans (5)",     af:"Gotei 13",    d:2, st:"Vivant",    hc:"Blanc",  bday:"??/??", w:1,  l:0,  draw:0, img:"assets/personnages/genshiro-okikiba.png"},
  {n:"Marechiyo Omaeda",      r:"Shinigami", sx:"M", arc:"Soul Society : L'Invasion (2.1)",       af:"Gotei 13",    d:2, st:"Vivant",    hc:"Noir",   bday:"05/05", w:1,  l:2,  draw:0, img:"assets/personnages/marechiyo-omaeda.png"},
  {n:"Izuru Kira",            r:"Shinigami", sx:"M", arc:"Soul Society : L'Invasion (2.1)",       af:"Gotei 13",    d:3, st:"Incertain", hc:"Blond",  bday:"27/03", w:3,  l:3,  draw:0, img:"assets/personnages/izuru-kira.png"},
  {n:"Kiyone Kotetsu",        r:"Shinigami", sx:"F", arc:"Soul Society : Le Sauvetage (2.2)",     af:"Gotei 13",    d:2, st:"Vivant",    hc:"Blond",  bday:"22/09", w:1,  l:1,  draw:0, img:"assets/personnages/kiyone-kotetsu.png"},
  {n:"Momo Hinamori",         r:"Shinigami", sx:"F", arc:"Soul Society : L'Invasion (2.1)",       af:"Gotei 13",    d:3, st:"Vivant",    hc:"Noir",   bday:"03/06", w:2,  l:3,  draw:0, img:"assets/personnages/momo-hinamori.png"},
  {n:"Renji Abarai",          r:"Shinigami", sx:"M", arc:"Le Shinigami Remplaçant (1)",           af:"Gotei 13",    d:4, st:"Vivant",    hc:"Rouge",  bday:"31/08", w:7,  l:5,  draw:0, img:"assets/personnages/renji-abarai.png"},
  {n:"Atau Rindo",            r:"Shinigami", sx:"M", arc:"NO BREATHES FROM HELL (6)",             af:"Gotei 13",    d:2, st:"Vivant",    hc:"Noir",   bday:"??/??", w:0,  l:0,  draw:0, img:"assets/personnages/atau-rindo.png"},
  {n:"Yuyu Yayahara",         r:"Shinigami", sx:"F", arc:"NO BREATHES FROM HELL (6)",             af:"Gotei 13",    d:2, st:"Vivant",    hc:"Blond",  bday:"??/??", w:0,  l:0,  draw:0, img:"assets/personnages/yuyu-yayahara.png"},
  {n:"Shuhei Hisagi",         r:"Shinigami", sx:"M", arc:"Soul Society : L'Invasion (2.1)",       af:"Gotei 13",    d:3, st:"Vivant",    hc:"Noir",   bday:"14/08", w:3,  l:3,  draw:0, img:"assets/personnages/shuhei-hisagi.png"},
  {n:"Mashiro Kuna",          r:"Vizard",    sx:"F", arc:"Arrancar : Bataille de Karakura (3.3)", af:"Gotei 13",    d:3, st:"Vivant",    hc:"Vert",   bday:"01/01", w:2,  l:1,  draw:0, img:"assets/personnages/mashiro-kuna.png"},
  {n:"Rangiku Matsumoto",     r:"Shinigami", sx:"F", arc:"Soul Society : L'Invasion (2.1)",       af:"Gotei 13",    d:3, st:"Vivant",    hc:"Blond",  bday:"25/05", w:3,  l:3,  draw:0, img:"assets/personnages/rangiku-matsumoto.png"},
  {n:"Ikkaku Madarame",       r:"Shinigami", sx:"M", arc:"Soul Society : Le Sauvetage (2.2)",     af:"Gotei 13",    d:3, st:"Vivant",    hc:"Chauve", bday:"09/11", w:4,  l:3,  draw:0, img:"assets/personnages/ikkaku-madarame.png"},
  {n:"Akon",                  r:"Shinigami", sx:"M", arc:"Guerre Sanglante de Mille Ans (5)",     af:"Gotei 13",    d:2, st:"Vivant",    hc:"Noir",   bday:"??/??", w:1,  l:0,  draw:0, img:"assets/personnages/akon.png"},
  {n:"Sentaro Kotsubaki",     r:"Shinigami", sx:"M", arc:"Soul Society : Le Sauvetage (2.2)",     af:"Gotei 13",    d:2, st:"Vivant",    hc:"Noir",   bday:"22/09", w:1,  l:1,  draw:0, img:"assets/personnages/sentaro-kotsubaki.png"},
 
  // ============================================================
  // GOTEI 13 — ANCIENS VICE-CAPITAINES
  // ============================================================
  {n:"Chojiro Sasakibe",      r:"Shinigami",                  sx:"M", arc:"Soul Society : L'Invasion (2.1)",   af:"Gotei 13",    d:3, st:"Mort",      hc:"Blanc",  bday:"04/11", w:0,  l:1,  draw:0, img:"assets/personnages/chojiro-sasakibe.png"},
  {n:"Yachiru Kusajishi",     r:"Shinigami",                  sx:"F", arc:"Soul Society : Le Sauvetage (2.2)", af:"Gotei 13",    d:4, st:"Incertain", hc:"Rose",   bday:"12/02", w:2,  l:0,  draw:1, img:"assets/personnages/yachiru-kusajishi.png"},
  {n:"Nemu Kurotsuchi",       r:"Mod-Soul/Âme artificielle",  sx:"F", arc:"Soul Society : L'Invasion (2.1)",   af:"Gotei 13",    d:3, st:"Mort",      hc:"Noir",   bday:"30/03", w:2,  l:2,  draw:0, img:"assets/personnages/nemu-kurotsuchi.png"},
 
  // ============================================================
  // GOTEI 13 — AUTRES MEMBRES NOTABLES
  // ============================================================
  {n:"Yumichika Ayasegawa",   r:"Shinigami", sx:"M", arc:"Soul Society : Le Sauvetage (2.2)", af:"Gotei 13",    d:3, st:"Vivant",    hc:"Noir",   bday:"19/09", w:3,  l:1,  draw:0, img:"assets/personnages/yumichika-ayasegawa.png"},
  {n:"Hanataro Yamada",       r:"Shinigami", sx:"M", arc:"Soul Society : Le Sauvetage (2.2)", af:"Gotei 13",    d:1, st:"Vivant",    hc:"Noir",   bday:"01/04", w:1,  l:1,  draw:0, img:"assets/personnages/hanataro-yamada.png"},
 
  // ============================================================
  // VIZARDS (non promus à la fin)
  // ============================================================
  {n:"Hiyori Sarugaki",       r:"Vizard",    sx:"F", arc:"Arrancar : Invasion du monde des humains (3.1)", af:"Indépendant", d:3, st:"Vivant",    hc:"Blond",  bday:"01/08", w:2,  l:2,  draw:0, img:"assets/personnages/hiyori-sarugaki.png"},
  {n:"Love Aikawa",           r:"Vizard",    sx:"M", arc:"Arrancar : Bataille de Karakura (3.3)",          af:"Indépendant", d:4, st:"Vivant",    hc:"Noir",   bday:"10/10", w:2,  l:2,  draw:0, img:"assets/personnages/love-aikawa.png"},
  {n:"Hachigen Ushoda",       r:"Vizard",    sx:"M", arc:"Arrancar : Bataille de Karakura (3.3)",          af:"Indépendant", d:4, st:"Vivant",    hc:"Rose",   bday:"08/09", w:2,  l:1,  draw:0, img:"assets/personnages/hachigen-ushoda.png"},
 
  // ============================================================
  // ESPADA (par numéro tatoué : 1 → 10)
  // ============================================================
  {n:"Coyote Starrk",         r:"Arrancar",  sx:"M", arc:"Arrancar : Invasion du monde des humains (3.1)", af:"Espada",      d:5, st:"Mort",      hc:"Brun",   bday:"19/01", w:4,  l:1,  draw:0, img:"assets/personnages/coyote-starrk.png"},
  {n:"Lilynette Gingerbuck",  r:"Arrancar",  sx:"F", arc:"Arrancar : Invasion du monde des humains (3.1)", af:"Espada",      d:4, st:"Mort",      hc:"Vert",   bday:"19/01", w:2,  l:1,  draw:0, img:"assets/personnages/lilynette-gingerbuck.png"},
  {n:"Baraggan Louisenbairn", r:"Arrancar",  sx:"M", arc:"Arrancar : Bataille de Karakura (3.3)",          af:"Espada",      d:5, st:"Mort",      hc:"Blanc",  bday:"09/02", w:3,  l:1,  draw:0, img:"assets/personnages/baraggan-louisenbairn.png"},
  {n:"Tier Harribel",         r:"Arrancar",  sx:"F", arc:"Arrancar : Bataille de Karakura (3.3)",          af:"Espada",      d:5, st:"Vivant",    hc:"Blond",  bday:"25/07", w:3,  l:1,  draw:0, img:"assets/personnages/tier-harribel.png"},
  {n:"Ulquiorra Cifer",       r:"Arrancar",  sx:"M", arc:"Arrancar : Invasion du monde des humains (3.1)", af:"Espada",      d:5, st:"Mort",      hc:"Noir",   bday:"01/12", w:5,  l:1,  draw:0, img:"assets/personnages/ulquiorra-cifer.png"},
  {n:"Nnoitra Gilga",         r:"Arrancar",  sx:"M", arc:"Arrancar : Invasion du Hueco Mundo (3.2)",       af:"Espada",      d:5, st:"Mort",      hc:"Noir",   bday:"11/11", w:4,  l:1,  draw:0, img:"assets/personnages/nnoitra-gilga.png"},
  {n:"Grimmjow Jaegerjaquez", r:"Arrancar",  sx:"M", arc:"Arrancar : Invasion du monde des humains (3.1)", af:"Espada",      d:5, st:"Vivant",    hc:"Bleu",   bday:"31/07", w:4,  l:2,  draw:0, img:"assets/personnages/grimmjow-jaegerjaquez.png"},
  {n:"Zommari Rureaux",       r:"Arrancar",  sx:"M", arc:"Arrancar : Invasion du Hueco Mundo (3.2)",       af:"Espada",      d:4, st:"Mort",      hc:"Chauve", bday:"13/10", w:2,  l:1,  draw:0, img:"assets/personnages/zommari-rureaux.png"},
  {n:"Szayelaporro Grantz",   r:"Arrancar",  sx:"M", arc:"Arrancar : Invasion du Hueco Mundo (3.2)",       af:"Espada",      d:4, st:"Mort",      hc:"Rose",   bday:"22/06", w:3,  l:1,  draw:0, img:"assets/personnages/szayelaporro-granz.png"},
  {n:"Aaroniero Arruruerie",  r:"Arrancar",  sx:"M", arc:"Arrancar : Invasion du Hueco Mundo (3.2)",       af:"Espada",      d:4, st:"Mort",      hc:"Chauve", bday:"23/04", w:2,  l:1,  draw:0, img:"assets/personnages/aaroniero-arruruerie.png"},
  {n:"Yammy Llargo",          r:"Arrancar",  sx:"M", arc:"Arrancar : Invasion du monde des humains (3.1)", af:"Espada",      d:5, st:"Mort",      hc:"Chauve", bday:"??/??", w:3,  l:1,  draw:0, img:"assets/personnages/yammy-llargo.png"},
 
  // ============================================================
  // EX-ESPADA & ARRANCAR NOTABLES
  // ============================================================
  {n:"Kukkapuro",                r:"Arrancar", sx:"M", arc:"Arrancar : Invasion du Hueco Mundo (3.2)", af:"Hueco Mundo", d:5, st:"Vivant",    hc:"Chauve", bday:"04/04", w:0,  l:0,  draw:0, img:"assets/personnages/kukkapuro.png"},
  {n:"Nelliel Tu Odelschwanck",  r:"Arrancar", sx:"F", arc:"Arrancar : Invasion du Hueco Mundo (3.2)", af:"Hueco Mundo", d:5, st:"Vivant",    hc:"Vert",   bday:"24/04", w:4,  l:1,  draw:0, img:"assets/personnages/nelliel-tu-odelschwanck.png"},
  {n:"Luppi Antenor",            r:"Arrancar", sx:"M", arc:"Arrancar : Invasion du monde des humains (3.1)", af:"Espada", d:3, st:"Mort",      hc:"Noir",   bday:"05/06", w:1,  l:1,  draw:0, img:"assets/personnages/luppi-antenor.png"},
  {n:"Wonderweiss Margela",      r:"Arrancar", sx:"M", arc:"Arrancar : Bataille de Karakura (3.3)",    af:"Espada",      d:4, st:"Mort",      hc:"Blond",  bday:"06/07", w:2,  l:1,  draw:0, img:"assets/personnages/wonderweiss-margela.png"},
 
  // ============================================================
  // FRACCIÓN DE HARRIBEL (Espada 3)
  // ============================================================
  {n:"Franceska Mila Rose",   r:"Arrancar",  sx:"F", arc:"Arrancar : Invasion du monde des humains (3.1)", af:"Espada",      d:3, st:"Vivant",    hc:"Brun",   bday:"17/08", w:1,  l:1,  draw:0, img:"assets/personnages/franceska-mila-rose.png"},
  {n:"Apache",                r:"Arrancar",  sx:"F", arc:"Arrancar : Invasion du monde des humains (3.1)", af:"Espada",      d:3, st:"Vivant",    hc:"Noir",   bday:"17/05", w:1,  l:1,  draw:0, img:"assets/personnages/apacci.webp"},
  {n:"Sun-Sun",               r:"Arrancar",  sx:"F", arc:"Arrancar : Invasion du monde des humains (3.1)", af:"Espada",      d:3, st:"Vivant",    hc:"Vert",   bday:"17/02", w:1,  l:1,  draw:0, img:"assets/personnages/cyan-sung-sun.png"},
 
  // ============================================================
  // ARRANCAR DIVERS
  // ============================================================
  {n:"Loly Aivirrne",         r:"Arrancar",  sx:"F", arc:"Arrancar : Invasion du Hueco Mundo (3.2)",       af:"Espada",      d:2, st:"Vivant",    hc:"Noir",   bday:"27/01", w:0,  l:2,  draw:0, img:"assets/personnages/loly-aivirrne.png"},
  {n:"Menoly Mallia",         r:"Arrancar",  sx:"F", arc:"Arrancar : Invasion du Hueco Mundo (3.2)",       af:"Espada",      d:2, st:"Incertain", hc:"Blond",  bday:"07/12", w:0,  l:2,  draw:0, img:"assets/personnages/menoly-mallia.png"},
  {n:"Shawlong Koufang",      r:"Arrancar",  sx:"M", arc:"Arrancar : Invasion du monde des humains (3.1)", af:"Espada",      d:3, st:"Mort",      hc:"Noir",   bday:"04/11", w:1,  l:1,  draw:0, img:"assets/personnages/shawlong-koufang.png"},
  {n:"Findorr Calius",        r:"Arrancar",  sx:"M", arc:"Arrancar : Bataille de Karakura (3.3)",          af:"Espada",      d:3, st:"Mort",      hc:"Blond",  bday:"27/06", w:1,  l:1,  draw:0, img:"assets/personnages/findorr-calius.png"},
  {n:"Charlotte Cuuhlhourne", r:"Arrancar",  sx:"M", arc:"Arrancar : Bataille de Karakura (3.3)",          af:"Espada",      d:3, st:"Mort",      hc:"Violet", bday:"08/08", w:1,  l:1,  draw:0, img:"assets/personnages/charlotte-cuuhlhourne.png"},
  {n:"Dordoni Alessandro",    r:"Arrancar",  sx:"M", arc:"Arrancar : Invasion du Hueco Mundo (3.2)",       af:"Hueco Mundo", d:3, st:"Mort",      hc:"Noir",   bday:"28/08", w:2,  l:2,  draw:0, img:"assets/personnages/dordoni-alessandro-del-socaccio.png"},
  {n:"Cirucci Sanderwicci",   r:"Arrancar",  sx:"F", arc:"Arrancar : Invasion du Hueco Mundo (3.2)",       af:"Hueco Mundo", d:3, st:"Mort",      hc:"Violet", bday:"27/02", w:1,  l:1,  draw:0, img:"assets/personnages/cirucci-sanderwicci.png"},
  {n:"Gantenbainne Mosqueda", r:"Arrancar",  sx:"M", arc:"Arrancar : Invasion du Hueco Mundo (3.2)",       af:"Hueco Mundo", d:3, st:"Mort",      hc:"Roux",   bday:"21/09", w:1,  l:1,  draw:0, img:"assets/personnages/gantenbainne-mosqueda.png"},
  {n:"Pesche Guatiche",       r:"Arrancar",  sx:"M", arc:"Arrancar : Invasion du Hueco Mundo (3.2)",       af:"Hueco Mundo", d:2, st:"Vivant",    hc:"Blond",  bday:"25/05", w:0,  l:1,  draw:0, img:"assets/personnages/pesche-guatiche.png"},
  {n:"Dondochakka Birstanne", r:"Arrancar",  sx:"M", arc:"Arrancar : Invasion du Hueco Mundo (3.2)",       af:"Hueco Mundo", d:2, st:"Vivant",    hc:"Chauve", bday:"30/06", w:0,  l:1,  draw:0, img:"assets/personnages/dondochakka-birstanne.png"},
 
  // ============================================================
  // HOLLOWS
  // ============================================================
  {n:"Grand Fisher",          r:"Hollow",    sx:"M", arc:"Le Shinigami Remplaçant (1)",              af:"Hueco Mundo", d:3, st:"Mort",      hc:"Noir",   bday:"??/??", w:2,  l:1,  draw:0, img:"assets/personnages/grand-fisher.webp"},
  {n:"Acidwire",              r:"Hollow",    sx:"M", arc:"Le Shinigami Remplaçant (1)",              af:"Hueco Mundo", d:1, st:"Mort",      hc:"Noir",   bday:"??/??", w:0,  l:1,  draw:0, img:"assets/personnages/acidwire.png"},
  {n:"Shrieker",              r:"Hollow",    sx:"M", arc:"Le Shinigami Remplaçant (1)",              af:"Hueco Mundo", d:2, st:"Mort",      hc:"Chauve", bday:"??/??", w:1,  l:1,  draw:0, img:"assets/personnages/shrieker.webp"},
  {n:"Metastacia",            r:"Hollow",    sx:"M", arc:"Soul Society : Le Sauvetage (2.2)",        af:"Hueco Mundo", d:3, st:"Mort",      hc:"Chauve", bday:"??/??", w:1,  l:1,  draw:0, img:"assets/personnages/metaastacia.jpg"},
  {n:"Runuganga",             r:"Hollow",    sx:"M", arc:"Arrancar : Invasion du Hueco Mundo (3.2)", af:"Hueco Mundo", d:2, st:"Mort",      hc:"Chauve", bday:"??/??", w:0,  l:1,  draw:0, img:"assets/personnages/runuganga.webp"},
  {n:"Fishbone D",            r:"Hollow",    sx:"M", arc:"Le Shinigami Remplaçant (1)",              af:"Hueco Mundo", d:1, st:"Mort",      hc:"Chauve", bday:"??/??", w:0,  l:1,  draw:0, img:"assets/personnages/fishbone-d.webp"},
  {n:"Bulbous G",             r:"Hollow",    sx:"M", arc:"Le Shinigami Remplaçant (1)",              af:"Hueco Mundo", d:2, st:"Mort",      hc:"Chauve", bday:"??/??", w:0,  l:1,  draw:0, img:"assets/personnages/bublous-g.webp"},
  {n:"Hexapodus",             r:"Hollow",    sx:"M", arc:"Le Shinigami Remplaçant (1)",              af:"Hueco Mundo", d:2, st:"Mort",      hc:"Chauve", bday:"??/??", w:0,  l:1,  draw:0, img:"assets/personnages/hexapodus.webp"},
 
  // ============================================================
  // FULLBRING — XCUTION
  // ============================================================
  {n:"Kugo Ginjo",            r:"Fullbring", sx:"M", arc:"Arc Fullbringers (4)", af:"Xcution",     d:4, st:"Mort",      hc:"Brun",   bday:"15/11", w:4,  l:2,  draw:0, img:"assets/personnages/kugo-ginjo.png"},
  {n:"Shukuro Tsukishima",    r:"Fullbring", sx:"M", arc:"Arc Fullbringers (4)", af:"Xcution",     d:4, st:"Mort",      hc:"Brun",   bday:"04/02", w:4,  l:1,  draw:0, img:"assets/personnages/shukuro-tsukishima.png"},
  {n:"Riruka Dokugamine",     r:"Fullbring", sx:"F", arc:"Arc Fullbringers (4)", af:"Xcution",     d:3, st:"Vivant",    hc:"Rose",   bday:"14/04", w:1,  l:1,  draw:0, img:"assets/personnages/riruka-dokugamine.png"},
  {n:"Yukio Hans Vorarlberna",r:"Fullbring", sx:"M", arc:"Arc Fullbringers (4)", af:"Xcution",     d:3, st:"Vivant",    hc:"Blond",  bday:"23/12", w:1,  l:1,  draw:0, img:"assets/personnages/yukio-hans-vorarlberna.png"},
  {n:"Jackie Tristan",        r:"Fullbring", sx:"F", arc:"Arc Fullbringers (4)", af:"Xcution",     d:3, st:"Vivant",    hc:"Noir",   bday:"??/??", w:1,  l:1,  draw:0, img:"assets/personnages/jackie-tristan.png"},
  {n:"Giriko Kutsuzawa",      r:"Fullbring", sx:"M", arc:"Arc Fullbringers (4)", af:"Xcution",     d:3, st:"Mort",      hc:"Noir",   bday:"??/??", w:1,  l:1,  draw:0, img:"assets/personnages/giriko-kutsuzawa.png"},
  {n:"Moe Shishigawara",      r:"Fullbring", sx:"M", arc:"Arc Fullbringers (4)", af:"Xcution",     d:2, st:"Vivant",    hc:"Noir",   bday:"??/??", w:1,  l:1,  draw:0, img:"assets/personnages/moe-shishigawara.png"},
 
  // ============================================================
  // WANDENREICH
  // ============================================================
  {n:"Yhwach",                r:"Quincy",    sx:"M", arc:"Guerre Sanglante de Mille Ans (5)", af:"Wandenreich", d:5, st:"Mort",      hc:"Noir",   bday:"??/??", w:8,  l:1,  draw:0, img:"assets/personnages/yhwach.webp"},
  {n:"Jugram Haschwalth",     r:"Quincy",    sx:"M", arc:"Guerre Sanglante de Mille Ans (5)", af:"Wandenreich", d:5, st:"Mort",      hc:"Blond",  bday:"05/11", w:5,  l:1,  draw:0, img:"assets/personnages/jugram-haschwalth.png"},
  {n:"Pernida Parnkgjas",     r:"Quincy",    sx:"M", arc:"Guerre Sanglante de Mille Ans (5)", af:"Wandenreich", d:5, st:"Mort",      hc:"Chauve", bday:"19/01", w:3,  l:1,  draw:0, img:"assets/personnages/pernida-parnkgjas.png"},
  {n:"Askin Nakk Le Vaar",    r:"Quincy",    sx:"M", arc:"Guerre Sanglante de Mille Ans (5)", af:"Wandenreich", d:5, st:"Mort",      hc:"Noir",   bday:"06/06", w:3,  l:1,  draw:0, img:"assets/personnages/askin-nakk-le-vaar.png"},
  {n:"Gerard Valkyrie",       r:"Quincy",    sx:"M", arc:"Guerre Sanglante de Mille Ans (5)", af:"Wandenreich", d:5, st:"Incertain", hc:"Blond",  bday:"07/01", w:3,  l:1,  draw:0, img:"assets/personnages/gerard-valkyrie.png"},
  {n:"Lille Barro",           r:"Quincy",    sx:"M", arc:"Guerre Sanglante de Mille Ans (5)", af:"Wandenreich", d:5, st:"Mort",      hc:"Blanc",  bday:"11/04", w:3,  l:1,  draw:0, img:"assets/personnages/lille-barro.png"},
  {n:"Bambietta Basterbine",  r:"Quincy",    sx:"F", arc:"Guerre Sanglante de Mille Ans (5)", af:"Wandenreich", d:4, st:"Mort",      hc:"Violet", bday:"06/08", w:2,  l:1,  draw:0, img:"assets/personnages/bambietta-basterbine.png"},
  {n:"As Nodt",               r:"Quincy",    sx:"M", arc:"Guerre Sanglante de Mille Ans (5)", af:"Wandenreich", d:5, st:"Mort",      hc:"Noir",   bday:"29/12", w:3,  l:1,  draw:0, img:"assets/personnages/as-nodt.png"},
  {n:"Liltotto Lamperd",      r:"Quincy",    sx:"F", arc:"Guerre Sanglante de Mille Ans (5)", af:"Wandenreich", d:4, st:"Vivant",    hc:"Blond",  bday:"16/09", w:3,  l:1,  draw:0, img:"assets/personnages/liltotto-lamperd.png"},
  {n:"Bazz-B",                r:"Quincy",    sx:"M", arc:"Guerre Sanglante de Mille Ans (5)", af:"Wandenreich", d:4, st:"Mort",      hc:"Rouge",  bday:"14/07", w:2,  l:2,  draw:0, img:"assets/personnages/bazz-b.png"},
  {n:"Cang Du",               r:"Quincy",    sx:"M", arc:"Guerre Sanglante de Mille Ans (5)", af:"Wandenreich", d:4, st:"Mort",      hc:"Noir",   bday:"27/05", w:2,  l:1,  draw:0, img:"assets/personnages/cang-du.png"},
  {n:"Quilge Opie",           r:"Quincy",    sx:"M", arc:"Guerre Sanglante de Mille Ans (5)", af:"Wandenreich", d:4, st:"Mort",      hc:"Noir",   bday:"01/09", w:2,  l:1,  draw:0, img:"assets/personnages/quilge-opie.png"},
  {n:"BG9",                   r:"Quincy",    sx:"M", arc:"Guerre Sanglante de Mille Ans (5)", af:"Wandenreich", d:4, st:"Mort",      hc:"Chauve", bday:"??/??", w:2,  l:1,  draw:0, img:"assets/personnages/bg9.png"},
  {n:"PePe Waccabrada",       r:"Quincy",    sx:"M", arc:"Guerre Sanglante de Mille Ans (5)", af:"Wandenreich", d:4, st:"Mort",      hc:"Chauve", bday:"03/04", w:2,  l:1,  draw:0, img:"assets/personnages/pepe-waccabrada.png"},
  {n:"Robert Accutrone",      r:"Quincy",    sx:"M", arc:"Guerre Sanglante de Mille Ans (5)", af:"Wandenreich", d:3, st:"Mort",      hc:"Brun",   bday:"??/??", w:1,  l:1,  draw:0, img:"assets/personnages/robert-accutrone.png"},
  {n:"Driscoll Berci",        r:"Quincy",    sx:"M", arc:"Guerre Sanglante de Mille Ans (5)", af:"Wandenreich", d:3, st:"Mort",      hc:"Noir",   bday:"25/03", w:1,  l:1,  draw:0, img:"assets/personnages/driscoll-berci.png"},
  {n:"Meninas McAllon",       r:"Quincy",    sx:"F", arc:"Guerre Sanglante de Mille Ans (5)", af:"Wandenreich", d:4, st:"Vivant",    hc:"Rose",   bday:"09/03", w:2,  l:1,  draw:0, img:"assets/personnages/meninas-mcallon.png"},
  {n:"Berenice Gabrielli",    r:"Quincy",    sx:"M", arc:"Guerre Sanglante de Mille Ans (5)", af:"Wandenreich", d:3, st:"Mort",      hc:"Blond",  bday:"08/02", w:1,  l:1,  draw:0, img:"assets/personnages/berenice-gabrielli.png"},
  {n:"Jerome Guizbatt",       r:"Quincy",    sx:"M", arc:"Guerre Sanglante de Mille Ans (5)", af:"Wandenreich", d:3, st:"Mort",      hc:"Noir",   bday:"25/08", w:1,  l:1,  draw:0, img:"assets/personnages/jerome-guizbatt.png"},
  {n:"Mask De Masculine",     r:"Quincy",    sx:"M", arc:"Guerre Sanglante de Mille Ans (5)", af:"Wandenreich", d:4, st:"Mort",      hc:"Blond",  bday:"20/10", w:2,  l:1,  draw:0, img:"assets/personnages/mask-de-masculine.png"},
  {n:"Candice Catnipp",       r:"Quincy",    sx:"F", arc:"Guerre Sanglante de Mille Ans (5)", af:"Wandenreich", d:4, st:"Vivant",    hc:"Vert",   bday:"07/06", w:2,  l:1,  draw:0, img:"assets/personnages/candice-catnipp.png"},
  {n:"NaNaNa Najahkoop",      r:"Quincy",    sx:"M", arc:"Guerre Sanglante de Mille Ans (5)", af:"Wandenreich", d:3, st:"Mort",      hc:"Noir",   bday:"27/02", w:1,  l:1,  draw:0, img:"assets/personnages/nanana-najahkoop.png"},
  {n:"Gremmy Thoumeaux",      r:"Quincy",    sx:"M", arc:"Guerre Sanglante de Mille Ans (5)", af:"Wandenreich", d:5, st:"Mort",      hc:"Blond",  bday:"30/06", w:2,  l:1,  draw:0, img:"assets/personnages/gremmy-thoumeaux.png"},
  {n:"Nianzol Weizol",        r:"Quincy",    sx:"M", arc:"Guerre Sanglante de Mille Ans (5)", af:"Wandenreich", d:4, st:"Mort",      hc:"Noir",   bday:"21/05", w:2,  l:1,  draw:0, img:"assets/personnages/nianzol-weizol.png"},
  {n:"Royd Lloyd",            r:"Quincy",    sx:"M", arc:"Guerre Sanglante de Mille Ans (5)", af:"Wandenreich", d:4, st:"Mort",      hc:"Chauve", bday:"28/04", w:2,  l:1,  draw:0, img:"assets/personnages/royd-lloyd.png"},
  {n:"Loyd Lloyd",            r:"Quincy",    sx:"M", arc:"Guerre Sanglante de Mille Ans (5)", af:"Wandenreich", d:3, st:"Mort",      hc:"Chauve", bday:"28/04", w:1,  l:1,  draw:0, img:"assets/personnages/loyd-lloyd.png"},
  {n:"Giselle Gewelle",       r:"Quincy",    sx:"F", arc:"Guerre Sanglante de Mille Ans (5)", af:"Wandenreich", d:4, st:"Vivant",    hc:"Noir",   bday:"24/12", w:2,  l:1,  draw:0, img:"assets/personnages/giselle-gewelle.png"},
 
];
 
