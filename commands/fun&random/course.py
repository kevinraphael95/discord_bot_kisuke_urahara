# ================================================================================
# 📌 course_kart.py
# Objectif : Course de karting (1 tour) façon Super Mario Kart (Mode 7) en GIF.
#            Circuit aléatoire, 5 rivaux, classement en direct, suspense jusqu'à la ligne
#            d'arrivée et écran de résultats. Tout est dessiné par le code.
# Catégorie : Fun
# Accès : Tous
# Cooldown : 15s (slash) / 15s (prefix)
# ================================================================================

# ================================================================================
# 📦 Modules standards
# ================================================================================
import asyncio
import io
import math
import random
from bisect import bisect_right

# ================================================================================
# 📦 Modules tiers
# ================================================================================
import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image, ImageChops, ImageDraw, ImageOps

# ================================================================================
# 📦 Modules internes
# ================================================================================
from utils.discord_anti429 import safe_send

# ================================================================================
# ⚙️ Constantes
# ================================================================================
W, H = 256, 224                     # résolution Super Nintendo
HZ = 66                             # ligne d'horizon
FOV = math.radians(72)
FOCAL = (W / 2) / math.tan(FOV / 2)
CAM_H = 40.0                        # hauteur de la caméra (en pixels de texture)
FOOT_ROW = int(H * 0.88)            # ligne où se pose le kart à l'écran
BACK = CAM_H * FOCAL / (FOOT_ROW - HZ)   # distance caméra -> kart

MAP = 1024                          # taille de la texture du circuit
ROAD_W = 62                         # largeur de la piste
STEP = 2.0                          # espacement des points de la ligne centrale

FRAMES = 160
FRAME_MS = 50
FADE_FRAMES = 6                     # fondu vers l'écran de résultats
RESULT_HOLD_MS = 7000
PALETTE_COLORS = 160
MAX_BYTES = 8 * 1024 * 1024

GRASS = (60, 176, 50)

# Pilotes : (nom, couleur principale, couleur de la combinaison). Le joueur est le premier.
RACERS = (
    ("TOI", (214, 40, 40), (40, 70, 200)),
    ("VERT", (40, 170, 60), (250, 210, 40)),
    ("JAUNE", (250, 200, 40), (200, 60, 40)),
    ("VIOLET", (140, 70, 200), (60, 60, 70)),
    ("CYAN", (40, 180, 230), (30, 60, 140)),
    ("ORANGE", (240, 130, 40), (60, 160, 60)),
)
KART_SEP = 15.0                     # écart latéral minimum entre deux karts qui se croisent (px de circuit)
KART_LONG = 30.0                    # à cette distance (devant/derrière) ils commencent à s'éviter
ROAD_LIM = 22.0                     # les karts restent dans cette bande autour du centre de la piste
PLACE_WEIGHTS = (30, 25, 18, 12, 10, 5)   # chances de finir 1er, 2e, ... 6e

# ================================================================================
# 🔤 Texte pixelisé (police PIL agrandie, avec contour)
# ================================================================================
def _text(img: Image.Image, s: str, x: int, y: int, scale: int, color, outline=(0, 0, 0), anchor="la", outline_px: int = 0) -> int:
    probe = ImageDraw.Draw(Image.new("L", (1, 1)))
    box = probe.textbbox((0, 0), s)
    w, h = box[2] + 2, box[3] + 2
    layer = Image.new("L", (w, h), 0)
    ImageDraw.Draw(layer).text((1, 1), s, fill=255)
    layer = layer.point(lambda v: 255 if v > 100 else 0).resize((w * scale, h * scale), Image.NEAREST)  # pixels nets
    if anchor == "ra":
        x -= layer.width
    elif anchor == "ma":
        x -= layer.width // 2
    if outline:
        o = outline_px or max(1, scale)
        for dx, dy in ((-o, 0), (o, 0), (0, -o), (0, o), (-o, -o), (o, o), (-o, o), (o, -o)):
            img.paste(Image.new("RGB", layer.size, outline), (x + dx, y + dy), layer)
    img.paste(Image.new("RGB", layer.size, color), (x, y), layer)
    return layer.width


# ================================================================================
# 🏎️ Sprite du kart (vu de dos, dessiné en pixel art)
# ================================================================================
KART_MAP = (
    ".....RRRRRR.....",
    "....RRRRRRRR....",
    "....RRWWWWRR....",
    "....RRRRRRRR....",
    "...BBBBBBBBBB...",
    "..BBBBBBBBBBBB..",
    "..BBBBBBBBBBBB..",
    "KK.RRRRRRRRRR.KK",
    "KK.RRRRRRRRRR.KK",
    "KKKRRWWWWWWRRKKK",
    "KKKRRRRRRRRRRKKK",
    "KKK.KKKKKKKK.KKK",
    ".KK..........KK.",
)


def _make_kart(body, suit, lean: int = 0, scale: int = 1) -> Image.Image:
    """Kart vu de dos. lean = -1/0/1 : le pilote se penche dans les virages."""
    pal = {"R": body, "B": suit, "W": (245, 245, 245), "K": (24, 24, 28)}
    img = Image.new("RGBA", (18, len(KART_MAP)), (0, 0, 0, 0))
    for y, row in enumerate(KART_MAP):
        shift = lean if y < 7 else 0
        for x, ch in enumerate(row):
            if ch in pal:
                img.putpixel((x + 1 + shift, y), pal[ch] + (255,))
    return img.resize((img.width * scale, img.height * scale), Image.NEAREST) if scale > 1 else img


# ================================================================================
# 🌄 Décor : ciel, nuages, collines rayées (défile selon le cap)
# ================================================================================
BG_LEN = int(W * 2 * math.pi / FOV)      # largeur du panorama (360°)


def _make_background(rng: random.Random) -> Image.Image:
    bg = Image.new("RGB", (BG_LEN, HZ))
    d = ImageDraw.Draw(bg)
    for y in range(HZ):
        t = y / HZ
        d.line([(0, y), (BG_LEN, y)], fill=(int(150 + 46 * t), int(190 + 34 * t), int(250 + 5 * t)))

    # nuages (répétés de chaque côté pour que le panorama boucle)
    for _ in range(9):
        cx, cy = rng.randrange(BG_LEN), rng.randint(6, 26)
        for off in (-BG_LEN, 0, BG_LEN):
            for dx, dy, rw, rh in ((0, 0, 22, 7), (-14, 3, 14, 5), (15, 3, 16, 5)):
                d.ellipse([cx + off + dx - rw, cy + dy - rh, cx + off + dx + rw, cy + dy + rh], fill=(255, 255, 255))

    # collines rondes à rayures horizontales
    hills = sorted(((rng.randrange(BG_LEN), rng.randint(70, 150), rng.randint(20, 46)) for _ in range(12)),
                   key=lambda h: h[2])
    for cx, w, h in hills:
        dark = rng.random() < 0.5
        base, light = ((30, 140, 40), (52, 172, 56)) if dark else ((44, 164, 50), (84, 200, 70))
        stripes = Image.new("RGB", (w + 1, h))
        sd = ImageDraw.Draw(stripes)
        for y in range(h):
            sd.line([(0, y), (w, y)], fill=light if (y // 3) % 2 == 0 else base)
        mask = Image.new("L", (w + 1, h), 0)
        ImageDraw.Draw(mask).ellipse([0, 0, w, 2 * h - 1], fill=255)
        for off in (-BG_LEN, 0, BG_LEN):
            bg.paste(stripes, (cx + off - w // 2, HZ - h), mask)
    return bg


# ================================================================================
# 🛣️ Circuit aléatoire (texture vue du dessus)
# ================================================================================
def _speckle(base_dark, base_mid, base_light) -> Image.Image:
    """Texture "pointillée" façon SNES (blocs de 2x2 pixels, contraste doux)."""
    n = Image.effect_noise((MAP // 2, MAP // 2), 60)
    n = ImageOps.autocontrast(n, cutoff=2).resize((MAP, MAP), Image.NEAREST)
    return ImageOps.colorize(n, black=base_dark, mid=base_mid, white=base_light, blackpoint=40, whitepoint=215)


def _make_centerline(rng: random.Random) -> list:
    """Courbe fermée aléatoire (somme d'harmoniques), puis points régulièrement espacés."""
    amps = {2: rng.uniform(0.05, 0.18), 3: rng.uniform(0.04, 0.14), 4: rng.uniform(0.02, 0.08), 5: rng.uniform(0.0, 0.05)}
    ph = {k: rng.uniform(0, 2 * math.pi) for k in amps}
    sx, sy = rng.uniform(0.85, 1.2), rng.uniform(0.85, 1.2)
    raw = []
    for i in range(900):
        th = 2 * math.pi * i / 900
        r = 1 + sum(a * math.cos(k * th + ph[k]) for k, a in amps.items())
        raw.append((r * math.cos(th) * sx, r * math.sin(th) * sy))
    if rng.random() < 0.5:
        raw.reverse()                                    # sens horaire ou anti-horaire

    xs, ys = [p[0] for p in raw], [p[1] for p in raw]
    ext = max(max(xs) - min(xs), max(ys) - min(ys))
    scale = 2 * 380 * rng.uniform(0.85, 1.0) / ext
    mx, my = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
    raw = [(MAP / 2 + (x - mx) * scale, MAP / 2 + (y - my) * scale) for x, y in raw]
    raw.append(raw[0])

    cum = [0.0]
    for i in range(1, len(raw)):
        cum.append(cum[-1] + math.hypot(raw[i][0] - raw[i - 1][0], raw[i][1] - raw[i - 1][1]))
    count = int(cum[-1] / STEP)
    pts = []
    for k in range(count):
        s = k * cum[-1] / count
        i = min(bisect_right(cum, s) - 1, len(raw) - 2)
        t = (s - cum[i]) / (cum[i + 1] - cum[i])
        pts.append((raw[i][0] + (raw[i + 1][0] - raw[i][0]) * t, raw[i][1] + (raw[i + 1][1] - raw[i][1]) * t))
    shift = rng.randrange(count)                         # emplacement de la ligne de départ
    return pts[shift:] + pts[:shift]


def _make_track(pts: list) -> Image.Image:
    img = _speckle((50, 164, 46), GRASS, (84, 198, 62))
    d = ImageDraw.Draw(img)
    n = len(pts)
    half = ROAD_W / 2
    curb = [(222, 44, 44), (242, 242, 242), (40, 80, 210), (246, 206, 40)]

    # Vibreurs colorés, bordure brune, puis piste en terre.
    for i, (x, y) in enumerate(pts):
        r = half + 9
        d.ellipse([x - r, y - r, x + r, y + r], fill=curb[(i // 5) % 4])
    for x, y in pts:
        r = half + 3
        d.ellipse([x - r, y - r, x + r, y + r], fill=(138, 108, 64))
    road = Image.new("L", (MAP, MAP), 0)
    rd = ImageDraw.Draw(road)
    for x, y in pts:
        rd.ellipse([x - half, y - half, x + half, y + half], fill=255)
    img.paste(_speckle((186, 158, 102), (198, 170, 110), (210, 184, 124)), (0, 0), road)

    # Tirets jaunes au centre.
    for i in range(0, n, 12):
        a, b = pts[i], pts[(i + 3) % n]
        d.line([a, b], fill=(246, 214, 40), width=3)

    # Ligne de départ en damier.
    (x0, y0), (x1, y1) = pts[0], pts[3]
    tx, ty = x1 - x0, y1 - y0
    tl = math.hypot(tx, ty)
    tx, ty = tx / tl, ty / tl
    nx, ny = -ty, tx
    cols, cw = 10, ROAD_W / 10
    for row in range(2):
        for c in range(cols):
            a0, a1 = -half + c * cw, -half + (c + 1) * cw
            b0, b1 = row * 6 - 6, row * 6
            quad = [(x0 + nx * a + tx * b, y0 + ny * a + ty * b) for a, b in ((a0, b0), (a1, b0), (a1, b1), (a0, b1))]
            d.polygon(quad, fill=(250, 250, 250) if (row + c) % 2 else (20, 20, 20))
    return img


# ================================================================================
# 🎥 Rendu d'une image (Mode 7 par transformation perspective + sprites)
# ================================================================================
class Scene:

    def __init__(self, rng: random.Random):
        self.pts = _make_centerline(rng)
        self.length = len(self.pts) * STEP
        self.track = _make_track(self.pts)
        self.bg = _make_background(rng)
        self.bg2 = Image.new("RGB", (BG_LEN * 2, HZ))
        self.bg2.paste(self.bg, (0, 0))
        self.bg2.paste(self.bg, (BG_LEN, 0))
        self._sprites = {}
        self._shadows = {}

    def pos(self, u: float) -> tuple:
        n = len(self.pts)
        f = (u / STEP) % n
        i = int(f)
        t = f - i
        a, b = self.pts[i], self.pts[(i + 1) % n]
        return a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t

    def point_at(self, u: float, lateral: float) -> tuple:
        """Position sur la piste à l'abscisse u, décalée latéralement (positif = à droite)."""
        x, y = self.pos(u)
        ax, ay = self.pos(u + 4)
        tx, ty = ax - x, ay - y
        tl = math.hypot(tx, ty) or 1.0
        return x - ty / tl * lateral, y + tx / tl * lateral

    def sprite(self, ci: int, width: int, lean: int = 0) -> Image.Image:
        key = (ci, width, lean)
        if key not in self._sprites:
            _, body, suit = RACERS[ci]
            base = _make_kart(body, suit, lean)
            self._sprites[key] = base.resize((width, max(2, round(width * base.height / base.width))), Image.NEAREST)
        return self._sprites[key]

    def shadow(self, width: int) -> Image.Image:
        if width not in self._shadows:
            m = Image.new("L", (width, max(2, width // 3)), 0)
            ImageDraw.Draw(m).ellipse([0, 0, m.width - 1, m.height - 1], fill=110)
            self._shadows[width] = m
        return self._shadows[width]

    def render(self, px: float, py: float, ang: float, lean: int, bob: int, timer: str,
               rank: int, rivals: list, banner: bool) -> Image.Image:
        fx, fy = math.cos(ang), math.sin(ang)
        rx, ry = -fy, fx
        cx, cy = px - fx * BACK, py - fy * BACK          # la caméra suit derrière le kart

        # Sol : une transformation perspective (1 unité = 1 pixel de la texture du circuit).
        coeffs = (
            2 * CAM_H * rx, 2 * cx, 2 * (0.5 * cx + CAM_H * FOCAL * fx - CAM_H * rx * W / 2),
            2 * CAM_H * ry, 2 * cy, 2 * (0.5 * cy + CAM_H * FOCAL * fy - CAM_H * ry * W / 2),
            0.0, 2.0,
        )
        floor = self.track.transform((W, H - HZ), Image.PERSPECTIVE, coeffs, Image.BILINEAR, fillcolor=GRASS)

        frame = Image.new("RGB", (W, H))
        x0 = int((ang % (2 * math.pi)) / (2 * math.pi) * BG_LEN)
        frame.paste(self.bg2.crop((x0, 0, x0 + W, HZ)), (0, 0))
        frame.paste(floor, (0, HZ))

        # Karts : du plus loin au plus proche (le joueur est à la profondeur BACK).
        draws = [(BACK, 0, None)]
        for wx, wy, ci in rivals:
            dx, dy = wx - cx, wy - cy
            depth = dx * fx + dy * fy
            if depth > 14:
                draws.append((depth, ci, (dx * rx + dy * ry)))
        for depth, ci, lateral in sorted(draws, key=lambda d: -d[0]):
            if lateral is None:                          # le joueur
                width, sx, foot = 36, W / 2, FOOT_ROW + bob
                spr = self.sprite(0, width, lean)
            else:
                width = int(36 * BACK / depth)
                sx, foot = W / 2 + lateral * FOCAL / depth, HZ + CAM_H * FOCAL / depth
                if width < 3 or foot - width > H or not -width < sx < W + width:
                    continue
                spr = self.sprite(ci, width)
            sh = self.shadow(int(width * 1.2))
            frame.paste((0, 0, 0), (int(sx - sh.width / 2), int(foot - sh.height + 1)), sh)
            frame.paste(spr, (int(sx - spr.width / 2), int(foot - spr.height + 2)), spr)

        # HUD : case d'objet vide, chrono, position.
        tw = _text(frame, timer, W - 6, 6, 2, (255, 255, 255), outline=(30, 90, 170), anchor="ra")
        bx = W - 6 - tw - 40
        ImageDraw.Draw(frame).rounded_rectangle([bx, 3, bx + 32, 27], radius=6, fill=(0, 0, 0), outline=(120, 220, 255), width=2)
        _text(frame, str(rank), W - 8, H - 82, 6, (255, 255, 255), outline=(70, 70, 70), anchor="ra", outline_px=2)

        if banner:
            _text(frame, "FINISH !", W // 2, 78, 4, (255, 226, 60), outline=(120, 40, 0), anchor="ma")
        return frame

    def results_screen(self, order: list) -> Image.Image:
        """Écran de classement final. order = indices RACERS du 1er au dernier."""
        img = Image.new("RGB", (W, H))
        d = ImageDraw.Draw(img)
        for y in range(H):
            t = y / H
            d.line([(0, y), (W, y)], fill=(int(16 + 20 * t), int(24 + 40 * t), int(80 + 70 * t)))
        place = order.index(0) + 1
        title = "VICTOIRE !" if place == 1 else f"{place}E PLACE"
        _text(img, title, W // 2, 8, 4, (255, 226, 60) if place == 1 else (255, 255, 255), outline=(60, 30, 0), anchor="ma")
        for k, ci in enumerate(order):
            y = 52 + k * 28
            if ci == 0:
                d.rounded_rectangle([14, y - 3, W - 14, y + 22], radius=5, fill=(80, 70, 10), outline=(255, 226, 60), width=2)
            name, body, suit = RACERS[ci]
            _text(img, str(k + 1), 26, y, 2, (255, 226, 60) if ci == 0 else (255, 255, 255), outline=(0, 0, 0))
            spr = _make_kart(body, suit).resize((36, 26), Image.NEAREST)
            img.paste(spr, (64, y - 1), spr)
            _text(img, name, 112, y, 2, (255, 226, 60) if ci == 0 else (230, 230, 240), outline=(0, 0, 0))
        return img


# ================================================================================
# 🏁 Plan de la course : classement final tiré au hasard, avec suspense
# ================================================================================
def _smooth(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


class Rival:

    def __init__(self, rng: random.Random, ci: int, lane: float, final_gap: float):
        self.ci, self.lane, self.final = ci, lane, final_gap
        self.start = rng.uniform(-35, 70)                # écart au départ (+ = devant le joueur)
        self.mean = rng.uniform(-40, 60)
        self.amp = rng.uniform(45, 95)
        self.freq = rng.uniform(0.7, 1.7)
        self.phase = rng.uniform(0, 2 * math.pi)
        self.late = None                                 # écart avant le dépassement final (rival "suspense")
        self.wobble = rng.uniform(0, 2 * math.pi)

    def gap(self, q: float, qc: float) -> float:
        """Avance du rival sur le joueur (en pixels) : positif = devant. q = avancement, qc = passage de la ligne."""
        wave = math.sin(2 * math.pi * (self.freq * q + self.phase))
        if self.late is not None:
            # Reste à l'opposé de son résultat final, puis bascule dans les derniers mètres.
            t = _smooth((q - (qc - 0.10)) / 0.09)
            mid = self.late * (1 - t) + self.final * t + self.amp * 0.12 * wave * (1 - t)
        else:
            t = _smooth((q - (qc - 0.28)) / 0.26)
            mid = (self.mean + self.amp * wave) * (1 - t) + self.final * t
        s = _smooth(q / 0.2)
        return (1 - s) * self.start + s * mid


def _plan_race(rng: random.Random) -> tuple:
    """Retourne (place finale du joueur, rivaux)."""
    place = rng.choices(range(1, 7), weights=PLACE_WEIGHTS)[0]
    ahead, behind = place - 1, 6 - place
    ids = list(range(1, 6))
    rng.shuffle(ids)
    lanes = [-23, -12, 0, 12, 23]
    rng.shuffle(lanes)

    gaps = [10 + 26 * j + rng.uniform(0, 6) for j in range(ahead)] + [-(10 + 26 * j + rng.uniform(0, 6)) for j in range(behind)]
    rivals = [Rival(rng, ci, lane, g) for ci, lane, g in zip(ids, lanes, gaps)]
    slots = [-72, -48, -24, 24, 48, 72]                  # grille de départ : karts espacés
    rng.shuffle(slots)
    for r, slot in zip(rivals, slots):
        r.start = slot + rng.uniform(-4, 4)

    # Le rival le plus proche de la place finale du joueur crée le suspense : il bascule à la fin.
    near = [r for r in rivals if abs(r.final) < 10 + 6 + 1]
    pick = rng.choice(near) if near else rivals[0]
    pick.late = -pick.final * rng.uniform(1.6, 3.0)
    return place, rivals


def _rank_at(rivals: list, q: float, qc: float) -> int:
    return 1 + sum(1 for r in rivals if r.gap(q, qc) > 0)


# ================================================================================
# 🎞️ Génération du GIF
# ================================================================================
def _timer(ms: float) -> str:
    return f"{int(ms // 60000):02d}' {int(ms // 1000) % 60:02d}\" {int(ms % 1000 / 10):02d}"


def _profile(p: float, acc: float = 0.08, dec: float = 0.06) -> float:
    """Avancement 0..1 : démarrage progressif, vitesse constante, freinage après l'arrivée."""
    v = 1 / (1 - acc / 2 - dec / 2)
    if p < acc:
        return v * p * p / (2 * acc)
    if p <= 1 - dec:
        return v * (acc / 2 + p - acc)
    return 1 - v * (1 - p) ** 2 / (2 * dec)


def _wrap(a: float) -> float:
    return (a + math.pi) % (2 * math.pi) - math.pi


def _swerve(u: float, phase: tuple, start: float, end: float) -> float:
    """Écart latéral du joueur par rapport au centre de la piste (px, + = à droite).
    Nul au départ et à l'arrivée, léger zigzag entre les deux."""
    fade = _smooth((u - start) / 70) * (1 - _smooth((u - end) / 60))
    return fade * (11 * math.sin(u / 85 + phase[0]) + 6 * math.sin(u / 37 + phase[1]))


def _lateral_paths(rivals: list, sway, u0: float, u1: float, qc: float) -> list:
    """
    Position latérale de chaque kart à chaque image (indice 0 = joueur, 1.. = rivaux).
    Chaque kart vise sa voie, mais deux karts proches (devant/derrière) se repoussent sur le côté :
    ils se croisent côte à côte au lieu de se traverser, et ça reste fluide (vitesse latérale limitée).
    """
    n, sub = 1 + len(rivals), 4
    kt, c, kr, kw, vmax, dt = 0.03, 0.4, 0.45, 0.5, 3.0, 1.0 / sub
    lat, vel = [0.0] * n, [0.0] * n

    def state(q: float) -> tuple:
        u = u0 + (u1 - u0) * _profile(q)
        us = [u] + [u + r.gap(q, qc) for r in rivals]
        targets = [sway(u)] + [r.lane + 4 * math.sin(us[i + 1] / 50 + r.wobble) for i, r in enumerate(rivals)]
        return us, targets

    def step(q: float):
        us, targets = state(q)
        acc = [kt * (targets[i] - lat[i]) - c * vel[i] for i in range(n)]
        for i in range(n):
            for j in range(i + 1, n):
                du = abs(us[i] - us[j])
                dl = lat[i] - lat[j]
                if du < KART_LONG and abs(dl) < KART_SEP:
                    f = kr * (1 - du / KART_LONG) * (KART_SEP - abs(dl))
                    sgn = 1 if dl > 0 else -1 if dl < 0 else (1 if i < j else -1)
                    acc[i] += f * sgn
                    acc[j] -= f * sgn
        for i in range(n):
            if abs(lat[i]) > ROAD_LIM:                  # rappel doux vers la piste
                acc[i] -= kw * (abs(lat[i]) - ROAD_LIM) * (1 if lat[i] > 0 else -1)
            vel[i] = max(-vmax, min(vmax, vel[i] + acc[i] * dt))
            lat[i] = max(-ROAD_LIM - 3, min(ROAD_LIM + 3, lat[i] + vel[i] * dt))

    lat[:] = state(0.0)[1]
    for _ in range(120):                                # mise en place de la grille de départ
        step(0.0)
    paths = [list(lat)]
    for k in range(1, (FRAMES - 1) * sub + 1):
        step(k / ((FRAMES - 1) * sub))
        if k % sub == 0:
            paths.append(list(lat))
    return paths


def _generate_race_gif() -> io.BytesIO:
    rng = random.Random()                                # graine système : tout est unique
    scene = Scene(rng)
    place, rivals = _plan_race(rng)
    u0, u1 = -110.0, scene.length + 90.0                 # départ avant la ligne, arrêt après l'arrivée
    race_ms = rng.uniform(46, 78) * 1000                 # temps affiché (la course est accélérée)

    phase = (rng.uniform(0, 6.28), rng.uniform(0, 6.28))
    sway = lambda v: _swerve(v, phase, u0, scene.length + 10)

    # Moment où le joueur franchit la ligne.
    qc = next(i / (FRAMES - 1) for i in range(FRAMES) if u0 + (u1 - u0) * _profile(i / (FRAMES - 1)) >= scene.length)

    lats = _lateral_paths(rivals, sway, u0, u1, qc)
    us = [u0 + (u1 - u0) * _profile(i / (FRAMES - 1)) for i in range(FRAMES)]

    frames, ang = [], None
    for i in range(FRAMES):
        q = i / (FRAMES - 1)
        u = us[i]
        i0, i1 = max(i - 1, 0), min(i + 1, FRAMES - 1)
        slope = (lats[i1][0] - lats[i0][0]) / max(1e-6, us[i1] - us[i0])    # le cap suit le mouvement latéral
        px, py = scene.point_at(u, lats[i][0])
        ax, ay = scene.point_at(u + 26, lats[i][0] + slope * 26)
        target = math.atan2(ay - py, ax - px)
        prev = target if ang is None else ang
        ang = target if ang is None else ang + _wrap(target - ang) * 0.45
        turn = _wrap(ang - prev)
        lean = 1 if turn > 0.02 else -1 if turn < -0.02 else 0

        others = [(*scene.point_at(u + r.gap(q, qc), lats[i][k + 1]), r.ci) for k, r in enumerate(rivals)]
        rank = _rank_at(rivals, min(q, qc), qc) if q < qc else place
        shown = race_ms * (min(u, scene.length) - u0) / (scene.length - u0)
        frames.append(scene.render(px, py, ang, lean, -(i % 2), _timer(shown), rank, others,
                                   u > scene.length + 30))

    # Classement final : les rivaux triés par écart final, le joueur inséré à sa place.
    order = [r.ci for r in sorted(rivals, key=lambda r: -r.final)]
    order.insert(place - 1, 0)
    results = scene.results_screen(order)
    for k in range(1, FADE_FRAMES + 1):
        frames.append(Image.blend(frames[FRAMES - 1], results, k / FADE_FRAMES))
    frames.append(results)

    # Palette commune à toutes les images.
    pick = [frames[i * (FRAMES - 1) // 5] for i in range(6)] + [frames[-1]]
    sample = Image.new("RGB", (W, H * len(pick)))
    for k, f in enumerate(pick):
        sample.paste(f, (0, H * k))
    sd = ImageDraw.Draw(sample)                          # couleurs du HUD à garder dans la palette
    for i, c in enumerate(((120, 220, 255), (255, 226, 60), (30, 90, 170), (255, 255, 255), (0, 0, 0), (120, 40, 0))):
        sd.rectangle([i * 8, 0, i * 8 + 7, 7], fill=c)
    pal = sample.quantize(colors=PALETTE_COLORS, method=Image.MEDIANCUT)
    q = [f.quantize(palette=pal, dither=0) for f in frames]

    durations = [FRAME_MS] * len(q)
    durations[-1] = RESULT_HOLD_MS
    buf = io.BytesIO()
    q[0].save(buf, "GIF", save_all=True, append_images=q[1:], duration=durations, optimize=False)
    buf.seek(0)  # 🔑 indispensable pour Discord
    return buf


# ================================================================================
# 🧠 Cog principal
# ================================================================================
class CourseKart(commands.Cog):
    """
    Commande /course et !course — Course de karting (1 tour) façon Super Mario Kart.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._lock = asyncio.Lock()

    def _embed(self) -> discord.Embed:
        embed = discord.Embed(title="🏎️ Course de Karting", color=discord.Color.green())
        embed.set_image(url="attachment://course.gif")
        return embed

    # ============================================================================
    # 🔹 Fonction interne commune
    # ============================================================================
    async def _build(self):
        async with self._lock:
            buffer = await asyncio.to_thread(_generate_race_gif)
        if buffer.getbuffer().nbytes > MAX_BYTES:
            return None, "❌ Le GIF est trop lourd pour Discord, réessaie."
        return discord.File(fp=buffer, filename="course.gif"), None

    async def _send_race(self, target):
        if self._lock.locked():
            await safe_send(target, "⏳ Une course est déjà en cours de génération, réessaie dans quelques secondes.")
            return

        file, error = await self._build()
        if error:
            await safe_send(target, error)
            return

        await safe_send(target, embed=self._embed(), file=file)

    # ============================================================================
    # 🔹 Commande SLASH
    # ============================================================================
    @app_commands.command(name="course", description="Lance une course de karting (1 tour).")
    @app_commands.checks.cooldown(rate=1, per=15.0, key=lambda i: i.user.id)
    async def slash_course(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self._send_race(interaction.channel)
        await interaction.delete_original_response()

    # ============================================================================
    # 🔹 Commande PREFIX
    # ============================================================================
    @commands.command(name="course")
    @commands.cooldown(1, 15.0, commands.BucketType.user)
    async def prefix_course(self, ctx: commands.Context):
        async with ctx.typing():
            await self._send_race(ctx.channel)


# ================================================================================
# 🔌 Setup du Cog
# ================================================================================
async def setup(bot: commands.Bot):
    cog = CourseKart(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Fun&Random"
    await bot.add_cog(cog)
