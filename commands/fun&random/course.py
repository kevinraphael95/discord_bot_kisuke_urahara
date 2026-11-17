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
W, H = 320, 200
HALF = H // 2
FOV = math.radians(60)
CAM_HEIGHT = 1.0
MAP_SIZE = 512
SPEED = 0.002
FRAME_MS = 60
MAX_FRAMES = 150
MAX_BYTES = 8 * 1024 * 1024

# ================================================================================
# 🗺️ Génération de la texture de la piste (Vue de dessus)
# ================================================================================
def _create_track_texture():
    """Dessine un circuit ovale avec de l'herbe autour et une ligne de départ."""
    img = Image.new("RGB", (MAP_SIZE, MAP_SIZE), (76, 175, 80)) # Herbe
    d = ImageDraw.Draw(img)
    
    cx, cy = MAP_SIZE // 2, MAP_SIZE // 2
    r_out, r_in = 200, 140
    
    # Route (Anneau)
    d.ellipse([cx - r_out, cy - r_out, cx + r_out, cy + r_out], fill=(150, 140, 130))
    d.ellipse([cx - r_in, cy - r_in, cx + r_in, cy + r_in], fill=(76, 175, 80))
    
    # Ligne de départ (damier)
    start_y = cy + r_out
    for i in range(10):
        x0 = cx - 30 + (i * 6)
        color = (255, 255, 255) if i % 2 == 0 else (0, 0, 0)
        d.rectangle([x0, start_y - 20, x0 + 6, start_y], fill=color)
        
    # Arbres
    for _ in range(200):
        tx = random.randint(0, MAP_SIZE)
        ty = random.randint(0, MAP_SIZE)
        dist = math.hypot(tx - cx, ty - cy)
        if dist < r_in or dist > r_out:
            d.ellipse([tx-8, ty-8, tx+8, ty+8], fill=(46, 125, 50))
            
    return img

TRACK_IMG = _create_track_texture()
TRACK_DATA = TRACK_IMG.load()

# ================================================================================
# 🏎️ Rendu Mode 7 (Pillow)
# ================================================================================
def _render_mode7(camX, camY, camAngle):
    """Génère une image 3D de la piste vue depuis la caméra."""
    frame = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(frame)
    
    # 1. Ciel (Dégradé)
    for y in range(HALF):
        c = int(135 + (y / HALF) * 100)
        d.line([(0, y), (W, y)], fill=(c, 206, 235))
        
    # 2. Sol (Mode 7)
    dirX, dirY = math.cos(camAngle), math.sin(camAngle)
    planeX, planeY = -dirY * math.tan(FOV/2), dirX * math.tan(FOV/2)
    
    pixels = frame.load()
    
    for y in range(HALF, H):
        p = y - HALF
        rowDistance = (CAM_HEIGHT * H) / (p + 1e-5)
        
        rayDirX0, rayDirY0 = dirX - planeX, dirY - planeY
        rayDirX1, rayDirY1 = dirX + planeX, dirY + planeY
        
        floorStepX = rowDistance * (rayDirX1 - rayDirX0) / W
        floorStepY = rowDistance * (rayDirY1 - rayDirY0) / W
        
        floorX = camX + rowDistance * rayDirX0
        floorY = camY + rowDistance * rayDirY0
        
        fog = min(1.0, rowDistance / 300.0)
        fogColor = (135, 206, 235)
        
        for x in range(W):
            tx = int(floorX) % MAP_SIZE
            ty = int(floorY) % MAP_SIZE
            
            c = TRACK_DATA[tx, ty]
            
            if fog > 0:
                r = int(c[0] * (1 - fog) + fogColor[0] * fog)
                g = int(c[1] * (1 - fog) + fogColor[1] * fog)
                b = int(c[2] * (1 - fog) + fogColor[2] * fog)
                c = (r, g, b)
                
            pixels[x, y] = c
            
            floorX += floorStepX
            floorY += floorStepY
            
    # 3. La voiture (au centre, vue de dos)
    cx, cy = W // 2, H - 40
    d.rectangle([cx-15, cy-5, cx+15, cy+15], fill=(211, 47, 47))
    d.rectangle([cx-20, cy, cx-12, cy+15], fill=(34, 34, 34))
    d.rectangle([cx+12, cy, cx+20, cy+15], fill=(34, 34, 34))
    d.ellipse([cx-6, cy-12, cx+6, cy], fill=(255, 204, 128))
    d.ellipse([cx-7, cy-15, cx+7, cy-5], fill=(255, 255, 255))
    
    return frame

# ================================================================================
# 🏁 Génération du GIF
# ================================================================================
def _generate_race_gif(seed: int = None) -> io.BytesIO:
    rng = random.Random(seed)
    
    cx, cy = MAP_SIZE / 2, MAP_SIZE / 2
    radius = 170 
    
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
    
    for px, py, ang in picks:
        frame = _render_mode7(px, py, ang)
        frames.append(frame)
        
    # Encodage en GIF
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
