# ================================================================================
# 📌 labyrinthe.py
# Objectif : Labyrinthe 3D animé (GIF) façon écran de veille Windows : briques rouges,
#            plafond carrelé, sol beige. Labyrinthe et trajet aléatoires : la caméra explore
#            jusqu'à tomber sur le logo Discord (cul-de-sac), puis écran de fin.
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
from collections import deque

# ================================================================================
# 📦 Modules tiers
# ================================================================================
import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

# ================================================================================
# 📦 Modules internes
# ================================================================================
from utils.discord_anti429 import safe_send

# ================================================================================
# ⚙️ Constantes
# ================================================================================
W, H = 320, 200
HALF = H // 2
COL_W = 2                  # largeur d'une colonne de rayon (160 rayons)
FOV = math.radians(66)
FOCAL = (W / 2) / math.tan(FOV / 2)
EYE = 0.5                  # hauteur des yeux (murs = 1 case de haut)
MAP_SIZES = (11, 13, 15, 17)       # taille tirée au hasard (impair)
MAX_PATH = 80                      # balade max (en cases) : sinon on retire un autre labyrinthe
TEX = 64                   # texture des murs
FLOOR_PX = 24              # pixels de texture sol/plafond par case
LEVELS = 16                # niveaux d'ombrage des murs
FOG_DIST = 14.0
FOG_MAX = 0.4              # assombrissement max au loin
SPEED = 0.002 * 16.67      # vitesse par tick (60 ticks/s)
TURN = 0.15                # lissage de l'angle
MAX_FRAMES = 250           # images max pour la balade (la vitesse s'adapte)
FRAME_MS = 75              # plus grand = plus lent
FOUND_HOLD_MS = 1000       # pause sur le logo
FADE_FRAMES = 8            # fondu vers l'écran de fin
END_HOLD_MS = 8000         # durée de l'écran de fin
GRAIN = 14                 # grain des briques (0 = lisse = GIF plus léger)
GROUND_BLUR = 0.9          # flou du bruit sol/plafond (plus haut = plus lisse et plus léger)
PALETTE_COLORS = 128       # couleurs du GIF (moins = plus léger)
MAX_BYTES = 8 * 1024 * 1024

DIRS = ((1, 0), (-1, 0), (0, 1), (0, -1))


# ================================================================================
# 🧱 Textures (générées une seule fois)
# ================================================================================
def _noise(size, sigma: float) -> Image.Image:
    return Image.effect_noise(size, sigma)


def _make_brick(rng: random.Random) -> Image.Image:
    """Briques rouges, joints blancs (comme l'écran de veille Windows)."""
    img = Image.new("RGB", (TEX, TEX), (232, 226, 220))
    d = ImageDraw.Draw(img)
    for row in range(4):
        y, off = row * 16, (0 if row % 2 == 0 else 16)
        for bx in range(-1, 3):
            x, v = bx * 32 + off, rng.randint(-18, 14)
            d.rectangle([x + 2, y + 2, x + 29, y + 13], fill=(178 + v, 30 + v // 3, 36 + v // 3))
            d.line([x + 2, y + 2, x + 29, y + 2], fill=(205 + v, 60, 60))
            d.line([x + 2, y + 13, x + 29, y + 13], fill=(130 + v, 20, 26))
    if GRAIN:
        img = ImageChops.add(img, _noise((TEX, TEX), GRAIN).convert("RGB"), 1, -128)
    return img


def _make_logo(rng: random.Random) -> Image.Image:
    """Mur de briques avec un logo Discord."""
    img = _make_brick(rng)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([10, 16, 53, 47], radius=12, fill=(88, 101, 242))
    d.polygon([(20, 45), (16, 56), (30, 47)], fill=(88, 101, 242))
    d.polygon([(44, 45), (48, 56), (34, 47)], fill=(88, 101, 242))
    for ex in (24, 40):
        d.ellipse([ex - 5, 26, ex + 5, 38], fill=(255, 255, 255))
        d.ellipse([ex - 2, 29, ex + 2, 35], fill=(30, 30, 60))
    return img


def _shade_variants(tex: Image.Image) -> list:
    return [tex.point(lambda v, f=1 - FOG_MAX * i / (LEVELS - 1): int(v * f)) for i in range(LEVELS)]


def _make_ground(ceiling: bool, size: int) -> Image.Image:
    """Sol beige/bois ou plafond carrelé gris-bleu, couvre toute la carte."""
    s = size * FLOOR_PX
    n = ImageOps.autocontrast(_noise((s, s), 40).filter(ImageFilter.GaussianBlur(GROUND_BLUR)), cutoff=1)
    if not ceiling:
        return ImageOps.colorize(n, black=(196, 152, 92), white=(238, 200, 136))
    img = ImageOps.colorize(n, black=(150, 172, 178), white=(238, 246, 246))
    d = ImageDraw.Draw(img)
    for k in range(0, s, FLOOR_PX):
        d.line([(k, 0), (k, s)], fill=(120, 140, 146))
        d.line([(0, k), (s, k)], fill=(120, 140, 146))
    return img


def _make_fog_mask() -> Image.Image:
    """Assombrissement du sol/plafond selon la distance (ligne 0 = horizon)."""
    mask = Image.new("RGB", (W, HALF))
    d = ImageDraw.Draw(mask)
    for j in range(HALF):
        v = int(255 * (1 - FOG_MAX * min(1.0, EYE * FOCAL / (j + 1.0) / FOG_DIST)))
        d.line([(0, j), (W, j)], fill=(v, v, v))
    return mask


_ASSETS = {}


def _assets() -> dict:
    """Textures de murs et brouillard : créés une fois. Sol/plafond : une fois par taille de carte."""
    if not _ASSETS:
        rng = random.Random(3)
        _ASSETS["wall"] = {1: _shade_variants(_make_brick(rng)), 3: _shade_variants(_make_logo(rng))}
        _ASSETS["fog"] = _make_fog_mask()
        _ASSETS["ground"] = {}
    return _ASSETS


def _ground(size: int) -> tuple:
    cache = _assets()["ground"]
    if size not in cache:
        cache[size] = (_make_ground(False, size), _make_ground(True, size))
    return cache[size]


# ================================================================================
# 🗺️ Labyrinthe aléatoire, logo en cul-de-sac, exploration aléatoire
# ================================================================================
def _gen_maze(n: int, rng: random.Random) -> list:
    """
    Algorithme "growing tree" avec un paramètre tiré au hasard :
    proche de 1 = longs couloirs sinueux, proche de 0 = beaucoup de petites impasses.
    Puis quelques murs percés au hasard pour créer des boucles.
    """
    m = [[1] * n for _ in range(n)]
    sx, sy = rng.randrange(1, n, 2), rng.randrange(1, n, 2)
    m[sy][sx] = 0
    active = [(sx, sy)]
    newest = rng.uniform(0.2, 1.0)
    while active:
        i = len(active) - 1 if rng.random() < newest else rng.randrange(len(active))
        x, y = active[i]
        nb = [(dx, dy) for dx, dy in ((2, 0), (-2, 0), (0, 2), (0, -2))
              if 0 < x + dx < n - 1 and 0 < y + dy < n - 1 and m[y + dy][x + dx] == 1]
        if nb:
            dx, dy = rng.choice(nb)
            m[y + dy // 2][x + dx // 2] = 0
            m[y + dy][x + dx] = 0
            active.append((x + dx, y + dy))
        else:
            active.pop(i)

    holes = [(x, y) for y in range(1, n - 1) for x in range(1, n - 1)
             if m[y][x] == 1 and ((m[y][x - 1] == 0 and m[y][x + 1] == 0) or (m[y - 1][x] == 0 and m[y + 1][x] == 0))]
    rng.shuffle(holes)
    for x, y in holes[: int(len(holes) * rng.uniform(0.0, 0.12))]:
        m[y][x] = 0
    return m


def _open_neighbors(m: list, x: int, y: int) -> list:
    return [(x + dx, y + dy) for dx, dy in DIRS if m[y + dy][x + dx] == 0]


def _distances(m: list, start: tuple) -> dict:
    dist, q = {start: 0}, deque([start])
    while q:
        x, y = q.popleft()
        for nxt in _open_neighbors(m, x, y):
            if nxt not in dist:
                dist[nxt] = dist[(x, y)] + 1
                q.append(nxt)
    return dist


def _build_level(rng: random.Random) -> tuple:
    """Retourne (labyrinthe, case de départ, cul-de-sac du logo, direction du logo)."""
    while True:
        n = rng.choice(MAP_SIZES)
        m = _gen_maze(n, rng)
        opens = [(x, y) for y in range(1, n - 1) for x in range(1, n - 1) if m[y][x] == 0]
        start = rng.choice(opens)
        dist = _distances(m, start)
        far = max(dist.values())
        dead_ends = [c for c in opens if c != start and len(_open_neighbors(m, *c)) == 1 and dist[c] >= far * 0.5]
        if not dead_ends:
            continue  # pas de bon cul-de-sac : on retire un labyrinthe
        goal = rng.choice(dead_ends)
        ox, oy = _open_neighbors(m, *goal)[0]
        d = (goal[0] - ox, goal[1] - oy)                 # sens d'entrée dans l'impasse
        m[goal[1] + d[1]][goal[0] + d[0]] = 3            # logo sur le mur du fond
        return m, start, goal, d


def _explore(m: list, rng: random.Random, start: tuple, goal: tuple) -> list:
    """
    Exploration aléatoire (DFS) : on avance au hasard vers les cases pas encore visitées
    (plutôt tout droit), et on revient en arrière en cas d'impasse. S'arrête sur le logo.
    """
    path, stack, visited, last = [start], [start], {start}, None
    while path[-1] != goal:
        x, y = path[-1]
        free = [c for c in _open_neighbors(m, x, y) if c not in visited]
        if free:
            ahead = (x + last[0], y + last[1]) if last else None
            nxt = ahead if ahead in free and rng.random() < 0.6 else rng.choice(free)
            last = (nxt[0] - x, nxt[1] - y)
            visited.add(nxt)
            stack.append(nxt)
        else:
            stack.pop()
            nxt = stack[-1]
            last = (nxt[0] - x, nxt[1] - y)
        path.append(nxt)
    return path


# ================================================================================
# 🔦 Raycasting (DDA, projection plane)
# ================================================================================
def _cast(m: list, n: int, px: float, py: float, dx: float, dy: float):
    mx, my = int(px), int(py)
    ddx = abs(1.0 / dx) if dx else 1e30
    ddy = abs(1.0 / dy) if dy else 1e30
    sx, sdx = (-1, (px - mx) * ddx) if dx < 0 else (1, (mx + 1.0 - px) * ddx)
    sy, sdy = (-1, (py - my) * ddy) if dy < 0 else (1, (my + 1.0 - py) * ddy)

    side = 0
    while True:
        if sdx < sdy:
            sdx, mx, side = sdx + ddx, mx + sx, 0
        else:
            sdy, my, side = sdy + ddy, my + sy, 1
        if not (0 <= mx < n and 0 <= my < n):
            return 99.0, 0, 0.0, 1
        if m[my][mx]:
            break

    if side == 0:
        dist = sdx - ddx
        wx = (py + dy * dist) % 1.0
        wx = 1.0 - wx if dx > 0 else wx
    else:
        dist = sdy - ddy
        wx = (px + dx * dist) % 1.0
        wx = 1.0 - wx if dy < 0 else wx
    return dist, side, wx, m[my][mx]


# ================================================================================
# 🏁 Écran de fin (texte pixelisé façon Windows 95)
# ================================================================================
def _pixel_text(img: Image.Image, text: str, cy: int, scale: int, color: tuple) -> None:
    probe = ImageDraw.Draw(Image.new("L", (1, 1)))
    box = probe.textbbox((0, 0), text)
    w, h = box[2] + 2, box[3] + 2
    layer = Image.new("L", (w, h), 0)
    ImageDraw.Draw(layer).text((1, 1), text, fill=255)
    layer = layer.resize((w * scale, h * scale), Image.NEAREST)
    x, y = (W - layer.width) // 2, cy - layer.height // 2
    shadow = Image.new("RGB", layer.size, (0, 0, 0))
    img.paste(shadow, (x + scale, y + scale), layer)          # ombre
    img.paste(Image.new("RGB", layer.size, color), (x, y), layer)


def _end_screen(last: Image.Image, steps: int) -> Image.Image:
    img = Image.blend(last, Image.new("RGB", (W, H), (8, 8, 20)), 0.78)
    _pixel_text(img, "FIN", 70, 9, (255, 255, 255))
    _pixel_text(img, "DISCORD TROUVE !", 128, 2, (150, 160, 255))
    _pixel_text(img, f"{steps} CASES PARCOURUES", 156, 2, (200, 200, 210))
    return img


# ================================================================================
# 🎞️ Génération du GIF
# ================================================================================
def _encode(frames: list, durations: list) -> io.BytesIO:
    """Palette commune à toutes les images ; on retire des images de la balade si trop lourd."""
    logo_frame = len(frames) - FADE_FRAMES - 2          # dernière image de la balade (logo bien visible)
    pick = [frames[i * (logo_frame - 1) // 5] for i in range(6)] + [frames[logo_frame], frames[-1]]
    sample = Image.new("RGB", (W, H * len(pick)))
    for k, f in enumerate(pick):
        sample.paste(f, (0, H * k))
    pal = sample.quantize(colors=PALETTE_COLORS, method=Image.MEDIANCUT)
    q = [f.quantize(palette=pal, dither=0) for f in frames]

    tail = FADE_FRAMES + 1                       # fondu + écran de fin : toujours conservés
    step = 1
    while True:
        body = list(range(0, len(q) - tail, step))
        idx = body + list(range(len(q) - tail, len(q)))
        sel = [q[i] for i in idx]
        dur = [durations[i] * (step if i < len(q) - tail else 1) for i in idx]
        buf = io.BytesIO()
        # pas de "loop" : lecture unique là où c'est géré, l'écran de fin reste affiché
        sel[0].save(buf, "GIF", save_all=True, append_images=sel[1:], duration=dur, optimize=False)
        if buf.tell() <= MAX_BYTES or len(body) <= 40:
            break
        step += 1
    buf.seek(0)  # 🔑 indispensable pour Discord
    return buf


def generate_maze_gif() -> io.BytesIO:
    rng = random.Random()                        # graine système : vraiment aléatoire
    while True:
        m, start, goal, (ddx, ddy) = _build_level(rng)
        cells = _explore(m, rng, start, goal)
        if len(cells) <= MAX_PATH:               # balade trop longue = trop rapide à l'écran : on retire
            break
    n = len(m)

    # Nœuds suivis par la caméra : on s'arrête dans la case avant l'impasse, face au logo
    ox, oy = cells[-2]
    nodes = [(x + 0.5, y + 0.5) for x, y in cells[:-1]]
    nodes.append((ox + 0.5 + ddx * 0.3, oy + 0.5 + ddy * 0.3))
    final_angle = math.atan2(ddy, ddx)

    # --- Simulation de la caméra (tick par tick) ---
    def wrap(a: float) -> float:
        return (a + math.pi) % (2 * math.pi) - math.pi

    x, y = nodes[0]
    angle = rng.choice((0.0, math.pi / 2, math.pi, -math.pi / 2))   # cap de départ aléatoire
    idx = 1
    states = [(x, y, angle)]
    while idx < len(nodes) and len(states) < 40000:
        tx, ty = nodes[idx]
        diff = wrap(math.atan2(ty - y, tx - x) - angle)
        angle += diff * (TURN * 2 if abs(diff) > 1.2 else TURN)   # demi-tour en impasse : plus vite
        spd = SPEED if abs(diff) < 0.5 else SPEED * 0.15           # on ralentit pour tourner
        nx, ny = x + math.cos(angle) * spd, y + math.sin(angle) * spd
        if m[int(ny)][int(nx)] == 0:
            x, y = nx, ny
        if math.hypot(tx - x, ty - y) < (0.2 if idx < len(nodes) - 1 else 0.05):
            idx += 1
        states.append((x, y, angle))
    for _ in range(40):                          # on se tourne face au logo
        angle += wrap(final_angle - angle) * 0.2
        states.append((x, y, angle))

    picks = states if len(states) <= MAX_FRAMES else [
        states[int(i * (len(states) - 1) / (MAX_FRAMES - 1))] for i in range(MAX_FRAMES)]

    # --- Rendu ---
    a = _assets()
    floor_tex, ceil_tex = _ground(n)
    n_rays = W // COL_W
    tan_half = math.tan(FOV / 2)
    t = FLOOR_PX

    def render(px: float, py: float, ang: float) -> Image.Image:
        fx, fy = math.cos(ang), math.sin(ang)
        rx, ry = -fy, fx
        coeffs = (
            2 * t * EYE * rx, 2 * t * px, 2 * t * (0.5 * px + EYE * FOCAL * fx - EYE * rx * W / 2),
            2 * t * EYE * ry, 2 * t * py, 2 * t * (0.5 * py + EYE * FOCAL * fy - EYE * ry * W / 2),
            0.0, 2.0,
        )
        floor = floor_tex.transform((W, HALF), Image.PERSPECTIVE, coeffs, Image.BILINEAR)
        ceil = ceil_tex.transform((W, HALF), Image.PERSPECTIVE, coeffs, Image.BILINEAR)
        frame = Image.new("RGB", (W, H))
        frame.paste(ImageOps.flip(ImageChops.multiply(ceil, a["fog"])), (0, 0))
        frame.paste(ImageChops.multiply(floor, a["fog"]), (0, HALF))

        for i in range(n_rays):
            cam = 2.0 * (i + 0.5) / n_rays - 1.0
            dist, side, wx, kind = _cast(m, n, px, py, fx + rx * cam * tan_half, fy + ry * cam * tan_half)
            dist = max(0.05, dist)
            lvl = min(LEVELS - 1, int(min(1.0, dist / FOG_DIST) * (LEVELS - 1)) + (1 if side else 0))
            tex = a["wall"][kind][lvl]
            tx = min(TEX - 1, int(wx * TEX))
            lh = max(1, int(FOCAL / dist))
            if lh > H:
                y0 = int(TEX * (1 - H / lh) / 2)
                col = tex.crop((tx, y0, tx + 1, max(y0 + 1, TEX - y0))).resize((COL_W, H), Image.NEAREST)
                frame.paste(col, (i * COL_W, 0))
            else:
                col = tex.crop((tx, 0, tx + 1, TEX)).resize((COL_W, lh), Image.NEAREST)
                frame.paste(col, (i * COL_W, (H - lh) // 2))
        return frame

    frames = [render(px, py, ang) for px, py, ang in picks]
    durations = [FRAME_MS] * len(frames)
    durations[-1] = FOUND_HOLD_MS                # pause sur le logo

    # Fondu vers l'écran de fin, puis écran de fin
    end = _end_screen(frames[-1], len(cells) - 1)
    dark = Image.blend(frames[-1], Image.new("RGB", (W, H), (8, 8, 20)), 0.78)
    for k in range(1, FADE_FRAMES + 1):
        frames.append(Image.blend(frames[len(picks) - 1], dark, k / FADE_FRAMES))
        durations.append(FRAME_MS)
    frames.append(end)
    durations.append(END_HOLD_MS)
    return _encode(frames, durations)


# ================================================================================
# 🧠 Cog principal
# ================================================================================
class Labyrinthe3D(commands.Cog):
    """
    Commande /labyrinthe et !labyrinthe — Labyrinthe 3D animé (GIF),
    style écran de veille Windows : exploration aléatoire jusqu'au logo Discord.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._lock = asyncio.Lock()  # 1 génération à la fois (serveur léger)

    def _embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="🧱 Labyrinthe",
            color=discord.Color.dark_red()
        )
        embed.set_image(url="attachment://labyrinthe.gif")
        return embed

    async def _build(self):
        async with self._lock:
            buffer = await asyncio.to_thread(generate_maze_gif)
        if buffer.getbuffer().nbytes > MAX_BYTES:
            return None, "❌ Le GIF est trop lourd pour Discord, réessaie."
        return discord.File(fp=buffer, filename="labyrinthe.gif"), None

    # ============================================================================
    # 🔹 Commande SLASH
    # ============================================================================
    @app_commands.command(
        name="labyrinthe",
        description="Labyrinthe : la caméra explore jusqu'au logo Discord."
    )
    @app_commands.checks.cooldown(rate=1, per=15.0, key=lambda i: i.user.id)
    async def slash_labyrinthe3d(self, interaction: discord.Interaction):
        if self._lock.locked():
            await interaction.response.send_message(
                "⏳ Un labyrinthe est déjà en cours de génération, réessaie dans quelques secondes.",
                ephemeral=True
            )
            return

        await interaction.response.defer()
        file, error = await self._build()
        if error:
            await interaction.followup.send(error, ephemeral=True)
            return

        await safe_send(interaction.channel, embed=self._embed(), file=file)
        await interaction.delete_original_response()

    # ============================================================================
    # 🔹 Commande PREFIX
    # ============================================================================
    @commands.command(name="labyrinthe", help="Labyrinthe : la caméra explore jusqu'au logo Discord.")
    @commands.cooldown(1, 15.0, commands.BucketType.user)
    async def prefix_labyrinthe3d(self, ctx: commands.Context):
        if self._lock.locked():
            await ctx.send("⏳ Un labyrinthe est déjà en cours de génération, réessaie dans quelques secondes.")
            return

        async with ctx.typing():
            file, error = await self._build()
        if error:
            await ctx.send(error)
            return

        await safe_send(ctx.channel, embed=self._embed(), file=file)


# ================================================================================
# 🔌 Setup du Cog
# ================================================================================
async def setup(bot: commands.Bot):
    cog = Labyrinthe3D(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Fun&Random"
    await bot.add_cog(cog)
