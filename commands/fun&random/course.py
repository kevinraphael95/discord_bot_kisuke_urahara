# ================================================================================
# 📌 course_kart.py
# Objectif : Course de karting (1 tour) style Super Mario Kart (Mode 7) en GIF.
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
import os
import random

# ================================================================================
# 📦  Modules tiers
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
# ⚙️ Constantes du jeu
# ================================================================================
W, H = 320, 240
HALF = 160
MINI_H = 80
FOV = math.radians(75)     # Champ de vision large pour le Mode 7
CAM_HEIGHT = 0.5           # Caméra basse
MAP_SIZE = 512
SPEED = 0.005
FRAME_MS = 60
MAX_FRAMES = 120
MAX_BYTES = 8 * 1024 * 1024

# ================================================================================
# 🗺️ Chargement et génération de la texture
# ================================================================================
def _load_track_texture():
    """Charge une vraie image de circuit (Mode 7). Fallback si absente."""
    path = os.path.join("assets", "track.png")
    try:
        img = Image.open(path).convert("RGB").resize((MAP_SIZE, MAP_SIZE))
    except FileNotFoundError:
        # Fallback (si l'image n'existe pas)
        img = Image.new("RGB", (MAP_SIZE, MAP_SIZE), (34, 139, 34))
        d = ImageDraw.Draw(img)
        d.ellipse([50, 50, 462, 462], fill=(218, 180, 130))
    return img

TRACK_IMG = _load_track_texture()
TRACK_DATA = TRACK_IMG.load()

# ================================================================================
# 🏎️ Rendu Mode 7 (Pillow)
# ================================================================================
def _render_frame(camX, camY, camAngle, time_ms):
    """Génère une image : 3D en haut, Minimap en bas, HUD."""
    frame = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(frame)
    
    # 1. Ciel
    d.rectangle([0, 0, W, 80], fill=(135, 206, 235))

    # 2. Route (Mode 7)
    dirX, dirY = math.cos(camAngle), math.sin(camAngle)
    planeX, planeY = -dirY * math.tan(FOV/2), dirX * math.tan(FOV/2)
    
    pixels = frame.load()
    
    for y in range(80, HALF):
        p = y - 80
        rowDistance = (CAM_HEIGHT * HALF) / (p + 1e-5)
        
        rayDirX0, rayDirY0 = dirX - planeX, dirY - planeY
        rayDirX1, rayDirY1 = dirX + planeX, dirY + planeY
        
        floorStepX = rowDistance * (rayDirX1 - rayDirX0) / W
        floorStepY = rowDistance * (rayDirY1 - rayDirY0) / W
        
        floorX = camX + rowDistance * rayDirX0
        floorY = camY + rowDistance * rayDirY0
        
        fog = min(1.0, rowDistance / 600.0)
        
        for x in range(W):
            tx = int(floorX) % MAP_SIZE
            ty = int(floorY) % MAP_SIZE
            
            c = TRACK_DATA[tx, ty]
            
            if fog > 0:
                r = int(c[0] * (1 - fog) + 135 * fog)
                g = int(c[1] * (1 - fog) + 206 * fog)
                b = int(c[2] * (1 - fog) + 235 * fog)
                c = (r, g, b)
                
            pixels[x, y] = c
            floorX += floorStepX
            floorY += floorStepY

    # 3. Kart (Sprite)
    kx, ky = W // 2, HALF - 15
    d.rectangle([kx-25, ky, kx-15, ky+20], fill=(34, 34, 34))
    d.rectangle([kx+15, ky, kx+25, ky+20], fill=(34, 34, 34))
    d.rectangle([kx-20, ky-10, kx+20, ky+15], fill=(211, 47, 47))
    d.rectangle([kx-25, ky-15, kx+25, ky-5], fill=(200, 0, 0))
    d.rectangle([kx-8, ky-20, kx+8, ky-8], fill=(255, 204, 128))
    d.rectangle([kx-10, ky-22, kx+10, ky-14], fill=(30, 136, 229))

    # 4. Mini-map
    d.rectangle([0, HALF, W, H], fill=(34, 139, 34))
    d.line([(0, HALF), (W, HALF)], fill=(255,255,255), width=2)
    
    mapScale = 0.12
    mapCX, mapCY = W // 2, HALF + (MINI_H // 2)
    d.ellipse([mapCX-60, mapCY-30, mapCX+60, mapCY+30], outline=(218, 180, 130), width=15)
    
    px = mapCX + int((camX - MAP_SIZE/2) * mapScale)
    py = mapCY + int((camY - MAP_SIZE/2) * mapScale)
    d.ellipse([px-3, py-3, px+3, py+3], fill=(255, 0, 0))

    # 5. HUD (Chrono)
    sec = int(time_ms / 1000)
    ms = int((time_ms % 1000) / 10)
    time_str = f"{sec:02d}\"{ms:02d}"
    
    d.rectangle([W - 80, 5, W - 5, 25], fill=(0, 0, 0), outline=(255, 255, 255))
    d.text((W - 10, 8), time_str, fill=(255, 255, 255), anchor="ra")

    return frame

# ================================================================================
# 🏁 Génération du GIF
# ================================================================================
def _generate_race_gif(seed: int = None) -> io.BytesIO:
    rng = random.Random(seed)
    cx, cy = MAP_SIZE / 2, MAP_SIZE / 2
    radius = 150 
    
    frames = []
    states = []
    start_angle = math.pi / 2
    total_steps = MAX_FRAMES * 2 
    
    for i in range(total_steps):
        t = i / total_steps
        angle_pos = start_angle + (t * math.pi * 2)
        px = cx + math.cos(angle_pos) * radius
        py = cy + math.sin(angle_pos) * radius
        cam_angle = angle_pos + math.pi / 2
        states.append((px, py, cam_angle))
        
    step = len(states) // MAX_FRAMES
    picks = states[::step][:MAX_FRAMES]
    
    for i, (px, py, ang) in enumerate(picks):
        time_ms = i * FRAME_MS
        frame = _render_frame(px, py, ang, time_ms)
        frames.append(frame)
        
    sample = Image.new("RGB", (W, H * 4))
    for k in range(4):
        sample.paste(frames[(len(frames) - 1) * k // 3], (0, H * k))
    
    pal = sample.quantize(colors=128, method=Image.MEDIANCUT)
    q = [f.quantize(palette=pal, dither=0) for f in frames]
    
    buf = io.BytesIO()
    q[0].save(buf, "GIF", save_all=True, append_images=q[1:], 
              duration=FRAME_MS, loop=0, optimize=True)
    buf.seek(0)
    return buf

# ================================================================================
# 🧠 Cog principal avec cooldowns centralisés
# ================================================================================
class CourseKart(commands.Cog):
    """
    Commande /course et !course — Course de karting (1 tour) en Mode 7.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._lock = asyncio.Lock()

    def _embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="🏎️ Course de Karting",
            description="Un tour de circuit en Mode 7 !",
            color=discord.Color.green()
        )
        embed.set_image(url="attachment://course.gif")
        return embed

    # ============================================================================
    # 🔹 Fonction interne commune
    # ============================================================================
    async def _build(self):
        async with self._lock:
            buffer = await asyncio.to_thread(_generate_race_gif, random.randint(0, 999999))
        if buffer.getbuffer().nbytes > MAX_BYTES:
            return None, "❌ Le GIF est trop lourd pour Discord."
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
