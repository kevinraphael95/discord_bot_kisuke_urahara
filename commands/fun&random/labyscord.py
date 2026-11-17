# ================================================================================
# 📌 labyscord.py
# Objectif : Jeu 3D à la première personne dans un labyrinthe aléatoire (style écran
#            de veille Windows). Retrouve le logo Discord en explorant les couloirs.
# Catégorie : Fun
# Accès : Tous (une partie privée par joueur)
# Cooldown : 15s (slash) / 15s (prefix)
# ================================================================================

# ================================================================================
# 📦 Modules standards
# ================================================================================
from __future__ import annotations

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
from utils.discord_anti429 import safe_send, safe_edit, safe_respond

# ================================================================================
# ⚙️ Configuration
# ================================================================================
WIDTH, HEIGHT = 320, 200
HALF = HEIGHT // 2
COL_W = 2                              # largeur d'une colonne de rayon (160 rayons)
MAP_SIZE = 15
FOV = math.radians(66)
FOCAL = (WIDTH / 2) / math.tan(FOV / 2)
EYE = 0.5                              # hauteur des yeux (murs = 1 case de haut)
TEX = 64                               # texture des murs
FLOOR_PX = 24                          # pixels de texture sol/plafond par case
FOG_DIST = 14.0
FOG_MAX = 0.40
SIDE_SHADE = 0.12                      # murs Est/Ouest un peu plus sombres
LEVELS = 16                            # niveaux d'ombrage précalculés
SHADE_RANGE = FOG_MAX + SIDE_SHADE
GAME_TIMEOUT = 180
ANIM_FRAMES = 8
ANIM_MS = 60
START_TEXT = "Trouve le logo Discord !"
COMPASS = ("➡️ Est", "⬇️ Sud", "⬅️ Ouest", "⬆️ Nord")

Pose = tuple  # (x, y, angle)


# ================================================================================
# 🎨 Textures (générées une seule fois, partagées par toutes les parties)
# ================================================================================
def _noise(size: tuple, sigma: float) -> Image.Image:
    return Image.effect_noise(size, sigma)


def _make_brick() -> Image.Image:
    """Briques rouges, joints blancs."""
    img = Image.new("RGB", (TEX, TEX), "#e8e2dc")
    d = ImageDraw.Draw(img)
    for row in range(4):
        y, off = row * 16, (0 if row % 2 == 0 else 16)
        for bx in range(-1, 3):
            x, v = bx * 32 + off, random.randint(-18, 14)
            d.rectangle((x + 2, y + 2, x + 29, y + 13), fill=(178 + v, 30 + v // 3, 36 + v // 3))
            d.line((x + 2, y + 2, x + 29, y + 2), fill=(205 + v, 60, 60))
            d.line((x + 2, y + 13, x + 29, y + 13), fill=(130 + v, 20, 26))
    return ImageChops.add(img, _noise((TEX, TEX), 14).convert("RGB"), 1, -128)


def _make_logo(brick: Image.Image) -> Image.Image:
    """Logo Discord sur fond de briques."""
    img = brick.copy()
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((10, 16, 53, 47), radius=12, fill="#5865f2")
    d.polygon(((20, 45), (16, 56), (30, 47)), fill="#5865f2")
    d.polygon(((44, 45), (48, 56), (34, 47)), fill="#5865f2")
    for x in (24, 40):
        d.ellipse((x - 5, 26, x + 5, 38), fill="white")
        d.ellipse((x - 2, 29, x + 2, 35), fill="#20203c")
    return img


def _make_ground(ceiling: bool) -> Image.Image:
    """Sol beige (bois) ou plafond carrelé gris-bleu, couvre toute la carte."""
    size = MAP_SIZE * FLOOR_PX
    noise = ImageOps.autocontrast(_noise((size, size), 40).filter(ImageFilter.GaussianBlur(0.9)), cutoff=1)
    if not ceiling:
        return ImageOps.colorize(noise, black=(196, 152, 92), white=(238, 200, 136))
    img = ImageOps.colorize(noise, black=(150, 172, 178), white=(238, 246, 246))
    d = ImageDraw.Draw(img)
    for k in range(0, size, FLOOR_PX):
        d.line((k, 0, k, size), fill="#788c92")
        d.line((0, k, size, k), fill="#788c92")
    return img


def _shade_variants(tex: Image.Image) -> list:
    return [tex.point(lambda v, f=1 - SHADE_RANGE * i / (LEVELS - 1): int(v * f)) for i in range(LEVELS)]


def _make_fog_mask() -> Image.Image:
    """Assombrissement sol/plafond selon la distance (ligne 0 = horizon)."""
    mask = Image.new("RGB", (WIDTH, HALF))
    d = ImageDraw.Draw(mask)
    for j in range(HALF):
        v = int(255 * (1 - FOG_MAX * min(1.0, EYE * FOCAL / (j + 1) / FOG_DIST)))
        d.line((0, j, WIDTH, j), fill=(v, v, v))
    return mask


_ASSETS: dict = {}


def get_assets() -> dict:
    if not _ASSETS:
        brick = _make_brick()
        _ASSETS.update(
            walls={1: _shade_variants(brick), 3: _shade_variants(_make_logo(brick))},
            floor=_make_ground(False),
            ceiling=_make_ground(True),
            fog=_make_fog_mask(),
        )
    return _ASSETS


# ================================================================================
# 🧩 Génération du labyrinthe
# ================================================================================
def generate_maze() -> tuple:
    """Labyrinthe aléatoire avec quelques boucles. Le logo (3) est placé le plus loin possible."""
    n = MAP_SIZE
    maze = [[1] * n for _ in range(n)]
    maze[1][1] = 0
    stack = [(1, 1)]
    while stack:
        x, y = stack[-1]
        nb = [(dx, dy) for dx, dy in ((2, 0), (-2, 0), (0, 2), (0, -2))
              if 0 < x + dx < n - 1 and 0 < y + dy < n - 1 and maze[y + dy][x + dx] == 1]
        if nb:
            dx, dy = random.choice(nb)
            maze[y + dy // 2][x + dx // 2] = maze[y + dy][x + dx] = 0
            stack.append((x + dx, y + dy))
        else:
            stack.pop()

    # Ouvertures supplémentaires (boucles).
    holes = [(x, y) for y in range(1, n - 1) for x in range(1, n - 1)
             if maze[y][x] == 1 and ((maze[y][x - 1] == 0 and maze[y][x + 1] == 0)
                                     or (maze[y - 1][x] == 0 and maze[y + 1][x] == 0))]
    for x, y in random.sample(holes, min(n, len(holes))):
        maze[y][x] = 0

    # BFS : la case la plus éloignée du départ reçoit le logo.
    dist = {(1, 1): 0}
    queue, far = deque([(1, 1)]), (1, 1)
    while queue:
        x, y = queue.popleft()
        if dist[(x, y)] > dist[far]:
            far = (x, y)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nxt = (x + dx, y + dy)
            if nxt not in dist and maze[nxt[1]][nxt[0]] == 0:
                dist[nxt] = dist[(x, y)] + 1
                queue.append(nxt)
    maze[far[1]][far[0]] = 3
    return maze, far


# ================================================================================
# 🎮 Moteur 3D
# ================================================================================
def cast_ray(maze: list, px: float, py: float, dx: float, dy: float) -> tuple:
    """Raycasting DDA. Retourne (distance, côté, position sur le mur, tuile)."""
    mx, my = int(px), int(py)
    ddx = abs(1 / dx) if dx else 1e30
    ddy = abs(1 / dy) if dy else 1e30
    sx, sdx = (-1, (px - mx) * ddx) if dx < 0 else (1, (mx + 1 - px) * ddx)
    sy, sdy = (-1, (py - my) * ddy) if dy < 0 else (1, (my + 1 - py) * ddy)

    side = 0
    while True:
        if sdx < sdy:
            sdx, mx, side = sdx + ddx, mx + sx, 0
        else:
            sdy, my, side = sdy + ddy, my + sy, 1
        if not (0 <= mx < MAP_SIZE and 0 <= my < MAP_SIZE):
            return 99.0, 0, 0.0, 1
        if maze[my][mx]:
            break

    if side == 0:
        dist = sdx - ddx
        wx = (py + dy * dist) % 1.0
        wx = 1 - wx if dx > 0 else wx
    else:
        dist = sdy - ddy
        wx = (px + dx * dist) % 1.0
        wx = 1 - wx if dy < 0 else wx
    return max(0.05, dist), side, wx, maze[my][mx]


def quantize_frames(frames: list) -> list:
    """Palette commune à toutes les images : GIF plus léger et sans scintillement."""
    sample = Image.new("RGB", (WIDTH, HEIGHT * 2))
    sample.paste(frames[0], (0, 0))
    sample.paste(frames[-1], (0, HEIGHT))
    ImageDraw.Draw(sample).rectangle((0, 0, 7, 7), fill="#5865f2")
    pal = sample.quantize(colors=224, method=Image.MEDIANCUT)
    return [f.quantize(palette=pal, dither=0) for f in frames]


class MazeGame:

    def __init__(self):
        self.maze, self.exit_position = generate_maze()
        self.x = self.y = 1.5
        self.angle = 0.0
        self.moves = 0
        self.finished = False

    @property
    def pose(self) -> Pose:
        return (self.x, self.y, self.angle)

    @property
    def heading(self) -> str:
        return COMPASS[round(self.angle / (math.pi / 2)) % 4]

    def _tile(self, x: int, y: int) -> int:
        return self.maze[y][x] if 0 <= x < MAP_SIZE and 0 <= y < MAP_SIZE else 1

    # ============================================================================
    # 🔹 Actions
    # ============================================================================
    def _step(self, offset: float, direction: int, text: str) -> str:
        """Avance d'une case dans la direction (cap + offset). offset = 0 : avant/arrière, ±90° : côtés."""
        if self.finished:
            return "La partie est déjà terminée."
        a = self.angle + offset
        dx, dy = round(math.cos(a)) * direction, round(math.sin(a)) * direction
        cx, cy = int(self.x), int(self.y)
        tile = self._tile(cx + dx, cy + dy)

        if tile == 1:
            return "🧱 Un mur bloque le passage !"
        self.moves += 1
        if tile == 3:  # on reste devant le logo, face à lui
            self.finished = True
            self.angle = math.atan2(dy, dx) % (2 * math.pi)
            return "🎉 **Discord retrouvé !** Tu as trouvé le logo !"
        self.x, self.y = cx + dx + 0.5, cy + dy + 0.5
        return text

    def move(self, direction: int) -> str:
        """1 = avancer, -1 = reculer."""
        return self._step(0.0, direction, "Continue à chercher le logo Discord…")

    def strafe(self, direction: int) -> str:
        """1 = pas à droite, -1 = pas à gauche (sans tourner)."""
        return self._step(math.pi / 2, direction, "Tu te décales sur le côté.")

    def turn(self, direction: int) -> str:
        if self.finished:
            return "La partie est déjà terminée."
        self.angle = (self.angle + direction * math.pi / 2) % (2 * math.pi)
        self.moves += 1
        return "Tu changes de direction."

    # ============================================================================
    # 🔹 Rendu d'une image
    # ============================================================================
    def render(self, pose: Pose) -> Image.Image:
        px, py, ang = pose
        a = get_assets()
        fx, fy = math.cos(ang), math.sin(ang)
        rx, ry = -fy, fx
        t = FLOOR_PX

        # Sol et plafond : une transformation perspective chacun (en C, très rapide).
        coeffs = (
            2 * t * EYE * rx, 2 * t * px, 2 * t * (0.5 * px + EYE * FOCAL * fx - EYE * rx * WIDTH / 2),
            2 * t * EYE * ry, 2 * t * py, 2 * t * (0.5 * py + EYE * FOCAL * fy - EYE * ry * WIDTH / 2),
            0.0, 2.0,
        )
        floor = a["floor"].transform((WIDTH, HALF), Image.PERSPECTIVE, coeffs, Image.BILINEAR)
        ceil = a["ceiling"].transform((WIDTH, HALF), Image.PERSPECTIVE, coeffs, Image.BILINEAR)
        frame = Image.new("RGB", (WIDTH, HEIGHT))
        frame.paste(ImageOps.flip(ImageChops.multiply(ceil, a["fog"])), (0, 0))
        frame.paste(ImageChops.multiply(floor, a["fog"]), (0, HALF))

        # Murs : une colonne de texture étirée par rayon.
        rays = WIDTH // COL_W
        half_tan = math.tan(FOV / 2)
        for i in range(rays):
            cam = 2 * (i + 0.5) / rays - 1
            dist, side, wx, tile = cast_ray(self.maze, px, py, fx + rx * cam * half_tan, fy + ry * cam * half_tan)
            shade = min(1.0, dist / FOG_DIST) * FOG_MAX + (SIDE_SHADE if side else 0)
            tex = a["walls"][tile][min(LEVELS - 1, int(shade / SHADE_RANGE * (LEVELS - 1) + 0.5))]
            tx = min(TEX - 1, int(wx * TEX))
            lh = max(1, int(FOCAL / dist))
            if lh > HEIGHT:  # mur plus haut que l'écran : on ne garde que le milieu
                y0 = int(TEX * (1 - HEIGHT / lh) / 2)
                col = tex.crop((tx, y0, tx + 1, max(y0 + 1, TEX - y0))).resize((COL_W, HEIGHT), Image.NEAREST)
                frame.paste(col, (i * COL_W, 0))
            else:
                col = tex.crop((tx, 0, tx + 1, TEX)).resize((COL_W, lh), Image.NEAREST)
                frame.paste(col, (i * COL_W, (HEIGHT - lh) // 2))
        return frame

    # ============================================================================
    # 🔹 Export GIF
    # ============================================================================
    @staticmethod
    def _gif(frames: list) -> io.BytesIO:
        frames = quantize_frames(frames)
        out = io.BytesIO()
        frames[0].save(out, "GIF", save_all=True, append_images=frames[1:], duration=ANIM_MS, optimize=False)
        out.seek(0)
        return out

    def render_gif(self) -> io.BytesIO:
        """Image fixe de la position actuelle."""
        return self._gif([self.render(self.pose)])

    def render_animation(self, start: Pose, end: Pose) -> io.BytesIO:
        """Animation start -> end (lecture unique, s'arrête sur la vue finale)."""
        sx, sy, sa = start
        ex, ey, ea = end
        delta = (ea - sa + math.pi) % (2 * math.pi) - math.pi
        frames = []
        for i in range(ANIM_FRAMES):
            p = i / (ANIM_FRAMES - 1)
            p = p * p * (3 - 2 * p)  # accélération/décélération douces
            frames.append(self.render((sx + (ex - sx) * p, sy + (ey - sy) * p, (sa + delta * p) % (2 * math.pi))))
        return self._gif(frames)


# ================================================================================
# 🎛️ UI — Vue de jeu
# ================================================================================
class MazeView(discord.ui.View):

    def __init__(self, owner_id: int, game: MazeGame):
        super().__init__(timeout=GAME_TIMEOUT)
        self.owner_id = owner_id
        self.game = game
        self.message: discord.Message | None = None
        self.status = START_TEXT
        self.lock = asyncio.Lock()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.owner_id:
            return True
        await safe_respond(interaction, "⛔ Cette partie ne t'appartient pas. Lance `/labyscord` pour créer la tienne.", ephemeral=True)
        return False

    def make_embed(self) -> discord.Embed:
        g = self.game
        embed = discord.Embed(
            title="🎉 Discord retrouvé !" if g.finished else "🧱 Labyscord",
            description=f"Tu as trouvé le logo en **{g.moves}** actions !" if g.finished else self.status,
            color=discord.Color.green() if g.finished else discord.Color.blurple(),
        )
        embed.set_image(url="attachment://labyscord.gif")
        embed.add_field(name="👣 Actions", value=str(g.moves))
        embed.add_field(name="🧭 Cap", value=g.heading)
        embed.add_field(name="📍 Position", value=f"{int(g.x) + 1}, {int(g.y) + 1}")
        embed.add_field(name="👤 Joueur", value=f"<@{self.owner_id}>")
        embed.set_footer(text="Expire après 3 minutes d'inactivité")
        return embed

    async def refresh(self, start: Pose | None = None):
        """Régénère l'image (dans un thread, pour ne pas bloquer le bot) et met le message à jour."""
        end = self.game.pose
        if start is not None and start != end:
            data = await asyncio.to_thread(self.game.render_animation, start, end)
        else:
            data = await asyncio.to_thread(self.game.render_gif)
        await safe_edit(
            self.message,
            embed=self.make_embed(),
            attachments=[discord.File(data, filename="labyscord.gif")],
            view=self,
        )

    async def act(self, interaction: discord.Interaction, action: str):
        await interaction.response.defer()
        async with self.lock:
            if self.game.finished:
                return
            start = self.game.pose
            self.status = {
                "forward": lambda: self.game.move(1),
                "back": lambda: self.game.move(-1),
                "strafe_left": lambda: self.game.strafe(-1),
                "strafe_right": lambda: self.game.strafe(1),
                "left": lambda: self.game.turn(-1),
                "right": lambda: self.game.turn(1),
            }[action]()
            if self.game.finished:
                for child in self.children:
                    child.disabled = child.custom_id != "labyscord:restart"
            await self.refresh(start)

    # ============================================================================
    # 🔹 Boutons
    # ============================================================================
    # Ligne 1 : tourner gauche / avancer / tourner droite
    @discord.ui.button(label="↶", style=discord.ButtonStyle.secondary, row=0)
    async def left(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.act(interaction, "left")

    @discord.ui.button(label="▲", style=discord.ButtonStyle.primary, row=0)
    async def forward(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.act(interaction, "forward")

    @discord.ui.button(label="↷", style=discord.ButtonStyle.secondary, row=0)
    async def right(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.act(interaction, "right")

    # Ligne 2 : straff gauche / reculer / straff droite / recommencer
    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary, row=1)
    async def strafe_left(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.act(interaction, "strafe_left")

    @discord.ui.button(label="▼", style=discord.ButtonStyle.secondary, row=1)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.act(interaction, "back")

    @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary, row=1)
    async def strafe_right(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.act(interaction, "strafe_right")

    @discord.ui.button(label="Recommencer", emoji="🔄", style=discord.ButtonStyle.success, row=1, custom_id="labyscord:restart")
    async def restart(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        async with self.lock:
            self.game = MazeGame()
            self.status = START_TEXT
            for child in self.children:
                child.disabled = False
            await self.refresh()

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message:
            try:
                await safe_edit(self.message, view=self)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                pass


# ================================================================================
# 🧠 Cog principal
# ================================================================================
class Labyscord(commands.Cog):
    """
    Commande /labyscord et !labyscord — Labyrinthe 3D à explorer, retrouve le logo Discord.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ============================================================================
    # 🔹 Fonction interne commune
    # ============================================================================
    async def _start_game(self, channel: discord.abc.Messageable, owner_id: int):
        game = MazeGame()
        view = MazeView(owner_id, game)
        data = await asyncio.to_thread(game.render_gif)
        view.message = await safe_send(
            channel,
            embed=view.make_embed(),
            file=discord.File(data, filename="labyscord.gif"),
            view=view,
        )

    # ============================================================================
    # 🔹 Commande SLASH
    # ============================================================================
    @app_commands.command(name="labyscord", description="Explore un labyrinthe 3D et retrouve le logo Discord.")
    @app_commands.checks.cooldown(rate=1, per=15.0, key=lambda i: i.user.id)
    async def slash_labyscord(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self._start_game(interaction.channel, interaction.user.id)
        await interaction.delete_original_response()

    # ============================================================================
    # 🔹 Commande PREFIX
    # ============================================================================
    @commands.command(name="labyscord")
    @commands.cooldown(1, 15.0, commands.BucketType.user)
    async def prefix_labyscord(self, ctx: commands.Context):
        await self._start_game(ctx.channel, ctx.author.id)

    @prefix_labyscord.error
    async def prefix_labyscord_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.CommandOnCooldown):
            await safe_send(ctx.channel, f"⏳ Attends encore **{max(1, math.ceil(error.retry_after))} seconde(s)** avant de relancer une partie.")
            return
        raise error


# ================================================================================
# 🔌 Setup du Cog
# ================================================================================
async def setup(bot: commands.Bot):
    cog = Labyscord(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Fun&Random"
    await bot.add_cog(cog)
