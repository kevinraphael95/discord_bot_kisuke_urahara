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
from PIL import Image, ImageDraw, ImageFilter

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
    """Dessine un circuit ovale avec une texture de sable et des vibreurs."""
    img = Image.new("RGB", (MAP_SIZE, MAP_SIZE), (34, 139, 34)) # Vert herbe foncé
    d = ImageDraw.Draw(img)
    
    cx, cy = MAP_SIZE // 2, MAP_SIZE // 2
    r_out, r_in = 200, 140
    
    # 1. Dessin de la route (Sable)
    d.ellipse([cx - r_out, cy - r_out, cx + r_out, cy + r_out], fill=(218, 180, 130))
    d.ellipse([cx - r_in, cy - r_in, cx + r_in, cy + r_in], fill=(34, 139, 34))
    
    # 2. Ajout d'une texture "pixel art" sur le sable et l'herbe
    # On utilise un bruit pour casser l'effet lisse
    noise = Image.effect_noise((MAP_SIZE, MAP_SIZE), 50).convert("L")
    # On applique le bruit uniquement sur l'herbe et le sable
    for y in range(MAP_SIZE):
        for x in range(MAP_SIZE):
            dist = math.hypot(x - cx, y - cy)
            if dist < r_out and dist > r_in:
                # Route (Sable)
                n = noise.getpixel((x, y))
                v = int(n / 255 * 20 - 10)
                c = (218 + v, 180 + v, 130 + v)
                d.point((x, y), fill=c)
            elif dist >= r_out:
                # Herbe
                if random.random() < 0.1: # Petits points pour l'herbe
                    d.point((x, y), fill=(50, 160, 50))
            elif dist <= r_in:
                # Herbe intérieure
                if random.random() < 0.1:
                    d.point((x, y), fill=(50, 160, 50))

    # 3. Vibreurs (Rouge / Blanc)
    for a in range(0, 360, 8):
        rad = math.radians(a)
        color = (255, 0, 0) if (a // 8) % 2 == 0 else (255, 255, 255)
        
        # Extérieur
        ox = cx + math.cos(rad) * r_out
        oy = cy + math.sin(rad) * r_out
        d.rectangle([ox-6, oy-6, ox+6, oy+6], fill=color)
        
        # Intérieur
        ix = cx + math.cos(rad) * r_in
        iy = cy + math.sin(rad) * r_in
        d.rectangle([ix-6, iy-6, ix+6, iy+6], fill=color)
    
    # 4. Ligne de départ
    start_y = cy + r_out
    for i in range(12):
        x0 = cx - 36 + (i * 6)
        color = (255, 255, 255) if i % 2 == 0 else (0, 0, 0)
        d.rectangle([x0, start_y - 15, x0 + 6, start_y], fill=color)
            
    return img

TRACK_IMG = _create_track_texture()
TRACK_DATA = TRACK_IMG.load()

# ================================================================================
# 🏎️ Rendu Mode 7 (Pillow) - Optimisé
# ================================================================================
def _render_frame(camX, camY, camAngle, time_ms):
    """Génère une image complète : 3D en haut, Minimap en bas, HUD."""
    frame = Image.new("RGB", (W, H))
    
    # --- 1. CIEL ---
    d = ImageDraw.Draw(frame)
    for y in range(80):
        c = int(135 + (y / 80) * 100)
        d.line([(0, y), (W, y)], fill=(c, 206, 235))
    # Ligne d'horizon floue
    d.rectangle([0, 80, W, 90], fill=(135, 206, 235))

    # --- 2. ROUTE (Mode 7) ---
    dirX, dirY = math.cos(camAngle), math.sin(camAngle)
    planeX, planeY = -dirY * math.tan(FOV/2), dirX * math.tan(FOV/2)
    
    pixels = frame.load()
    
    for y in range(90, HALF):
        p = y - 90
        rowDistance = (CAM_HEIGHT * 200) / (p + 1e-5)
        
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

    # --- 3. LE KART (Sprite détaillé) ---
    kx, ky = W // 2, HALF - 15
    d = ImageDraw.Draw(frame)
    
    # Ombre
    d.ellipse([kx-18, ky+12, kx+18, ky+20], fill=(0,0,0))
    
    # Pneus
    d.rectangle([kx-22, ky, kx-12, ky+16], fill=(30, 30, 30))
    d.rectangle([kx+12, ky, kx+22, ky+16], fill=(30, 30, 30))
    
    # Aileron arrière
    d.rectangle([kx-26, ky-8, kx+26, ky-2], fill=(200, 0, 0))
    
    # Châssis (Rouge)
    d.polygon([(kx-15, ky-5), (kx+15, ky-5), (kx+12, ky+15), (kx-12, ky+15)], fill=(211, 47, 47))
    
    # Détails du châssis (Blanc)
    d.rectangle([kx-8, ky-2, kx+8, ky+8], fill=(255, 255, 255))
    
    # Pilote (Tête + Casque)
    d.rectangle([kx-6, ky-16, kx+6, ky-6], fill=(255, 204, 128)) # Visage
    d.rectangle([kx-8, ky-20, kx+8, ky-14], fill=(30, 136, 229)) # Casque Bleu

    # --- 4. MINI-MAP (En bas) ---
    d.rectangle([0, HALF, W, H], fill=(34, 139, 34))
    d.line([(0, HALF), (W, HALF)], fill=(255,255,255), width=2)
    
    mapScale = 0.1
    mapCX, mapCY = W // 2, HALF + (MINI_H // 2)
    rx, ry = int(300 * mapScale), int(200 * mapScale)
    
    # Route sur la minimap
    d.ellipse([mapCX-rx, mapCY-ry, mapCX+rx, mapCY+ry], outline=(218, 180, 130), width=int(140*mapScale))
    
    # Joueur
    px = mapCX + int((camX - MAP_SIZE/2) * mapScale)
    py = mapCY + int((camY - MAP_SIZE/2) * mapScale)
    d.ellipse([px-3, py-3, px+3, py+3], fill=(255, 0, 0))
    
    # Direction
    ex = px + int(math.cos(camAngle) * 8)
    ey = py + int(math.sin(camAngle) * 8)
    d.line([(px, py), (ex, ey)], fill=(255, 0, 0), width=2)

    # --- 5. HUD ---
    sec = int(time_ms / 1000)
    ms = int((time_ms % 1000) / 10)
    time_str = f"{sec:02d}\"{ms:02d}"
    
    # Boite Chrono
    d.rectangle([W - 80, 5, W - 5, 25], fill=(0, 0, 0), outline=(255, 255, 255))
    d.text((W - 10, 8), time_str, fill=(255, 255, 255), anchor="ra")
    
    # Boite Position
    d.rectangle([W - 110, 5, W - 85, 25], fill=(0, 0, 0), outline=(255, 255, 255))
    d.text((W - 97, 8), "1", fill=(255, 0, 0), anchor="ma")

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
        time_ms = i * FRAME_MS
        frame = _render_frame(px, py, ang, time_ms)
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
