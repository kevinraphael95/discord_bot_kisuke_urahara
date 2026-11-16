# ================================================================================
# 📌 labyrinthe3d.py
# Objectif : Labyrinthe 3D (raycasting) animé en GIF, fidèle à l'écran de veille HTML.
#            La caméra parcourt le chemin le plus court jusqu'au logo Discord.
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
from PIL import Image, ImageDraw

# ================================================================================
# 📦 Modules internes
# ================================================================================
from utils.discord_anti429 import safe_send

# ================================================================================
# ⚙️ Constantes (mêmes valeurs que le HTML)
# ================================================================================
W, H = 320, 200
COL_W = 2                 # 160 rayons
FOV = math.pi / 3
MAP_SIZE = 25
TEX = 64
LEVELS = 24               # niveaux de brouillard
FOG_DIV = 10.0            # shade = min(0.95, dist / 10)
SPEED = 0.002 * 16.67     # vitesse par tick (60 ticks/s comme le navigateur)
TURN = 0.15               # lissage de l'angle
MAX_FRAMES = 200
FRAME_MS = 60
HOLD_FRAMES = 12
MAX_BYTES = 8 * 1024 * 1024


# ================================================================================
# 🧱 Textures
# ================================================================================
def _brick(img: Image.Image) -> None:
    d = ImageDraw.Draw(img, "RGBA")
    d.rectangle([0, 0, 63, 63], fill=(42, 26, 26, 255))
    for y in range(0, 64, 16):
        for x in range(0, 64, 32):
            off = 0 if (y // 16) % 2 == 0 else 16
            bx = x + off
            d.rectangle([bx + 1, y + 1, bx + 30, y + 14], fill=(74, 46, 46, 255))
            d.rectangle([bx + 1, y + 1, bx + 30, y + 2], fill=(255, 255, 255, 26))
            d.rectangle([bx + 1, y + 13, bx + 30, y + 14], fill=(0, 0, 0, 102))


def _make_brick() -> Image.Image:
    img = Image.new("RGB", (TEX, TEX))
    _brick(img)
    return img


def _make_discord() -> Image.Image:
    img = Image.new("RGB", (TEX, TEX), (42, 26, 26))
    d = ImageDraw.Draw(img)
    d.rectangle([2, 2, 61, 61], fill=(74, 46, 46))
    d.rounded_rectangle([12, 18, 51, 45], radius=10, fill=(88, 101, 242))
    for ex in (24, 40):
        d.ellipse([ex - 4, 26, ex + 4, 34], fill=(255, 255, 255))
        d.ellipse([ex - 2, 28, ex + 2, 32], fill=(42, 26, 26))
    return img


def _shade_variants(tex: Image.Image) -> list:
    out = []
    for i in range(LEVELS):
        f = 1.0 - (i / (LEVELS - 1)) * 0.95
        out.append(tex.point(lambda v, f=f: int(v * f)))
    return out


_TEX = {}


def _textures() -> dict:
    if not _TEX:
        _TEX[1] = _shade_variants(_make_brick())
        _TEX[3] = _shade_variants(_make_discord())
    return _TEX


def _make_background() -> Image.Image:
    """Plafond #1a1a1a -> #333, sol #222 -> #0a0a0a (dégradés du HTML)."""
    bg = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(bg)
    half = H // 2
    for y in range(half):
        c = int(26 + (51 - 26) * y / half)
        d.line([(0, y), (W, y)], fill=(c, c, c))
    for y in range(half, H):
        c = int(34 + (10 - 34) * (y - half) / half)
        d.line([(0, y), (W, y)], fill=(c, c, c))
    return bg


# ================================================================================
# 🗺️ Labyrinthe + chemin (BFS)
# ================================================================================
def _gen_maze(n: int, rng: random.Random) -> list:
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
    return m


def _bfs(m: list, start: tuple, goal: tuple) -> list:
    q = deque([start])
    prev = {start: None}
    while q:
        cur = q.popleft()
        if cur == goal:
            break
        x, y = cur
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            nxt = (x + dx, y + dy)
            if nxt not in prev and m[nxt[1]][nxt[0]] == 0:
                prev[nxt] = cur
                q.append(nxt)
    path, cur = [], goal
    while cur is not None:
        path.append(cur)
        cur = prev[cur]
    return path[::-1]


# ================================================================================
# 🔦 Raycasting (DDA)
# ================================================================================
def _cast(m: list, px: float, py: float, ra: float):
    dx, dy = math.cos(ra), math.sin(ra)
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
        if m[my][mx] != 0:
            break

    if side == 0:
        dist = sdx - ddx
        wx = py + dy * dist
        wx -= math.floor(wx)
        if dx > 0:
            wx = 1.0 - wx
    else:
        dist = sdy - ddy
        wx = px + dx * dist
        wx -= math.floor(wx)
        if dy < 0:
            wx = 1.0 - wx
    return dist, wx, m[my][mx]


# ================================================================================
# 🎞️ Génération du GIF
# ================================================================================
def generate_maze_gif(seed: int = None) -> io.BytesIO:
    rng = random.Random(seed)
    n = MAP_SIZE
    m = _gen_maze(n, rng)

    cells = _bfs(m, (1, 1), (n - 2, n - 2))

    # Logo Discord sur le mur juste devant la sortie (dans l'axe du dernier pas)
    ex, ey = cells[-1]
    lx, ly = cells[-2]
    ddx, ddy = ex - lx, ey - ly
    m[ey + ddy][ex + ddx] = 3
    final_angle = math.atan2(ddy, ddx)

    # Nœuds suivis par la caméra (centres de cases), arrêt avant le logo
    nodes = [(x + 0.5, y + 0.5) for x, y in cells[:-1]]
    nodes.append((lx + 0.5 + ddx * 0.3, ly + 0.5 + ddy * 0.3))

    # --- Simulation identique au HTML (tick par tick) ---
    def wrap(a: float) -> float:
        return (a + math.pi) % (2 * math.pi) - math.pi

    x, y = nodes[0]
    angle = 0.0
    idx = 1
    states = [(x, y, angle)]
    while idx < len(nodes):
        tx, ty = nodes[idx]
        target = math.atan2(ty - y, tx - x)
        angle += wrap(target - angle) * TURN
        x += math.cos(angle) * SPEED
        y += math.sin(angle) * SPEED
        if math.hypot(tx - x, ty - y) < 0.2 and idx < len(nodes) - 1:
            idx += 1
        elif idx == len(nodes) - 1 and math.hypot(tx - x, ty - y) < 0.05:
            idx += 1
        states.append((x, y, angle))
    for _ in range(60):  # on se tourne vers le logo
        angle += wrap(final_angle - angle) * 0.2
        states.append((x, y, angle))

    # Échantillonnage régulier
    if len(states) > MAX_FRAMES:
        picks = [states[int(i * (len(states) - 1) / (MAX_FRAMES - 1))] for i in range(MAX_FRAMES)]
    else:
        picks = states
    picks += [states[-1]] * HOLD_FRAMES

    # --- Rendu ---
    textures = _textures()
    bg = _make_background()
    n_rays = W // COL_W

    def render(px: float, py: float, ang: float) -> Image.Image:
        frame = bg.copy()
        for i in range(n_rays):
            ra = ang + (i / n_rays - 0.5) * FOV
            dist, wx, kind = _cast(m, px, py, ra)
            perp = max(0.05, dist * math.cos(ra - ang))
            lh = max(1, int(H / perp))
            shade = min(0.95, perp / FOG_DIV)
            lvl = int(round(shade / 0.95 * (LEVELS - 1)))
            tex = textures[kind][lvl]
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

    frames = [render(px, py, a) for px, py, a in picks]

    buffer = io.BytesIO()
    frames[0].save(
        buffer, "GIF", save_all=True, append_images=frames[1:],
        duration=FRAME_MS, loop=0, optimize=False,
    )
    buffer.seek(0)  # 🔑 indispensable pour Discord
    return buffer


# ================================================================================
# 🧠 Cog principal
# ================================================================================
class Labyrinthe3D(commands.Cog):
    """
    Commande /labyrinthe3d et !labyrinthe3d — Labyrinthe 3D animé (GIF),
    style écran de veille, qui finit sur le logo Discord.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._lock = asyncio.Lock()  # 1 génération à la fois (serveur léger)

    def _embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="🧱 Labyrinthe 3D Discord",
            description="Écran de veille — direction le logo Discord !",
            color=discord.Color.blurple()
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
        name="labyrinthe3d",
        description="Labyrinthe 3D animé jusqu'au logo Discord."
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
    @commands.command(name="labyrinthe3d")
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
