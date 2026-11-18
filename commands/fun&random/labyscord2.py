# ================================================================================
# 📌 labyscord2.py
# Objectif : Labyscord version "ultra réactive" : labyrinthe 3D à la première personne,
#            images fixes ultra légères, déplacements instantanés. Retrouve le logo Discord !
# Catégorie : Fun
# Accès : Tous (une partie privée par joueur)
# Cooldown : 15s (slash) / 15s (prefix)
# ================================================================================
#
# ⚡ Ce qui rend le jeu rapide :
#   - Images PNG fixes en palette de 96 couleurs (~8 Ko) : upload et chargement quasi instantanés.
#   - Une seule requête par clic (réponse directe à l'interaction).
#   - Un mur devant toi ? L'image n'est PAS renvoyée (juste le texte) : aucun flou.
#   - Clics en rafale : l'état du jeu avance tout de suite, l'affichage ne montre que la dernière vue.
#   - Vues déjà vues en cache + préchargement des vues les plus probables (avant, gauche, droite).
#   - Boutons "Foncer" (jusqu'au prochain carrefour) et "Demi-tour" : moins de clics.
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
WIDTH, HEIGHT = 256, 160               # petite image = rendu et envoi plus rapides
HALF = HEIGHT // 2
COL_W = 2                              # largeur d'une colonne de rayon
MAP_SIZE = 15
FOV = math.radians(66)
FOCAL = (WIDTH / 2) / math.tan(FOV / 2)
EYE = 0.5                              # hauteur des yeux (murs = 1 case de haut)
TEX = 64                               # texture des murs
FLOOR_PX = 24                          # pixels de texture sol/plafond par case
FOG_DIST = 14.0
FOG_MAX = 0.40
SIDE_SHADE = 0.10                      # murs Est/Ouest un peu plus sombres
LEVELS = 16                            # niveaux d'ombrage précalculés
SHADE_RANGE = FOG_MAX + SIDE_SHADE
PALETTE_COLORS = 96                    # couleurs des images (moins = plus léger)
GROUND_BLUR = 2.5                      # flou du bruit du sol/plafond (lisse = PNG plus léger)
PREFETCH = True                        # précalcule les vues probables pendant que tu réfléchis
GAME_TIMEOUT = 180
FILENAME = "labyscord2.png"
START_TEXT = "Trouve le logo Discord !"
COMPASS = ("➡️ Est", "⬇️ Sud", "⬅️ Ouest", "⬆️ Nord")
DIRS = ((1, 0), (0, 1), (-1, 0), (0, -1))     # Est, Sud, Ouest, Nord (cap 0..3)

Pose = tuple  # (x, y, angle)


# ================================================================================
# 🎨 Textures (générées une seule fois, partagées par toutes les parties)
# ================================================================================
def _make_brick() -> Image.Image:
    """Briques rouges, joints blancs (lisses : se compriment très bien)."""
    img = Image.new("RGB", (TEX, TEX), "#e8e2dc")
    d = ImageDraw.Draw(img)
    for row in range(4):
        y, off = row * 16, (0 if row % 2 == 0 else 16)
        for bx in range(-1, 3):
            x, v = bx * 32 + off, random.randint(-18, 14)
            d.rectangle((x + 2, y + 2, x + 29, y + 13), fill=(178 + v, 30 + v // 3, 36 + v // 3))
            d.line((x + 2, y + 2, x + 29, y + 2), fill=(205 + v, 60, 60))
            d.line((x + 2, y + 13, x + 29, y + 13), fill=(130 + v, 20, 26))
    return img


def _make_logo(brick: Image.Image) -> Image.Image:
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
    size = MAP_SIZE * FLOOR_PX
    noise = ImageOps.autocontrast(Image.effect_noise((size, size), 40).filter(ImageFilter.GaussianBlur(GROUND_BLUR)), cutoff=1)
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
    mask = Image.new("RGB", (WIDTH, HALF))
    d = ImageDraw.Draw(mask)
    for j in range(HALF):
        v = int(255 * (1 - FOG_MAX * min(1.0, EYE * FOCAL / (j + 1) / FOG_DIST)))
        d.line((0, j, WIDTH, j), fill=(v, v, v))
    return mask


_ASSETS: dict = {}


def get_assets() -> dict:
    """Crée une seule fois textures + palette commune (appelé au chargement du cog)."""
    if not _ASSETS:
        brick = _make_brick()
        walls = {1: _shade_variants(brick), 3: _shade_variants(_make_logo(brick))}
        floor, ceiling = _make_ground(False), _make_ground(True)
        # Palette commune à toutes les images : les couleurs ne "bougent" pas d'une vue à l'autre.
        sample = Image.new("RGB", (TEX * 4, TEX * 4))
        for k in range(LEVELS):
            sample.paste(walls[1][k], ((k % 4) * TEX, (k // 4) * TEX))
        sample.paste(walls[3][0], (0, 0))
        sample.paste(walls[3][6], (TEX, 0))
        sample.paste(floor.crop((0, 0, TEX * 2, TEX)), (0, 0))
        sample.paste(ceiling.crop((0, 0, TEX * 2, TEX)), (TEX * 2, 0))
        _ASSETS.update(walls=walls, floor=floor, ceiling=ceiling, fog=_make_fog_mask(),
                       palette=sample.quantize(colors=PALETTE_COLORS, method=Image.MEDIANCUT))
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

    holes = [(x, y) for y in range(1, n - 1) for x in range(1, n - 1)
             if maze[y][x] == 1 and ((maze[y][x - 1] == 0 and maze[y][x + 1] == 0)
                                     or (maze[y - 1][x] == 0 and maze[y + 1][x] == 0))]
    for x, y in random.sample(holes, min(n, len(holes))):
        maze[y][x] = 0

    dist = {(1, 1): 0}
    queue, far = deque([(1, 1)]), (1, 1)
    while queue:
        x, y = queue.popleft()
        if dist[(x, y)] > dist[far]:
            far = (x, y)
        for dx, dy in DIRS:
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


class MazeGame:

    def __init__(self):
        self.maze, self.exit_position = generate_maze()
        self.cx = self.cy = 1                 # case (le joueur est toujours au centre d'une case)
        self.dir = 0                          # cap : 0 Est, 1 Sud, 2 Ouest, 3 Nord
        self.moves = 0
        self.finished = False
        self._cache: dict = {}                # (case, cap) -> octets PNG

    @property
    def pose(self) -> Pose:
        return (self.cx + 0.5, self.cy + 0.5, self.dir * math.pi / 2)

    @property
    def heading(self) -> str:
        return COMPASS[self.dir]

    def _tile(self, x: int, y: int) -> int:
        return self.maze[y][x] if 0 <= x < MAP_SIZE and 0 <= y < MAP_SIZE else 1

    # ============================================================================
    # 🔹 Actions (instantanées : aucun rendu ici)
    # ============================================================================
    def _step(self, offset: int, sign: int, text: str) -> str:
        """Une case dans le sens (cap + offset). offset 0 = avant/arrière, ±1 = côtés."""
        if self.finished:
            return "La partie est déjà terminée."
        dx, dy = DIRS[(self.dir + offset) % 4]
        dx, dy = dx * sign, dy * sign
        tile = self._tile(self.cx + dx, self.cy + dy)
        if tile == 1:
            return "🧱 Un mur bloque le passage !"
        self.moves += 1
        if tile == 3:                          # on reste devant le logo, face à lui
            self.finished = True
            self.dir = DIRS.index((dx, dy))
            return "🎉 **Discord retrouvé !**"
        self.cx, self.cy = self.cx + dx, self.cy + dy
        return text

    def forward(self) -> str:
        return self._step(0, 1, "Tu avances.")

    def back(self) -> str:
        return self._step(0, -1, "Tu recules.")

    def strafe(self, side: int) -> str:
        return self._step(1, side, "Tu te décales sur le côté.")

    def turn(self, side: int) -> str:
        if self.finished:
            return "La partie est déjà terminée."
        self.dir = (self.dir + side) % 4
        self.moves += 1
        return "Tu changes de direction."

    def uturn(self) -> str:
        if self.finished:
            return "La partie est déjà terminée."
        self.dir = (self.dir + 2) % 4
        self.moves += 1
        return "Demi-tour !"

    def run(self) -> str:
        """Fonce tout droit jusqu'au prochain carrefour, au mur, ou au logo (1 seule action)."""
        if self.finished:
            return "La partie est déjà terminée."
        dx, dy = DIRS[self.dir]
        steps = 0
        while True:
            ahead = self._tile(self.cx + dx, self.cy + dy)
            if ahead == 1:
                break
            if ahead == 3:
                self.moves += 1
                self.finished = True
                return "🎉 **Discord retrouvé !**"
            self.cx, self.cy = self.cx + dx, self.cy + dy
            steps += 1
            if self._tile(self.cx - dy, self.cy + dx) != 1 or self._tile(self.cx + dy, self.cy - dx) != 1:
                break                          # carrefour : on s'arrête
        if steps == 0:
            return "🧱 Un mur bloque le passage !"
        self.moves += 1
        return f"Tu fonces sur **{steps}** case(s)."

    # ============================================================================
    # 🔹 Rendu d'une vue
    # ============================================================================
    def render(self, pose: Pose) -> Image.Image:
        px, py, ang = pose
        a = get_assets()
        fx, fy = math.cos(ang), math.sin(ang)
        rx, ry = -fy, fx
        t = FLOOR_PX

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

        rays = WIDTH // COL_W
        half_tan = math.tan(FOV / 2)
        for i in range(rays):
            cam = 2 * (i + 0.5) / rays - 1
            dist, side, wx, tile = cast_ray(self.maze, px, py, fx + rx * cam * half_tan, fy + ry * cam * half_tan)
            shade = min(1.0, dist / FOG_DIST) * FOG_MAX + (SIDE_SHADE if side else 0)
            tex = a["walls"][tile][min(LEVELS - 1, int(shade / SHADE_RANGE * (LEVELS - 1) + 0.5))]
            tx = min(TEX - 1, int(wx * TEX))
            lh = max(1, int(FOCAL / dist))
            if lh > HEIGHT:
                y0 = int(TEX * (1 - HEIGHT / lh) / 2)
                col = tex.crop((tx, y0, tx + 1, max(y0 + 1, TEX - y0))).resize((COL_W, HEIGHT), Image.NEAREST)
                frame.paste(col, (i * COL_W, 0))
            else:
                col = tex.crop((tx, 0, tx + 1, TEX)).resize((COL_W, lh), Image.NEAREST)
                frame.paste(col, (i * COL_W, (HEIGHT - lh) // 2))
        return frame

    def png(self, pose: Pose) -> bytes:
        """PNG de la vue (palette commune, ~8 Ko). Mis en cache : une vue n'est calculée qu'une fois."""
        key = (int(pose[0]), int(pose[1]), round(pose[2] / (math.pi / 2)) % 4)
        data = self._cache.get(key)
        if data is None:
            out = io.BytesIO()
            self.render(pose).quantize(palette=get_assets()["palette"], dither=0).save(out, "PNG", compress_level=4)
            data = self._cache[key] = out.getvalue()
        return data

    def probable_poses(self) -> list:
        """Les vues les plus probables au prochain clic : tourner à gauche/droite, avancer."""
        poses = []
        for side in (-1, 1):
            poses.append((self.cx + 0.5, self.cy + 0.5, ((self.dir + side) % 4) * math.pi / 2))
        dx, dy = DIRS[self.dir]
        if self._tile(self.cx + dx, self.cy + dy) == 0:
            poses.append((self.cx + dx + 0.5, self.cy + dy + 0.5, self.dir * math.pi / 2))
        return poses

    def warm(self, poses: list):
        """Précalcule des vues (exécuté dans un thread)."""
        try:
            for pose in poses:
                self.png(pose)
        except Exception:
            pass


# ================================================================================
# 🎛️ UI — Vue de jeu
# ================================================================================
ACTIONS = {
    "left": lambda g: g.turn(-1),
    "forward": lambda g: g.forward(),
    "right": lambda g: g.turn(1),
    "run": lambda g: g.run(),
    "strafe_left": lambda g: g.strafe(-1),
    "back": lambda g: g.back(),
    "strafe_right": lambda g: g.strafe(1),
    "uturn": lambda g: g.uturn(),
}


class MazeView(discord.ui.View):

    def __init__(self, owner_id: int, game: MazeGame):
        super().__init__(timeout=GAME_TIMEOUT)
        self.owner_id = owner_id
        self.game = game
        self.message: discord.Message | None = None
        self.status = START_TEXT
        self.busy = False                      # un affichage est en cours d'envoi
        self.dirty = False                     # d'autres clics sont arrivés pendant l'envoi
        self._task: asyncio.Task | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.owner_id:
            return True
        await safe_respond(interaction, "⛔ Cette partie ne t'appartient pas. Lance `/labyscord2` pour créer la tienne.", ephemeral=True)
        return False

    def make_embed(self) -> discord.Embed:
        g = self.game
        embed = discord.Embed(
            title="🎉 Discord retrouvé !" if g.finished else "🧱 Labyscord 2",
            description=f"<@{self.owner_id}> a trouvé le logo en **{g.moves}** actions !" if g.finished else f"{self.status}",
            color=discord.Color.green() if g.finished else discord.Color.blurple(),
        )
        embed.set_image(url=f"attachment://{FILENAME}")
        embed.set_footer(text=f"👣 {g.moves} actions  •  {g.heading}  •  📍 {g.cx + 1}, {g.cy + 1}")
        return embed

    # ============================================================================
    # 🔹 Affichage : une requête par clic, les clics en rafale sont regroupés
    # ============================================================================
    async def push(self, interaction: discord.Interaction):
        """Envoie la vue actuelle. Si un envoi est déjà en cours, on la marque à rafraîchir et on répond tout de suite."""
        if self.busy:
            self.dirty = True
            await interaction.response.defer()
            return
        self.busy = True
        try:
            first = True
            while True:
                self.dirty = False
                pose, embed = self.game.pose, self.make_embed()      # état figé pour cet envoi
                data = await asyncio.to_thread(self.game.png, pose)
                file = discord.File(io.BytesIO(data), filename=FILENAME)
                if first:
                    first = False
                    await interaction.response.edit_message(embed=embed, attachments=[file], view=self)
                else:
                    await safe_edit(self.message, embed=embed, attachments=[file], view=self)
                if not self.dirty:
                    break
        finally:
            self.busy = False
        if PREFETCH and not self.game.finished:
            self._task = asyncio.create_task(asyncio.to_thread(self.game.warm, self.game.probable_poses()))

    async def act(self, interaction: discord.Interaction, action: str):
        g = self.game
        if g.finished:
            await interaction.response.defer()
            return
        before = g.pose
        self.status = ACTIONS[action](g)                 # l'état avance immédiatement
        if g.finished:
            for child in self.children:
                child.disabled = child.custom_id != "labyscord2:restart"
        if g.pose == before and not g.finished and not self.busy:
            # Mur, rien n'a bougé : on ne renvoie PAS l'image (juste le texte) -> instantané, sans flou.
            await interaction.response.edit_message(embed=self.make_embed())
            return
        await self.push(interaction)

    # ============================================================================
    # 🔹 Boutons
    # ============================================================================
    # Ligne 1 : tourner gauche / avancer / tourner droite / foncer
    @discord.ui.button(label="↶", style=discord.ButtonStyle.secondary, row=0)
    async def left(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.act(interaction, "left")

    @discord.ui.button(label="▲", style=discord.ButtonStyle.primary, row=0)
    async def forward(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.act(interaction, "forward")

    @discord.ui.button(label="↷", style=discord.ButtonStyle.secondary, row=0)
    async def right(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.act(interaction, "right")

    @discord.ui.button(label="Foncer", emoji="⏫", style=discord.ButtonStyle.primary, row=0)
    async def run(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.act(interaction, "run")

    # Ligne 2 : straff gauche / reculer / straff droite / demi-tour / recommencer
    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary, row=1)
    async def strafe_left(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.act(interaction, "strafe_left")

    @discord.ui.button(label="▼", style=discord.ButtonStyle.secondary, row=1)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.act(interaction, "back")

    @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary, row=1)
    async def strafe_right(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.act(interaction, "strafe_right")

    @discord.ui.button(label="↩", style=discord.ButtonStyle.secondary, row=1)
    async def uturn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.act(interaction, "uturn")

    @discord.ui.button(emoji="🔄", style=discord.ButtonStyle.success, row=1, custom_id="labyscord2:restart")
    async def restart(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.game = MazeGame()
        self.status = START_TEXT
        for child in self.children:
            child.disabled = False
        await self.push(interaction)

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
class Labyscord2(commands.Cog):
    """
    Commande /labyscord2 et !labyscord2 — Labyrinthe 3D ultra réactif, retrouve le logo Discord.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        get_assets()                          # textures + palette prêtes avant la première partie

    # ============================================================================
    # 🔹 Fonction interne commune
    # ============================================================================
    async def _start_game(self, channel: discord.abc.Messageable, owner_id: int):
        game = MazeGame()
        view = MazeView(owner_id, game)
        data = await asyncio.to_thread(game.png, game.pose)
        view.message = await safe_send(
            channel,
            embed=view.make_embed(),
            file=discord.File(io.BytesIO(data), filename=FILENAME),
            view=view,
        )

    # ============================================================================
    # 🔹 Commande SLASH
    # ============================================================================
    @app_commands.command(name="labyscord2", description="Labyrinthe 3D ultra réactif : retrouve le logo Discord.")
    @app_commands.checks.cooldown(rate=1, per=15.0, key=lambda i: i.user.id)
    async def slash_labyscord2(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self._start_game(interaction.channel, interaction.user.id)
        await interaction.delete_original_response()

    # ============================================================================
    # 🔹 Commande PREFIX
    # ============================================================================
    @commands.command(name="labyscord2", help="Labyrinthe 3D ultra réactif : retrouve le logo Discord.")
    @commands.cooldown(1, 15.0, commands.BucketType.user)
    async def prefix_labyscord2(self, ctx: commands.Context):
        await self._start_game(ctx.channel, ctx.author.id)

    @prefix_labyscord2.error
    async def prefix_labyscord2_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.CommandOnCooldown):
            await safe_send(ctx.channel, f"⏳ Attends encore **{max(1, math.ceil(error.retry_after))} seconde(s)** avant de relancer une partie.")
            return
        raise error


# ================================================================================
# 🔌 Setup du Cog
# ================================================================================
async def setup(bot: commands.Bot):
    cog = Labyscord2(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Fun&Random"
    await bot.add_cog(cog)
