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
from PIL import Image, ImageDraw, ImageFont

# ================================================================================
# 📦 Modules internes
# ================================================================================
from utils.discord_anti429 import safe_send, safe_edit, safe_respond, safe_delete

# ================================================================================
# ⚙️ Constantes du jeu
# ================================================================================
W, H = 320, 240            # Écran total (Haut 3D + Bas Minimap)
HALF = 160                 # Hauteur de la vue 3D
MINI_H = 80                # Hauteur de la minimap
FOV = math.radians(60)
CAM_HEIGHT = 1.0
MAP_SIZE = 512
SPEED = 0.005
FRAME_MS = 60
MAX_FRAMES = 150
MAX_BYTES = 8 * 1024 * 1024

# ================================================================================
# 🗺️ Génération de la texture de la piste (Vue de dessus)
# ================================================================================
def _create_track_texture():
    """Dessine un circuit ovale avec de l'herbe, des bordures et une ligne de départ."""
    img = Image.new("RGB", (MAP_SIZE, MAP_SIZE), (59, 122, 56)) # Herbe
    d = ImageDraw.Draw(img)
    
    cx, cy = MAP_SIZE // 2, MAP_SIZE // 2
    r_out, r_in = 200, 140
    
    # Route (Anneau)
    d.ellipse([cx - r_out, cy - r_out, cx + r_out, cy + r_out], fill=(194, 167, 125)) # Sable
    d.ellipse([cx - r_in, cy - r_in, cx + r_in, cy + r_in], fill=(59, 122, 56))
    
    # Bordures de piste (Rouge / Blanc)
    for a in range(0, 360, 10):
        rad = math.radians(a)
        # Bord extérieur
        ox = cx + math.cos(rad) * r_out
        oy = cy + math.sin(rad) * r_out
        color = (255, 0, 0) if (a // 10) % 2 == 0 else (255, 255, 255)
        d.rectangle([ox-5, oy-5, ox+5, oy+5], fill=color)
        
        # Bord intérieur
        ix = cx + math.cos(rad) * r_in
        iy = cy + math.sin(rad) * r_in
        d.rectangle([ix-5, iy-5, ix+5, iy+5], fill=color)
    
    # Ligne de départ (damier)
    start_y = cy + r_out
    for i in range(10):
        x0 = cx - 30 + (i * 6)
        color = (255, 255, 255) if i % 2 == 0 else (0, 0, 0)
        d.rectangle([x0, start_y - 20, x0 + 6, start_y], fill=color)
            
    return img

TRACK_IMG = _create_track_texture()
TRACK_DATA = TRACK_IMG.load()

# ================================================================================
# 🏎️ Rendu Mode 7 (Pillow)
# ================================================================================
def _render_frame(camX, camY, camAngle, time_ms, map_img):
    """Génère une image complète : 3D en haut, Minimap en bas, HUD."""
    frame = Image.new("RGB", (W, H))
    
    # --- 1. RENDU 3D (Mode 7) ---
    # Ciel
    d3d = ImageDraw.Draw(frame)
    for y in range(100):
        c = int(135 + (y / 100) * 100)
        d3d.line([(0, y), (W, y)], fill=(c, 206, 235))
        
    dirX, dirY = math.cos(camAngle), math.sin(camAngle)
    planeX, planeY = -dirY * math.tan(FOV/2), dirX * math.tan(FOV/2)
    
    pixels = frame.load()
    
    for y in range(100, HALF):
        p = y - 100
        rowDistance = (CAM_HEIGHT * H) / (p + 1e-5)
        
        rayDirX0, rayDirY0 = dirX - planeX, dirY - planeY
        rayDirX1, rayDirY1 = dirX + planeX, dirY + planeY
        
        floorStepX = rowDistance * (rayDirX1 - rayDirX0) / W
        floorStepY = rowDistance * (rayDirY1 - rayDirY0) / W
        
        floorX = camX + rowDistance * rayDirX0
        floorY = camY + rowDistance * rayDirY0
        
        fog = min(1.0, rowDistance / 400.0)
        
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

    # --- 2. LE KART (Sprite) ---
    kx, ky = W // 2, HALF - 10
    d = ImageDraw.Draw(frame)
    # Ombre
    d.ellipse([kx-20, ky+10, kx+20, ky+18], fill=(0,0,0))
    # Pneus
    d.rectangle([kx-25, ky, kx-15, ky+20], fill=(34, 34, 34))
    d.rectangle([kx+15, ky, kx+25, ky+20], fill=(34, 34, 34))
    # Châssis
    d.rectangle([kx-20, ky-10, kx+20, ky+15], fill=(211, 47, 47))
    # Pilote
    d.rectangle([kx-8, ky-20, kx+8, ky-8], fill=(255, 204, 128))
    d.rectangle([kx-10, ky-22, kx+10, ky-14], fill=(30, 136, 229))

    # --- 3. MINI-MAP (En bas) ---
    # Fond herbe
    d.rectangle([0, HALF, W, H], fill=(42, 122, 42))
    d.line([(0, HALF), (W, HALF)], fill=(255,255,255), width=2)
    
    # Dessin du circuit
    mapScale = 0.1
    mapCX, mapCY = W // 2, HALF + (MINI_H // 2)
    rx, ry = int(300 * mapScale), int(200 * mapScale)
    
    d.ellipse([mapCX-rx, mapCY-ry, mapCX+rx, mapCY+ry], outline=(194, 167, 125), width=int(140*mapScale))
    
    # Position du joueur
    px = mapCX + int((camX - MAP_SIZE/2) * mapScale)
    py = mapCY + int((camY - MAP_SIZE/2) * mapScale)
    d.ellipse([px-3, py-3, px+3, py+3], fill=(255,0,0))
    
    # Direction
    ex = px + int(math.cos(camAngle) * 8)
    ey = py + int(math.sin(camAngle) * 8)
    d.line([(px, py), (ex, ey)], fill=(255,0,0), width=2)

    # --- 4. HUD (Chrono & Position) ---
    sec = int(time_ms / 1000)
    ms = int((time_ms % 1000) / 10)
    time_str = f"00' {sec:02d}\" {ms:02d}"
    
    d.rectangle([W - 90, 5, W - 5, 30], fill=(0,0,0))
    d.text((W - 15, 10), time_str, fill=(255,255,255), anchor="ra")
    
    d.rectangle([W - 120, 5, W - 95, 30], fill=(255,0,0))
    d.text((W - 110, 10), "1er", fill=(255,255,255), anchor="ma")

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
    
    for i, (px, py, ang) in enumerate(picks):
        # Simulation du chrono (50ms par frame)
        time_ms = i * FRAME_MS
        frame = _render_frame(px, py, ang, time_ms, TRACK_IMG)
        frames.append(frame)
        
    # Encodage en GIF
    sample = Image.new("RGB", (W, H * 4))
    for k in range(4):
        sample.paste(frames[(len(frames) - 1) * k // 3], (0, H * k))
    
    # Palette optimisée
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
