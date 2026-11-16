# ================================================================================
# 📌 labyrinthe.py
# Objectif : Labyrinthe 3D animé (GIF) façon écran de veille Windows : briques rouges,
#            plafond carrelé, sol beige. Labyrinthe aléatoire, la caméra se balade au hasard.
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
MAP_SIZE = 25
WALK_CELLS = 40            # longueur de la balade (en cases)
TEX = 64                   # texture des murs
FLOOR_PX = 24              # pixels de texture sol/plafond par case
LEVELS = 16                # niveaux d'ombrage des murs
FOG_DIST = 14.0
FOG_MAX = 0.4              # assombrissement max au loin (0.4 = -40 %)
SPEED = 0.002 * 16.67      # vitesse par tick (60 ticks/s)
TURN = 0.15                # lissage de l'angle
MAX_FRAMES = 240
FRAME_MS = 60
MAX_BYTES = 8 * 1024 * 1024


# ================================================================================
# 🧱 Textures
# ================================================================================
def _noise(size, sigma: float) -> Image.Image:
    return Image.effect_noise(size, sigma)


def _make_brick(rng: random.Random) -> Image.Image:
    """Briques rouges, joints blancs (comme l'écran de veille Windows)."""
    img = Image.new("RGB", (TEX, TEX), (232, 226, 220))
    d = ImageDraw.Draw(img)
    for row in range(4):
        y = row * 16
        off = 0 if row % 2 == 0 else 16
        for bx in range(-1, 3):
            x = bx * 32 + off
            v = rng.randint(-18, 14)
            d.rectangle([x + 2, y + 2, x + 29, y + 13], fill=(178 + v, 30 + v // 3, 36 + v // 3))
            d.line([x + 2, y + 2, x + 29, y + 2], fill=(205 + v, 60, 60))      # reflet haut
            d.line([x + 2, y + 13, x + 29, y + 13], fill=(130 + v, 20, 26))    # ombre bas
    grain = _noise((TEX, TEX), 14).convert("RGB")
    return ImageChops.add(img, grain, 1, -128)


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
    out = []
    for i in range(LEVELS):
        f = 1.0 - FOG_MAX * i / (LEVELS - 1)
        out.append(tex.point(lambda v, f=f: int(v * f)))
    return out


def _make_floor() -> Image.Image:
    """Sol beige/bois, couvre toute la carte (1 case = FLOOR_PX px)."""
    s = MAP_SIZE * FLOOR_PX
    n = _noise((s, s), 40).filter(ImageFilter.GaussianBlur(0.9))
    n = ImageOps.autocontrast(n, cutoff=1)
    return ImageOps.colorize(n, black=(196, 152, 92), white=(238, 200, 136))


def _make_ceiling() -> Image.Image:
    """Plafond carrelé gris-bleu clair avec joints."""
    s = MAP_SIZE * FLOOR_PX
    n = _noise((s, s), 40).filter(ImageFilter.GaussianBlur(0.9))
    n = ImageOps.autocontrast(n, cutoff=1)
    img = ImageOps.colorize(n, black=(150, 172, 178), white=(238, 246, 246))
    d = ImageDraw.Draw(img)
    for k in range(0, s, FLOOR_PX):
        d.line([(k, 0), (k, s)], fill=(120, 140, 146), width=1)
        d.line([(0, k), (s, k)], fill=(120, 140, 146), width=1)
    return img


def _make_fog_mask() -> Image.Image:
    """Assombrissement du sol/plafond selon la distance (ligne 0 = horizon)."""
    mask = Image.new("RGB", (W, HALF))
    d = ImageDraw.Draw(mask)
    for j in range(HALF):
        dist = EYE * FOCAL / (j + 1.0)
        f = 1.0 - FOG_MAX * min(1.0, dist / FOG_DIST)
        v = int(255 * f)
        d.line([(0, j), (W, j)], fill=(v, v, v))
    return mask


_ASSETS = {}


def _assets() -> dict:
    if not _ASSETS:
        rng = random.Random(3)
        _ASSETS["wall"] = {1: _shade_variants(_make_brick(rng)), 3: _shade_variants(_make_logo(rng))}
        _ASSETS["floor"] = _make_floor()
        _ASSETS["ceiling"] = _make_ceiling()
        _ASSETS["fog"] = _make_fog_mask()
    return _ASSETS


# ================================================================================
# 🗺️ Labyrinthe aléatoire + balade aléatoire
# ================================================================================
def _gen_maze(n: int, rng: random.Random) -> list:
    """Labyrinthe (DFS) + quelques murs retirés pour créer des boucles."""
    m = [[1] * n for _ in range(n)]
    m[1][1] = 0
    stack = [(1, 1)]
    while stack:
        x, y = stack[-1]
        nb = [(dx, dy) for dx, dy in ((2, 0), (-2, 0), (0, 2), (0, -2))
              if 0 < x + dx < n - 1 and 0 < y + dy < n - 1 and m[y + dy][x + dx] == 1]
        if nb:
            dx, dy = rng.choice(nb)
            m[y + dy // 2][x + dx // 2] = 0
            m[y + dy][x + dx] = 0
            stack.append((x + dx, y + dy))
        else:
            stack.pop()

    # Boucles : on perce des murs entre deux couloirs
    candidates = []
    for y in range(1, n - 1):
        for x in range(1, n - 1):
            if m[y][x] == 1 and (x + y) % 2 == 1:
                if (m[y][x - 1] == 0 and m[y][x + 1] == 0) or (m[y - 1][x] == 0 and m[y + 1][x] == 0):
                    candidates.append((x, y))
    rng.shuffle(candidates)
    for x, y in candidates[: n]:
        m[y][x] = 0
    return m


def _place_logos(m: list, n: int, rng: random.Random, count: int = 5) -> None:
    """Quelques murs avec le logo Discord, à côté d'un couloir."""
    spots = []
    for y in range(1, n - 1):
        for x in range(1, n - 1):
            if m[y][x] == 1 and any(m[y + dy][x + dx] == 0 for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                spots.append((x, y))
    for x, y in rng.sample(spots, min(count, len(spots))):
        m[y][x] = 3


def _random_walk(m: list, n: int, rng: random.Random, steps: int) -> list:
    """Balade au hasard : tout droit de préférence, demi-tour seulement en cul-de-sac."""
    opens = [(x, y) for y in range(1, n - 1) for x in range(1, n - 1) if m[y][x] == 0]
    path = [rng.choice(opens)]
    prev, last_dir = None, None
    for _ in range(steps):
        x, y = path[-1]
        dirs = [(dx, dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)) if m[y + dy][x + dx] == 0]
        forward = [d for d in dirs if (x + d[0], y + d[1]) != prev]
        if forward:
            if last_dir in forward and rng.random() < 0.7:
                d = last_dir
            else:
                d = rng.choice(forward)
        else:
            d = rng.choice(dirs)
        prev, last_dir = (x, y), d
        path.append((x + d[0], y + d[1]))
    return path


# ================================================================================
# 🔦 Raycasting (DDA, projection plane)
# ================================================================================
def _cast(m: list, n: int, px: float, py: float, dx: float, dy: float):
    mx, my = int(px), int(py)
    ddx = abs(1.0 / dx) if dx else 1e30
    ddy = abs(1.0 / dy) if dy else 1e30
    if dx < 0:
        sx, sdx = -1, (px - mx) * ddx
    else:
        sx, sdx = 1, (mx + 1.0 - px) * ddx
    if dy < 0:
        sy, sdy = -1, (py - my) * ddy
    else:
        sy, sdy = 1, (my + 1.0 - py) * ddy

    side = 0
    while True:
        if sdx < sdy:
            sdx += ddx
            mx += sx
            side = 0
        else:
            sdy += ddy
            my += sy
            side = 1
        if not (0 <= mx < n and 0 <= my < n):
            return 99.0, 0, 0.0, 1
        if m[my][mx] != 0:
            break

    dist = (sdx - ddx) if side == 0 else (sdy - ddy)
    if side == 0:
        wx = py + dy * dist
        wx -= math.floor(wx)
        if dx > 0:
            wx = 1.0 - wx
    else:
        wx = px + dx * dist
        wx -= math.floor(wx)
        if dy < 0:
            wx = 1.0 - wx
    return dist, side, wx, m[my][mx]


# ================================================================================
# 🎞️ Génération du GIF
# ================================================================================
def _encode(frames: list) -> io.BytesIO:
    """Palette commune (moins de scintillement), et on retire des images si trop lourd."""
    sample = Image.new("RGB", (W, H * 4))
    for k in range(4):
        sample.paste(frames[(len(frames) - 1) * k // 3], (0, H * k))
    ImageDraw.Draw(sample).rectangle([0, 0, 7, 7], fill=(88, 101, 242))
    pal = sample.quantize(colors=224, method=Image.MEDIANCUT)
    q = [f.quantize(palette=pal, dither=0) for f in frames]

    step = 1
    while True:
        sel = q[::step]
        buf = io.BytesIO()
        sel[0].save(buf, "GIF", save_all=True, append_images=sel[1:],
                    duration=FRAME_MS * step, loop=0, optimize=False)
        if buf.tell() <= MAX_BYTES or len(sel) <= 40:
            break
        step += 1
    buf.seek(0)  # 🔑 indispensable pour Discord
    return buf


def generate_maze_gif(seed: int = None) -> io.BytesIO:
    rng = random.Random(seed)
    n = MAP_SIZE
    m = _gen_maze(n, rng)
    _place_logos(m, n, rng)

    cells = _random_walk(m, n, rng, WALK_CELLS)
    nodes = [(x + 0.5, y + 0.5) for x, y in cells]

    # --- Simulation de la caméra ---
    def wrap(a: float) -> float:
        return (a + math.pi) % (2 * math.pi) - math.pi

    x, y = nodes[0]
    angle = math.atan2(nodes[1][1] - y, nodes[1][0] - x)
    idx = 1
    states = [(x, y, angle)]
    while idx < len(nodes):
        tx, ty = nodes[idx]
        diff = wrap(math.atan2(ty - y, tx - x) - angle)
        angle += diff * TURN
        spd = SPEED if abs(diff) < 0.5 else SPEED * 0.15  # on ralentit pour tourner
        nx, ny = x + math.cos(angle) * spd, y + math.sin(angle) * spd
        if m[int(ny)][int(nx)] == 0:
            x, y = nx, ny
        if math.hypot(tx - x, ty - y) < 0.2:
            idx += 1
        states.append((x, y, angle))
        if len(states) > 20000:  # sécurité
            break

    if len(states) > MAX_FRAMES:
        picks = [states[int(i * (len(states) - 1) / (MAX_FRAMES - 1))] for i in range(MAX_FRAMES)]
    else:
        picks = states

    # --- Rendu ---
    a = _assets()
    n_rays = W // COL_W
    tan_half = math.tan(FOV / 2)
    T = FLOOR_PX

    def render(px: float, py: float, ang: float) -> Image.Image:
        fx, fy = math.cos(ang), math.sin(ang)
        rx, ry = -fy, fx

        # Sol et plafond : une seule transformation perspective chacun
        coeffs = (
            2 * T * EYE * rx, 2 * T * px, 2 * T * (0.5 * px + EYE * FOCAL * fx - EYE * rx * W / 2),
            2 * T * EYE * ry, 2 * T * py, 2 * T * (0.5 * py + EYE * FOCAL * fy - EYE * ry * W / 2),
            0.0, 2.0,
        )
        floor = a["floor"].transform((W, HALF), Image.PERSPECTIVE, coeffs, Image.BILINEAR)
        ceil = a["ceiling"].transform((W, HALF), Image.PERSPECTIVE, coeffs, Image.BILINEAR)
        floor = ImageChops.multiply(floor, a["fog"])
        ceil = ImageOps.flip(ImageChops.multiply(ceil, a["fog"]))

        frame = Image.new("RGB", (W, H))
        frame.paste(ceil, (0, 0))
        frame.paste(floor, (0, HALF))

        # Murs
        for i in range(n_rays):
            cx = 2.0 * (i + 0.5) / n_rays - 1.0
            dist, side, wx, kind = _cast(m, n, px, py, fx + rx * cx * tan_half, fy + ry * cx * tan_half)
            perp = max(0.05, dist)
            lh = max(1, int(FOCAL / perp))
            lvl = min(LEVELS - 1, int(min(1.0, perp / FOG_DIST) * (LEVELS - 1)) + (1 if side else 0))
            tex = a["wall"][kind][lvl]
            tx = min(TEX - 1, int(wx * TEX))
            if lh > H:
                y0 = int(TEX * (1 - H / lh) / 2)
                y1 = max(y0 + 1, TEX - y0)
                col = tex.crop((tx, y0, tx + 1, y1)).resize((COL_W, H), Image.NEAREST)
                frame.paste(col, (i * COL_W, 0))
            else:
                col = tex.crop((tx, 0, tx + 1, TEX)).resize((COL_W, lh), Image.NEAREST)
                frame.paste(col, (i * COL_W, (H - lh) // 2))
        return frame

    frames = [render(px, py, ang) for px, py, ang in picks]
    return _encode(frames)


# ================================================================================
# 🧠 Cog principal
# ================================================================================
class Labyrinthe3D(commands.Cog):
    """
    Commande /labyrinthe3d et !labyrinthe3d — Labyrinthe 3D animé (GIF),
    style écran de veille Windows, labyrinthe et balade aléatoires.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._lock = asyncio.Lock()  # 1 génération à la fois (serveur léger)

    def _embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="🧱 Labyrinthe 3D",
            description="Style écran de veille Windows",
            color=discord.Color.dark_red()
        )
        embed.set_image(url="attachment://labyrinthe3d.gif")
        return embed

    async def _build(self):
        async with self._lock:
            buffer = await asyncio.to_thread(generate_maze_gif, random.randint(0, 999999))
        if buffer.getbuffer().nbytes > MAX_BYTES:
            return None, "❌ Le GIF est trop lourd pour Discord, réessaie."
        return discord.File(fp=buffer, filename="labyrinthe3d.gif"), None

    # ============================================================================
    # 🔹 Commande SLASH
    # ============================================================================
    @app_commands.command(
        name="labyrinthe",
        description="Labyrinthe 3D animé façon écran de veille Windows."
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
    @commands.command(name="labyrinthe")
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
