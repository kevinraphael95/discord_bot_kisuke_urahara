# ================================================================================
# 📌 3dpipes.py
# Objectif : Économiseur d'écran 3D Pipes animé (GIF), façon Windows 98/XP :
#            tuyaux métalliques colorés, cylindres brillants, coudes à 90°,
#            ramifications aléatoires et caméra orbitale autour du réseau.
#            Les tuyaux se développent progressivement dans un espace 3D.
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
from PIL import Image, ImageDraw, ImageFont

# ================================================================================
# 📦 Modules internes
# ================================================================================
from utils.discord_anti429 import safe_send

# ================================================================================
# ⚙️ Constantes
# ================================================================================
W, H = 320, 200

GRID_X = 9
GRID_Y = 7
GRID_Z = 7

PIPE_RADIUS = 0.135
PIPE_SIDES = 8
PIPE_SPACING = 0.85

MAX_SEGMENTS = 145
MAX_FRAMES = 52
FRAME_MS = 85
END_HOLD_MS = 4000

BRANCH_CHANCE = 0.17
STRAIGHT_CHANCE = 0.58

CAMERA_DISTANCE = 12.5
CAMERA_HEIGHT = 4.0
CAMERA_SPEED = 0.035

FOCAL = 245.0
NEAR_CLIP = 0.5

PALETTE_COLORS = 128
MAX_BYTES = 8 * 1024 * 1024

BACKGROUND = (5, 7, 13)

DIRECTIONS = (
    (1, 0, 0),
    (-1, 0, 0),
    (0, 1, 0),
    (0, -1, 0),
    (0, 0, 1),
    (0, 0, -1),
)

PIPE_COLORS = (
    (235, 65, 65),       # Rouge
    (65, 145, 245),      # Bleu
    (70, 210, 115),      # Vert
    (245, 195, 55),      # Jaune
    (185, 95, 240),      # Violet
    (40, 210, 220),      # Cyan
    (245, 125, 45),     # Orange
    (235, 100, 165),     # Rose
    (220, 225, 235),     # Argent
)

LIGHT = (-0.45, 0.8, -0.55)

# ================================================================================
# 🔧 Fonctions mathématiques 3D
# ================================================================================
def _add(a, b):
    return tuple(a[i] + b[i] for i in range(3))


def _sub(a, b):
    return tuple(a[i] - b[i] for i in range(3))


def _mul(a, k):
    return tuple(v * k for v in a)


def _dot(a, b):
    return sum(a[i] * b[i] for i in range(3))


def _cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _length(v):
    return math.sqrt(_dot(v, v))


def _normalize(v):
    length = _length(v)
    if length < 1e-9:
        return (0.0, 0.0, 0.0)
    return _mul(v, 1.0 / length)


def _clamp(v, low=0, high=255):
    return max(low, min(high, int(v)))


def _color_scale(color, factor):
    return tuple(_clamp(c * factor) for c in color)


# ================================================================================
# 🧱 Génération du réseau de tuyaux
# ================================================================================
def _inside(p):
    x, y, z = p
    return (
        -GRID_X // 2 <= x <= GRID_X // 2
        and -GRID_Y // 2 <= y <= GRID_Y // 2
        and -GRID_Z // 2 <= z <= GRID_Z // 2
    )


def _choose_direction(rng, previous, position, occupied):
    """Choisit une direction libre, avec une préférence pour la ligne droite."""
    candidates = []

    for direction in DIRECTIONS:
        if previous and direction == tuple(-v for v in previous):
            continue

        nxt = _add(position, direction)

        if not _inside(nxt):
            continue

        if nxt in occupied:
            continue

        candidates.append(direction)

    if not candidates:
        return None

    if previous in candidates and rng.random() < STRAIGHT_CHANCE:
        return previous

    return rng.choice(candidates)


def _generate_network(rng):
    """
    Construction procédurale du réseau.

    Chaque extrémité active peut continuer dans une direction libre.
    Des ramifications sont créées pendant la construction.
    Les tuyaux partagent leurs raccords aux intersections.
    """

    segments = []
    active = []
    occupied = set()

    roots = [
        ((-3, 0, 0), (1, 0, 0)),
        ((2, -2, -2), (0, 0, 1)),
        ((0, 2, 2), (-1, 0, 0)),
    ]

    for index, (position, direction) in enumerate(roots):
        occupied.add(position)

        active.append({
            "position": position,
            "direction": direction,
            "color": PIPE_COLORS[index],
        })

    while active and len(segments) < MAX_SEGMENTS:
        index = rng.randrange(len(active))
        tip = active[index]

        position = tip["position"]
        previous = tip["direction"]

        direction = _choose_direction(
            rng, previous, position, occupied
        )

        if direction is None:
            active.pop(index)
            continue

        nxt = _add(position, direction)
        color = tip["color"]

        segments.append({
            "a": position,
            "b": nxt,
            "color": color,
        })

        occupied.add(nxt)

        tip["position"] = nxt
        tip["direction"] = direction

        # Ramification : un nouveau tuyau démarre au même raccord.
        if rng.random() < BRANCH_CHANCE and len(active) < 12:
            branch = _choose_direction(
                rng, direction, nxt, occupied
            )

            if branch is not None:
                active.append({
                    "position": nxt,
                    "direction": branch,
                    "color": color,
                })

        # Une extrémité qui ne trouve plus de place est terminée.
        if len(segments) >= MAX_SEGMENTS:
            break

    return segments, occupied


# ================================================================================
# 🧭 Préparation de la géométrie des cylindres
# ================================================================================
def _cylinder_faces(segment):
    """
    Transforme un segment en faces polygonales 3D.
    Chaque cylindre possède huit faces latérales.
    """

    a = _mul(segment["a"], PIPE_SPACING)
    b = _mul(segment["b"], PIPE_SPACING)

    axis = _normalize(_sub(b, a))

    reference = (0, 1, 0)
    if abs(_dot(axis, reference)) > 0.9:
        reference = (1, 0, 0)

    u = _normalize(_cross(axis, reference))
    v = _normalize(_cross(axis, u))

    rings = []

    for center in (a, b):
        ring = []

        for i in range(PIPE_SIDES):
            angle = 2 * math.pi * i / PIPE_SIDES

            offset = _add(
                _mul(u, math.cos(angle) * PIPE_RADIUS),
                _mul(v, math.sin(angle) * PIPE_RADIUS),
            )

            ring.append(_add(center, offset))

        rings.append(ring)

    faces = []

    for i in range(PIPE_SIDES):
        j = (i + 1) % PIPE_SIDES

        normal = _normalize(
            _add(
                _mul(u, math.cos(2 * math.pi * (i + 0.5) / PIPE_SIDES)),
                _mul(v, math.sin(2 * math.pi * (i + 0.5) / PIPE_SIDES)),
            )
        )

        light = max(0.0, _dot(normal, _normalize(LIGHT)))
        brightness = 0.48 + light * 0.85

        color = _color_scale(segment["color"], brightness)

        quad = (
            rings[0][i],
            rings[0][j],
            rings[1][j],
            rings[1][i],
        )

        faces.append((quad, color))

    return faces


# ================================================================================
# 🔩 Raccords et intersections
# ================================================================================
def _build_joints(segments):
    """Récupère les points de raccord et leurs couleurs."""
    joints = {}

    for segment in segments:
        for point in (segment["a"], segment["b"]):
            point = tuple(point)

            if point not in joints:
                joints[point] = []

            joints[point].append(segment["color"])

    result = []

    for point, colors in joints.items():
        color = tuple(
            sum(c[i] for c in colors) // len(colors)
            for i in range(3)
        )

        result.append({
            "position": _mul(point, PIPE_SPACING),
            "color": color,
            "radius": PIPE_RADIUS * (1.12 if len(colors) > 2 else 1.0),
        })

    return result


# ================================================================================
# 🎥 Caméra et projection perspective
# ================================================================================
def _camera(angle):
    """Caméra orbitale autour du réseau."""

    target = (0.0, 0.0, 0.0)

    cx = math.cos(angle) * CAMERA_DISTANCE
    cz = math.sin(angle) * CAMERA_DISTANCE
    cy = CAMERA_HEIGHT

    position = (cx, cy, cz)

    forward = _normalize(_sub(target, position))
    right = _normalize(_cross(forward, (0.0, 1.0, 0.0)))
    up = _normalize(_cross(right, forward))

    return position, right, up, forward


def _project(point, camera):
    position, right, up, forward = camera

    relative = _sub(point, position)

    x = _dot(relative, right)
    y = _dot(relative, up)
    z = _dot(relative, forward)

    if z <= NEAR_CLIP:
        return None

    sx = W / 2 + x * FOCAL / z
    sy = H / 2 - y * FOCAL / z

    return sx, sy, z


# ================================================================================
# 🎨 Rendu des tuyaux 3D
# ================================================================================
def _render_frame(segments, joints, angle, progress):
    """Dessine le réseau avec profondeur, éclairage et reflets métalliques."""

    frame = Image.new("RGB", (W, H), BACKGROUND)
    draw = ImageDraw.Draw(frame)

    camera = _camera(angle)

    objects = []

    # --------------------------------------------------------------------------
    # Faces des cylindres
    # --------------------------------------------------------------------------
    for segment in segments:
        faces = _cylinder_faces(segment)

        for vertices, color in faces:
            projected = [_project(v, camera) for v in vertices]

            if any(p is None for p in projected):
                continue

            depth = sum(p[2] for p in projected) / len(projected)

            points = [(p[0], p[1]) for p in projected]

            if not all(
                math.isfinite(v)
                for point in points
                for v in point
            ):
                continue

            objects.append((
                depth,
                "face",
                points,
                color,
            ))

    # --------------------------------------------------------------------------
    # Raccords sphériques
    # --------------------------------------------------------------------------
    for joint in joints:
        projected = _project(joint["position"], camera)

        if projected is None:
            continue

        sx, sy, depth = projected

        radius = max(
            1,
            int(joint["radius"] * FOCAL / depth)
        )

        if radius > 35:
            continue

        color = joint["color"]

        objects.append((
            depth,
            "joint",
            (sx, sy, radius),
            color,
        ))

    # --------------------------------------------------------------------------
    # Tri par profondeur : arrière-plan avant premier plan
    # --------------------------------------------------------------------------
    objects.sort(key=lambda item: item[0], reverse=True)

    for depth, kind, geometry, color in objects:

        if kind == "face":
            points = geometry

            if not any(
                -20 <= x <= W + 20 and -20 <= y <= H + 20
                for x, y in points
            ):
                continue

            draw.polygon(
                points,
                fill=color,
                outline=_color_scale(color, 0.48),
            )

            # Reflet métallique sur une arête.
            p1, p2, p3, p4 = points

            draw.line(
                [p1, p4],
                fill=_color_scale(color, 1.45),
                width=1,
            )

        else:
            sx, sy, radius = geometry

            if (
                sx + radius < 0 or sx - radius > W
                or sy + radius < 0 or sy - radius > H
            ):
                continue

            base = color

            # Corps sphérique du raccord.
            draw.ellipse(
                [
                    sx - radius,
                    sy - radius,
                    sx + radius,
                    sy + radius,
                ],
                fill=_color_scale(base, 0.68),
                outline=_color_scale(base, 1.25),
            )

            # Reflet supérieur.
            if radius >= 3:
                draw.ellipse(
                    [
                        sx - radius * 0.48,
                        sy - radius * 0.55,
                        sx + radius * 0.15,
                        sy - radius * 0.05,
                    ],
                    fill=_color_scale(base, 1.55),
                )

    # --------------------------------------------------------------------------
    # Cadre discret façon économiseur de veille
    # --------------------------------------------------------------------------
    draw.line(
        [(0, H - 1), (W, H - 1)],
        fill=(15, 19, 29),
    )

    return frame


# ================================================================================
# 🏁 Écran final
# ================================================================================
def _end_screen(last):
    img = Image.blend(
        last,
        Image.new("RGB", (W, H), (3, 5, 12)),
        0.48,
    )

    draw = ImageDraw.Draw(img)

    try:
        font_big = ImageFont.truetype("DejaVuSans.ttf", 19)
        font_small = ImageFont.truetype("DejaVuSans.ttf", 9)
    except OSError:
        font_big = ImageFont.load_default()
        font_small = ImageFont.load_default()

    title = "3D PIPES"
    subtitle = "NETWORK COMPLETE"

    box = draw.textbbox((0, 0), title, font=font_big)
    x = (W - (box[2] - box[0])) // 2

    draw.text(
        (x + 1, 69 + 1),
        title,
        font=font_big,
        fill=(0, 0, 0),
    )

    draw.text(
        (x, 69),
        title,
        font=font_big,
        fill=(230, 235, 255),
    )

    box = draw.textbbox((0, 0), subtitle, font=font_small)
    x = (W - (box[2] - box[0])) // 2

    draw.text(
        (x, 105),
        subtitle,
        font=font_small,
        fill=(115, 190, 255),
    )

    # Barre décorative.
    draw.rounded_rectangle(
        [105, 124, 215, 127],
        radius=2,
        fill=(45, 100, 190),
    )

    return img


# ================================================================================
# 🎞️ Encodage du GIF
# ================================================================================
def _encode(frames, durations):
    """Palette commune et réduction automatique si le GIF dépasse la limite."""

    sample_indices = sorted({
        0,
        len(frames) // 5,
        len(frames) // 2,
        len(frames) * 4 // 5,
        len(frames) - 1,
    })

    sample = Image.new(
        "RGB",
        (W, H * len(sample_indices)),
    )

    for index, frame in enumerate(sample_indices):
        sample.paste(
            frames[frame],
            (0, index * H),
        )

    palette = sample.quantize(
        colors=PALETTE_COLORS,
        method=Image.Quantize.MEDIANCUT,
    )

    quantized = [
        frame.quantize(
            palette=palette,
            dither=Image.Dither.NONE,
        )
        for frame in frames
    ]

    step = 1

    while True:
        indices = list(range(0, len(quantized) - 1, step))
        indices.append(len(quantized) - 1)

        selected = [quantized[i] for i in indices]

        selected_durations = [
            durations[i] * (
                step if i != indices[-1] else 1
            )
            for i in indices
        ]

        buffer = io.BytesIO()

        selected[0].save(
            buffer,
            format="GIF",
            save_all=True,
            append_images=selected[1:],
            duration=selected_durations,
            optimize=True,
            disposal=2,
        )

        if buffer.tell() <= MAX_BYTES or len(selected) <= 12:
            break

        step += 1

    buffer.seek(0)
    return buffer


# ================================================================================
# 🎬 Génération complète du GIF
# ================================================================================
def generate_pipes_gif():
    rng = random.Random()

    segments, occupied = _generate_network(rng)

    if not segments:
        raise RuntimeError("Impossible de générer le réseau de tuyaux.")

    joints = _build_joints(segments)

    # --------------------------------------------------------------------------
    # Construction progressive des images
    # --------------------------------------------------------------------------
    frames = []
    durations = []

    total = len(segments)

    frame_count = min(MAX_FRAMES, max(24, total // 2))

    angle_offset = rng.uniform(0, math.pi * 2)

    for i in range(frame_count):

        # Progression de la construction.
        progress = (i + 1) / frame_count

        count = max(
            3,
            min(
                total,
                int(total * progress),
            ),
        )

        visible_segments = segments[:count]

        visible_points = set()

        for segment in visible_segments:
            visible_points.add(tuple(segment["a"]))
            visible_points.add(tuple(segment["b"]))

        visible_joints = [
            joint for joint in joints
            if tuple(
                round(v / PIPE_SPACING)
                for v in joint["position"]
            ) in visible_points
        ]

        # La caméra tourne lentement autour du réseau.
        angle = (
            angle_offset
            + i * CAMERA_SPEED
        )

        frame = _render_frame(
            visible_segments,
            visible_joints,
            angle,
            progress,
        )

        frames.append(frame)
        durations.append(FRAME_MS)

    # --------------------------------------------------------------------------
    # Dernière vue complète
    # --------------------------------------------------------------------------
    final_frame = _render_frame(
        segments,
        joints,
        angle_offset + frame_count * CAMERA_SPEED,
        1.0,
    )

    frames.append(final_frame)
    durations.append(1200)

    # --------------------------------------------------------------------------
    # Fondu vers l'écran final
    # --------------------------------------------------------------------------
    dark = Image.new("RGB", (W, H), (3, 5, 12))

    for i in range(1, 7):
        frames.append(
            Image.blend(
                final_frame,
                dark,
                i / 7,
            )
        )
        durations.append(75)

    frames.append(_end_screen(final_frame))
    durations.append(END_HOLD_MS)

    return _encode(frames, durations)


# ================================================================================
# 🧠 Cog principal
# ================================================================================
class ThreeDPipes(commands.Cog):
    """
    Commande /3dpipes et !3dpipes — Économiseur d'écran 3D Pipes
    avec tuyaux métalliques colorés et génération procédurale.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._lock = asyncio.Lock()

    def _embed(self):
        embed = discord.Embed(
            title="🔩 3D Pipes",
            description="Génération procédurale de tuyaux en 3D.",
            color=discord.Color.blurple(),
        )

        embed.set_image(url="attachment://3dpipes.gif")

        return embed

    async def _build(self):
        async with self._lock:
            buffer = await asyncio.to_thread(generate_pipes_gif)

        if buffer.getbuffer().nbytes > MAX_BYTES:
            return None, "❌ Le GIF est trop lourd pour Discord, réessaie."

        return discord.File(
            fp=buffer,
            filename="3dpipes.gif",
        ), None

    # ============================================================================
    # 🔹 Commande SLASH
    # ============================================================================
    @app_commands.command(
        name="3dpipes",
        description="Génère un économiseur d'écran animé avec des tuyaux 3D colorés."
    )
    @app_commands.checks.cooldown(
        rate=1,
        per=15.0,
        key=lambda i: i.user.id,
    )
    async def slash_3dpipes(self, interaction: discord.Interaction):

        if self._lock.locked():
            await interaction.response.send_message(
                "⏳ Une animation 3D Pipes est déjà en cours de génération, réessaie dans quelques secondes.",
                ephemeral=True,
            )
            return

        await interaction.response.defer()

        try:
            file, error = await self._build()

            if error:
                await interaction.followup.send(
                    error,
                    ephemeral=True,
                )
                return

            await safe_send(
                interaction.channel,
                embed=self._embed(),
                file=file,
            )

        except Exception:
            await interaction.followup.send(
                "❌ Une erreur est survenue pendant la génération des tuyaux 3D.",
                ephemeral=True,
            )
            raise

        finally:
            await interaction.delete_original_response()

    # ============================================================================
    # 🔹 Commande PREFIX
    # ============================================================================
    @commands.command(name="3dpipes")
    @commands.cooldown(
        1,
        15.0,
        commands.BucketType.user,
    )
    async def prefix_3dpipes(self, ctx: commands.Context):

        if self._lock.locked():
            await ctx.send(
                "⏳ Une animation 3D Pipes est déjà en cours de génération, réessaie dans quelques secondes."
            )
            return

        async with ctx.typing():
            try:
                file, error = await self._build()

                if error:
                    await ctx.send(error)
                    return

                await safe_send(
                    ctx.channel,
                    embed=self._embed(),
                    file=file,
                )

            except Exception:
                await ctx.send(
                    "❌ Une erreur est survenue pendant la génération des tuyaux 3D."
                )
                raise


# ================================================================================
# 🔌 Setup du Cog
# ================================================================================
async def setup(bot: commands.Bot):
    cog = ThreeDPipes(bot)

    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Fun&Random"

    await bot.add_cog(cog)
