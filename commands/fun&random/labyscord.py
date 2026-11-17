
# ================================================================================
# 📌 labyscord.py
# Objectif : Jeu 3D à la première personne dans un labyrinthe aléatoire.
#            Retrouve le logo Discord en explorant les couloirs.
# Catégorie : Fun
# Accès : Tous (une partie privée par joueur)
# Cooldown : 15s (slash) / 15s (prefix)
# ================================================================================
#
# 📦 Dépendances :
#   pip install -U discord.py Pillow
#
# 📂 Emplacement :
#   commands/fun/labyscord.py
#
# 🎛️ Commandes :
#   /labyscord
#   %labyscord (ou le préfixe configuré sur ton bot)
#
# 🧠 Fonctionnement :
#   - Génération procédurale d'un labyrinthe 15x15.
#   - Vue 3D à la première personne par raycasting.
#   - Textures générées avec Pillow.
#   - Déplacements et rotations animés en GIF (lecture unique).
#   - Chaque animation s'arrête sur la vue finale.
#   - Une partie privée par joueur.
#   - Le joueur qui lance la commande est le seul à pouvoir jouer.
#
# 🔌 Chargement :
#   await bot.load_extension("commands.fun.labyscord")
#
# Note : Les GIF sont générés à chaque action. Discord ne permet pas de
# reproduire une animation 3D continue comme un canvas HTML.
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
from PIL import Image, ImageDraw


# ================================================================================
# 📦 Modules internes
# ================================================================================

from utils.discord_anti429 import safe_send, safe_edit, safe_respond, safe_delete


# ================================================================================
# ⚙️ CONFIGURATION
# ================================================================================

WIDTH = 320
HEIGHT = 200
HALF_HEIGHT = HEIGHT // 2

MAP_SIZE = 15

FOV = math.radians(66)
FOCAL = (WIDTH / 2) / math.tan(FOV / 2)

TEXTURE_SIZE = 64
FLOOR_PIXELS = 24

FOG_DISTANCE = 14
FOG_MAX = 0.40

GAME_TIMEOUT = 180

ANIMATION_FRAMES = 5
ANIMATION_DURATION = 90

MOVE_LABEL = "Trouve le logo Discord !"


# ================================================================================
# 🎨 TEXTURES
# ================================================================================

def make_brick_texture() -> Image.Image:
    """Génère une texture de briques rouges."""

    image = Image.new(
        "RGB",
        (TEXTURE_SIZE, TEXTURE_SIZE),
        "#e8e2dc"
    )

    draw = ImageDraw.Draw(image)

    for row in range(4):
        y = row * 16
        offset = 0 if row % 2 == 0 else 16

        for bx in range(-1, 3):
            x = bx * 32 + offset
            variation = random.randint(-18, 14)

            red = max(0, min(255, 178 + variation))
            green = max(0, min(255, 30 + variation // 3))
            blue = max(0, min(255, 36 + variation // 3))

            draw.rectangle(
                (x + 2, y + 2, x + 29, y + 13),
                fill=(red, green, blue)
            )

            draw.line(
                (x + 2, y + 2, x + 29, y + 2),
                fill=(
                    max(0, min(255, 205 + variation)),
                    60,
                    60
                )
            )

            draw.line(
                (x + 2, y + 13, x + 29, y + 13),
                fill=(
                    max(0, min(255, 130 + variation)),
                    20,
                    26
                )
            )

    pixels = image.load()

    for _ in range(1800):
        x = random.randrange(TEXTURE_SIZE)
        y = random.randrange(TEXTURE_SIZE)

        r, g, b = pixels[x, y]
        amount = random.randint(0, 18)

        if random.random() > 0.5:
            pixels[x, y] = (
                min(255, r + amount),
                min(255, g + amount),
                min(255, b + amount)
            )
        else:
            pixels[x, y] = (
                max(0, r - amount),
                max(0, g - amount),
                max(0, b - amount)
            )

    return image


def make_logo_texture(brick: Image.Image) -> Image.Image:
    """Génère le logo Discord sur une texture de briques."""

    image = brick.copy()
    draw = ImageDraw.Draw(image)

    draw.rounded_rectangle(
        (10, 16, 53, 47),
        radius=12,
        fill="#5865f2"
    )

    draw.polygon(
        ((20, 45), (16, 56), (30, 47)),
        fill="#5865f2"
    )

    draw.polygon(
        ((44, 45), (48, 56), (34, 47)),
        fill="#5865f2"
    )

    for x in (24, 40):
        draw.ellipse(
            (x - 5, 26, x + 5, 38),
            fill="white"
        )

        draw.ellipse(
            (x - 2, 29, x + 2, 35),
            fill="#20203c"
        )

    return image


def make_ground_texture(
    size: int,
    ceiling: bool = False
) -> Image.Image:
    """Génère le sol beige ou le plafond carrelé."""

    if ceiling:
        image = Image.new(
            "RGB",
            (size, size),
            "#c6d1d2"
        )

        pixels = image.load()

        for _ in range(size * size // 3):
            x = random.randrange(size)
            y = random.randrange(size)

            r, g, b = pixels[x, y]
            amount = random.randint(0, 18)

            if random.random() > 0.5:
                pixels[x, y] = (
                    min(255, r + amount),
                    min(255, g + amount),
                    min(255, b + amount)
                )
            else:
                pixels[x, y] = (
                    max(0, r - amount),
                    max(0, g - amount),
                    max(0, b - amount)
                )

        draw = ImageDraw.Draw(image)

        for k in range(0, size, FLOOR_PIXELS):
            draw.line(
                (k, 0, k, size),
                fill="#84999d",
                width=1
            )

            draw.line(
                (0, k, size, k),
                fill="#84999d",
                width=1
            )

        return image

    image = Image.new(
        "RGB",
        (size, size),
        "#d6ae78"
    )

    pixels = image.load()

    for _ in range(size * size // 2):
        x = random.randrange(size)
        y = random.randrange(size)

        r, g, b = pixels[x, y]
        amount = random.randint(0, 25)

        if random.random() > 0.5:
            pixels[x, y] = (
                min(255, r + amount),
                min(255, g + amount),
                min(255, b + amount)
            )
        else:
            pixels[x, y] = (
                max(0, r - amount),
                max(0, g - amount),
                max(0, b - amount)
            )

    draw = ImageDraw.Draw(image)

    for y in range(0, size, 12):
        draw.line(
            (0, y, size, y),
            fill=(150, 110, 65),
            width=1
        )

    return image


# ================================================================================
# 🧩 GÉNÉRATION DU LABYRINTHE
# ================================================================================

def generate_maze() -> tuple[list[list[int]], tuple[int, int]]:
    """Génère un labyrinthe et place le logo à son extrémité."""

    maze = [
        [1 for _ in range(MAP_SIZE)]
        for _ in range(MAP_SIZE)
    ]

    stack = [(1, 1)]
    maze[1][1] = 0

    while stack:
        x, y = stack[-1]

        directions = [
            (2, 0),
            (-2, 0),
            (0, 2),
            (0, -2)
        ]

        random.shuffle(directions)

        carved = False

        for dx, dy in directions:
            nx = x + dx
            ny = y + dy

            if (
                0 < nx < MAP_SIZE - 1
                and 0 < ny < MAP_SIZE - 1
                and maze[ny][nx] == 1
            ):
                maze[y + dy // 2][x + dx // 2] = 0
                maze[ny][nx] = 0

                stack.append((nx, ny))
                carved = True

                break

        if not carved:
            stack.pop()

    # Ouvertures supplémentaires.

    candidates = []

    for y in range(1, MAP_SIZE - 1):
        for x in range(1, MAP_SIZE - 1):

            if maze[y][x] != 1:
                continue

            horizontal = (
                maze[y][x - 1] == 0
                and maze[y][x + 1] == 0
            )

            vertical = (
                maze[y - 1][x] == 0
                and maze[y + 1][x] == 0
            )

            if horizontal or vertical:
                candidates.append((x, y))

    random.shuffle(candidates)

    for x, y in candidates[:MAP_SIZE]:
        maze[y][x] = 0

    # Recherche BFS de la case la plus éloignée.

    distances = [
        [-1 for _ in range(MAP_SIZE)]
        for _ in range(MAP_SIZE)
    ]

    distances[1][1] = 0

    queue = deque([(1, 1)])
    farthest = (1, 1)

    while queue:
        x, y = queue.popleft()

        if distances[y][x] > distances[farthest[1]][farthest[0]]:
            farthest = (x, y)

        for dx, dy in (
            (1, 0),
            (-1, 0),
            (0, 1),
            (0, -1)
        ):
            nx = x + dx
            ny = y + dy

            if (
                0 <= nx < MAP_SIZE
                and 0 <= ny < MAP_SIZE
                and maze[ny][nx] == 0
                and distances[ny][nx] == -1
            ):
                distances[ny][nx] = distances[y][x] + 1
                queue.append((nx, ny))

    maze[farthest[1]][farthest[0]] = 3

    return maze, farthest


# ================================================================================
# 🎮 MOTEUR 3D
# ================================================================================

class MazeGame:

    def __init__(self):
        self.maze, self.exit_position = generate_maze()

        self.x = 1.5
        self.y = 1.5
        self.angle = 0.0

        self.moves = 0
        self.finished = False

        self.brick = make_brick_texture()
        self.logo = make_logo_texture(self.brick)

        texture_size = MAP_SIZE * FLOOR_PIXELS

        self.floor = make_ground_texture(texture_size)
        self.ceiling = make_ground_texture(
            texture_size,
            ceiling=True
        )

    # ============================================================================
    # 🔹 Collision
    # ============================================================================

    def get_tile(self, x: float, y: float) -> int:
        tx = math.floor(x)
        ty = math.floor(y)

        if (
            tx < 0
            or ty < 0
            or tx >= MAP_SIZE
            or ty >= MAP_SIZE
        ):
            return 1

        return self.maze[ty][tx]

    # ============================================================================
    # 🔹 Déplacement
    # ============================================================================

    def move(self, direction: int) -> str:

        if self.finished:
            return "La partie est déjà terminée."

        dx = round(math.cos(self.angle)) * direction
        dy = round(math.sin(self.angle)) * direction

        target_x = math.floor(self.x) + dx + 0.5
        target_y = math.floor(self.y) + dy + 0.5

        tile = self.get_tile(target_x, target_y)

        if tile == 1:
            return "🧱 Un mur bloque le passage !"

        self.x = target_x
        self.y = target_y

        self.moves += 1

        if tile == 3:
            self.finished = True

            return (
                "🎉 **Discord retrouvé !** "
                "Tu as trouvé le logo !"
            )

        return "Continue à chercher le logo Discord…"

    # ============================================================================
    # 🔹 Rotation
    # ============================================================================

    def turn(self, direction: int) -> str:

        if self.finished:
            return "La partie est déjà terminée."

        self.angle = (
            self.angle + direction * math.pi / 2
        ) % (math.pi * 2)

        self.moves += 1

        return "Tu changes de direction."

    # ============================================================================
    # 🔹 Assombrissement
    # ============================================================================

    @staticmethod
    def _fog(
        color: tuple[int, int, int],
        amount: float
    ) -> tuple[int, int, int]:

        shade = max(0.0, 1.0 - amount)

        return (
            int(color[0] * shade),
            int(color[1] * shade),
            int(color[2] * shade)
        )

    # ============================================================================
    # 🔹 Raycasting
    # ============================================================================

    def _cast_ray(
        self,
        px: float,
        py: float,
        dx: float,
        dy: float
    ):

        mx = math.floor(px)
        my = math.floor(py)

        ddx = abs(1 / dx) if dx != 0 else 1e30
        ddy = abs(1 / dy) if dy != 0 else 1e30

        if dx < 0:
            sx = -1
            sdx = (px - mx) * ddx
        else:
            sx = 1
            sdx = (mx + 1 - px) * ddx

        if dy < 0:
            sy = -1
            sdy = (py - my) * ddy
        else:
            sy = 1
            sdy = (my + 1 - py) * ddy

        side = 0

        for _ in range(MAP_SIZE * 4):

            if sdx < sdy:
                sdx += ddx
                mx += sx
                side = 0
            else:
                sdy += ddy
                my += sy
                side = 1

            if not (
                0 <= mx < MAP_SIZE
                and 0 <= my < MAP_SIZE
            ):
                return 99.0, 0, 0.0, 1

            if self.maze[my][mx] != 0:
                break

        distance = (
            sdx - ddx
            if side == 0
            else sdy - ddy
        )

        if side == 0:
            wall_x = py + distance * dy
            wall_x -= math.floor(wall_x)

            if dx > 0:
                wall_x = 1 - wall_x

        else:
            wall_x = px + distance * dx
            wall_x -= math.floor(wall_x)

            if dy < 0:
                wall_x = 1 - wall_x

        return (
            max(0.05, distance),
            side,
            wall_x,
            self.maze[my][mx]
        )

    # ============================================================================
    # 🔹 Rendu PNG
    # ============================================================================

    def render(self) -> io.BytesIO:

        image = Image.new(
            "RGB",
            (WIDTH, HEIGHT),
            "black"
        )

        pixels = image.load()

        forward_x = math.cos(self.angle)
        forward_y = math.sin(self.angle)

        right_x = -forward_y
        right_y = forward_x

        texture_size = MAP_SIZE * FLOOR_PIXELS
        half_tan = math.tan(FOV / 2)

        floor_pixels = self.floor.load()
        ceiling_pixels = self.ceiling.load()

        # Sol et plafond.

        for screen_y in range(HEIGHT):

            if screen_y == HALF_HEIGHT:
                continue

            is_floor = screen_y > HALF_HEIGHT

            row_distance = abs(screen_y - HALF_HEIGHT)

            distance = 0.5 * FOCAL / row_distance

            fog = min(
                1.0,
                distance / FOG_DISTANCE
            ) * FOG_MAX

            shade = 1.0 - fog

            texture_pixels = (
                floor_pixels
                if is_floor
                else ceiling_pixels
            )

            for screen_x in range(WIDTH):

                camera_x = (
                    2 * (screen_x + 0.5) / WIDTH
                ) - 1

                ray_x = (
                    forward_x
                    + right_x * camera_x * half_tan
                )

                ray_y = (
                    forward_y
                    + right_y * camera_x * half_tan
                )

                world_x = self.x + ray_x * distance
                world_y = self.y + ray_y * distance

                tx = int(world_x * FLOOR_PIXELS) % texture_size
                ty = int(world_y * FLOOR_PIXELS) % texture_size

                r, g, b = texture_pixels[tx, ty]

                pixels[screen_x, screen_y] = (
                    int(r * shade),
                    int(g * shade),
                    int(b * shade)
                )

        # Murs.

        for ray_index in range(WIDTH // 2):

            camera_x = (
                2 * (ray_index + 0.5) / (WIDTH // 2)
            ) - 1

            ray_x = (
                forward_x
                - math.sin(self.angle) * camera_x * half_tan
            )

            ray_y = (
                forward_y
                + math.cos(self.angle) * camera_x * half_tan
            )

            distance, side, wall_x, tile = self._cast_ray(
                self.x,
                self.y,
                ray_x,
                ray_y
            )

            wall_height = max(
                1,
                int(FOCAL / distance)
            )

            top = (HEIGHT - wall_height) // 2
            bottom = top + wall_height

            visible_top = max(0, top)
            visible_bottom = min(HEIGHT, bottom)

            if visible_bottom <= visible_top:
                continue

            texture = (
                self.logo
                if tile == 3
                else self.brick
            )

            texture_x = min(
                TEXTURE_SIZE - 1,
                int(wall_x * TEXTURE_SIZE)
            )

            darkness = (
                min(1.0, distance / FOG_DISTANCE)
                * FOG_MAX
            )

            if side:
                darkness += 0.12

            darkness = min(0.8, darkness)

            tex_pixels = texture.load()

            for screen_y in range(
                visible_top,
                visible_bottom
            ):

                source_y = int(
                    (screen_y - top)
                    / wall_height
                    * TEXTURE_SIZE
                )

                source_y = max(
                    0,
                    min(TEXTURE_SIZE - 1, source_y)
                )

                color = self._fog(
                    tex_pixels[texture_x, source_y],
                    darkness
                )

                sx = ray_index * 2

                pixels[sx, screen_y] = color

                if sx + 1 < WIDTH:
                    pixels[sx + 1, screen_y] = color

        output = io.BytesIO()

        image.save(
            output,
            format="PNG",
            optimize=True
        )

        output.seek(0)

        return output

    # ============================================================================
    # 🔹 Conversion GIF
    # ============================================================================

    def render_gif(self) -> io.BytesIO:
        """Convertit une image du jeu en GIF valide."""

        source = self.render()

        image = Image.open(source).convert("RGB")

        output = io.BytesIO()

        image.save(
            output,
            format="GIF",
            optimize=True
        )

        output.seek(0)

        return output

    # ============================================================================
    # 🔹 Animation GIF
    # ============================================================================

    def render_animation(
        self,
        start: tuple[float, float, float],
        end: tuple[float, float, float]
    ) -> io.BytesIO:

        frames = []

        start_x, start_y, start_angle = start
        end_x, end_y, end_angle = end

        original = (
            self.x,
            self.y,
            self.angle
        )

        angle_delta = (
            (end_angle - start_angle + math.pi)
            % (2 * math.pi)
        ) - math.pi

        try:

            for index in range(ANIMATION_FRAMES):

                progress = index / (ANIMATION_FRAMES - 1)

                # Interpolation fluide.

                progress = (
                    progress
                    * progress
                    * (3 - 2 * progress)
                )

                self.x = (
                    start_x
                    + (end_x - start_x) * progress
                )

                self.y = (
                    start_y
                    + (end_y - start_y) * progress
                )

                self.angle = (
                    start_angle
                    + angle_delta * progress
                ) % (math.pi * 2)

                frame_data = self.render()

                frame = Image.open(
                    frame_data
                ).convert("RGB")

                frames.append(frame.copy())

        finally:

            self.x = original[0]
            self.y = original[1]
            self.angle = original[2]

        # ========================================================================
        # 🔹 Export du GIF (lecture unique)
        # ========================================================================

        output = io.BytesIO()

        frames[0].save(
            output,
            format="GIF",
            save_all=True,
            append_images=frames[1:],
            duration=ANIMATION_DURATION,
            optimize=True
        )

        output.seek(0)

        return output


# ================================================================================
# 🎛️ INTERFACE DISCORD
# ================================================================================

class MazeView(discord.ui.View):

    def __init__(
        self,
        owner_id: int,
        game: MazeGame
    ):

        super().__init__(
            timeout=GAME_TIMEOUT
        )

        self.owner_id = owner_id
        self.game = game

        self.message: discord.Message | None = None

        self.last_status = MOVE_LABEL

        self.lock = asyncio.Lock()

    # ============================================================================
    # 🔹 Vérification du propriétaire
    # ============================================================================

    async def interaction_check(
        self,
        interaction: discord.Interaction
    ) -> bool:

        if interaction.user.id != self.owner_id:

            await safe_respond(
                interaction,
                "⛔ Cette partie ne t'appartient pas. "
                "Lance `/labyscord` pour créer la tienne.",
                ephemeral=True
            )

            return False

        return True

    # ============================================================================
    # 🔹 Embed
    # ============================================================================

    def make_embed(self) -> discord.Embed:

        if self.game.finished:

            title = "🎉 Discord retrouvé !"

            description = (
                "Tu as trouvé le logo Discord "
                "et terminé le labyrinthe."
            )

            color = discord.Color.green()

        else:

            title = "🧱 Labyscord"

            description = self.last_status

            color = discord.Color.blurple()

        embed = discord.Embed(
            title=title,
            description=description,
            color=color
        )

        embed.set_image(
            url="attachment://labyscord.gif"
        )

        embed.add_field(
            name="👣 Actions",
            value=str(self.game.moves),
            inline=True
        )

        embed.add_field(
            name="📍 Position",
            value=(
                f"{math.floor(self.game.x) + 1}, "
                f"{math.floor(self.game.y) + 1}"
            ),
            inline=True
        )

        embed.set_footer(
            text=(
                f"Partie de {self.owner_name} "
                "• Expire après 3 minutes d'inactivité"
            )
        )

        return embed

    @property
    def owner_name(self) -> str:
        return f"<@{self.owner_id}>"

    # ============================================================================
    # 🔹 Actualisation de l'affichage
    # ============================================================================

    async def refresh(
        self,
        interaction: discord.Interaction,
        start: tuple[float, float, float] | None = None
    ):

        if self.game.finished or start is None:

            image_data = self.game.render_gif()

        else:

            end = (
                self.game.x,
                self.game.y,
                self.game.angle
            )

            changed = start != end

            if changed:

                image_data = self.game.render_animation(
                    start,
                    end
                )

            else:

                image_data = self.game.render_gif()

        file = discord.File(
            image_data,
            filename="labyscord.gif"
        )

        await safe_edit(
            self.message,
            embed=self.make_embed(),
            attachments=[file],
            view=self
        )

    # ============================================================================
    # 🔹 Actions
    # ============================================================================

    async def act(
        self,
        interaction: discord.Interaction,
        action: str
    ):

        async with self.lock:

            if self.game.finished:

                await safe_respond(
                    interaction,
                    "🏁 Cette partie est terminée. "
                    "Utilise le bouton Recommencer.",
                    ephemeral=True
                )

                return

            start = (
                self.game.x,
                self.game.y,
                self.game.angle
            )

            if action == "forward":

                self.last_status = self.game.move(1)

            elif action == "back":

                self.last_status = self.game.move(-1)

            elif action == "left":

                self.last_status = self.game.turn(-1)

            elif action == "right":

                self.last_status = self.game.turn(1)

            if self.game.finished:

                for child in self.children:

                    if (
                        isinstance(child, discord.ui.Button)
                        and child.custom_id != "labyscord:restart"
                    ):

                        child.disabled = True

            await interaction.response.defer()

            await self.refresh(
                interaction,
                start
            )

    # ============================================================================
    # 🔹 Boutons
    # ============================================================================

    @discord.ui.button(
        label="▲",
        style=discord.ButtonStyle.secondary,
        row=0,
        custom_id="labyscord:forward"
    )
    async def forward(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await self.act(
            interaction,
            "forward"
        )

    @discord.ui.button(
        label="↶",
        style=discord.ButtonStyle.secondary,
        row=1,
        custom_id="labyscord:left"
    )
    async def left(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await self.act(
            interaction,
            "left"
        )

    @discord.ui.button(
        label="▼",
        style=discord.ButtonStyle.secondary,
        row=1,
        custom_id="labyscord:back"
    )
    async def back(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await self.act(
            interaction,
            "back"
        )

    @discord.ui.button(
        label="↷",
        style=discord.ButtonStyle.secondary,
        row=1,
        custom_id="labyscord:right"
    )
    async def right(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await self.act(
            interaction,
            "right"
        )

    # ============================================================================
    # 🔹 Recommencer
    # ============================================================================

    @discord.ui.button(
        label="Recommencer",
        emoji="🔄",
        style=discord.ButtonStyle.primary,
        row=2,
        custom_id="labyscord:restart"
    )
    async def restart(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        async with self.lock:

            await interaction.response.defer()

            self.game = MazeGame()

            self.last_status = MOVE_LABEL

            for child in self.children:
                child.disabled = False

            await self.refresh(interaction)

    # ============================================================================
    # 🔹 Timeout
    # ============================================================================

    async def on_timeout(self):

        for child in self.children:
            child.disabled = True

        if self.message:

            try:

                await safe_edit(
                    self.message,
                    view=self
                )

            except (
                discord.NotFound,
                discord.Forbidden,
                discord.HTTPException
            ):

                pass


# ================================================================================
# 🧠 COG PRINCIPAL
# ================================================================================

class Labyscord(commands.Cog):

    """
    Commande /labyscord et %labyscord — Labyrinthe 3D.
    """

    def __init__(self, bot: commands.Bot):

        self.bot = bot

    # ============================================================================
    # 🔹 Fonction interne commune
    # ============================================================================

    async def _start_game(
        self,
        channel: discord.abc.Messageable,
        owner_id: int
    ):

        game = MazeGame()

        view = MazeView(
            owner_id,
            game
        )

        file = discord.File(
            game.render_gif(),
            filename="labyscord.gif"
        )

        message = await safe_send(
            channel,
            embed=view.make_embed(),
            file=file,
            view=view
        )

        view.message = message

    # ============================================================================
    # 🔹 Commande SLASH
    # ============================================================================

    @app_commands.command(
        name="labyscord",
        description="Explore un labyrinthe 3D et retrouve le logo Discord."
    )
    @app_commands.checks.cooldown(
        rate=1,
        per=15.0,
        key=lambda interaction: interaction.user.id
    )
    async def slash_labyscord(
        self,
        interaction: discord.Interaction
    ):

        await interaction.response.defer()

        await self._start_game(
            interaction.channel,
            interaction.user.id
        )

        await interaction.delete_original_response()

    # ============================================================================
    # 🔹 Commande PREFIX
    # ============================================================================

    @commands.command(
        name="labyscord"
    )
    @commands.cooldown(
        1,
        15.0,
        commands.BucketType.user
    )
    async def prefix_labyscord(
        self,
        ctx: commands.Context
    ):

        await self._start_game(
            ctx.channel,
            ctx.author.id
        )

    # ============================================================================
    # 🔹 Erreur commande PREFIX
    # ============================================================================

    @prefix_labyscord.error
    async def prefix_labyscord_error(
        self,
        ctx: commands.Context,
        error: commands.CommandError
    ):

        if isinstance(
            error,
            commands.CommandOnCooldown
        ):

            remaining = max(
                1,
                math.ceil(error.retry_after)
            )

            await safe_send(
                ctx.channel,
                f"⏳ Attends encore **{remaining} seconde(s)** "
                "avant de relancer une partie."
            )
            return

        raise error


# ================================================================================
# 🔌 SETUP DU COG
# ================================================================================

async def setup(bot: commands.Bot):

    cog = Labyscord(bot)

    for command in cog.get_commands():

        if not hasattr(command, "category"):
            command.category = "Fun&Random"

    await bot.add_cog(cog)
