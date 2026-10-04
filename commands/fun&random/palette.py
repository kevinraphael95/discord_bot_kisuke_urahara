# ================================================================================
# 📌 palette.py — Nuancier d'artiste généré avec Pillow
# Objectif : Construire un VRAI nuancier structuré (grille / ramp), pas du random
# Catégorie : Fun&Random
# Accès : Public
# Cooldown : 1 utilisation / 5 sec / utilisateur
# ================================================================================

# ================================================================================
# 📦 Imports nécessaires
# ================================================================================
import io
import random
import json
import logging
import colorsys
import math
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont

from utils.discord_utils import safe_send, safe_edit, safe_interact
from utils.init_db import get_conn

log = logging.getLogger(__name__)

# ================================================================================
# 🎨 Modes de nuancier disponibles
# ================================================================================
MODES = {
    "peintre":    "Grille de familles de teintes (style nuancier Pantone)",
    "analogue":   "Grille de teintes voisines sur la roue chromatique",
    "complement": "Teinte + sa complémentaire, déclinées en luminosité",
    "triade":     "3 teintes en triangle, déclinées en luminosité",
    "ramp":       "Dégradé continu traversant le spectre",
    "terre":      "Palette de pigments naturels (ocres, terres, verts)",
    "pastel":     "Teintes douces et désaturées (style aquarelle)",
    "nuit":       "Palette sombre et saturée (style nocturne)",
}

# ================================================================================
# 🔤 Polices
# ================================================================================
FONT_DIR = Path("assets/fonts")

def _load_font(size: int, bold: bool = False):
    candidates = [
        FONT_DIR / ("Inter-Bold.ttf" if bold else "Inter-Regular.ttf"),
        FONT_DIR / ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else
             "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for path in candidates:
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size)
            except Exception:
                continue
    return ImageFont.load_default()

# ================================================================================
# 🧮 Utilitaires couleur
# ================================================================================
def _hsl_to_rgb(h: float, s: float, l: float) -> tuple[int, int, int]:
    r, g, b = colorsys.hls_to_rgb(h / 360.0, l, s)
    return int(r * 255), int(g * 255), int(b * 255)

def _hsl_to_hex(h: float, s: float, l: float) -> str:
    r, g, b = _hsl_to_rgb(h, s, l)
    return f"#{r:02X}{g:02X}{b:02X}"

def _luminance(rgb: tuple[int, int, int]) -> float:
    r, g, b = [c / 255 for c in rgb]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b

def _texte_sur(rgb: tuple[int, int, int]) -> tuple[int, int, int]:
    return (0, 0, 0) if _luminance(rgb) > 0.55 else (255, 255, 255)

def _clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, v))

# ================================================================================
# 🧱 Construction des nuanciers (STRUCTURÉS, pas random)
# ================================================================================
def build_nuancier(mode: str, n_cols: int = 8, n_rows: int = 5) -> dict:
    """
    Retourne un dict :
    {
      "mode": str,
      "titre": str,
      "grille": [[(hex, rgb, (h,s,l)), ...], ...],   # n_rows x n_cols
      "type": "grille" | "ramp"
    }
    Toutes les couleurs sont calculées par pas réguliers — AUCUN random sur H/S/L.
    """
    # --- On tire UNE graine de teinte (le reste est déterministe)
    h_seed = random.uniform(0, 360)

    grille = []

    if mode == "peintre":
        # Chaque ligne = une famille de teinte, on décline L de sombre à clair
        # Les lignes voisines sont des teintes proches (analogues ±15°)
        for r in range(n_rows):
            h = (h_seed + r * 15) % 360
            ligne = []
            for c in range(n_cols):
                # L varie de 15% (très sombre) à 90% (très clair)
                l = 0.15 + (c / (n_cols - 1)) * 0.75
                # S reste haute pour un nuancier "peinture"
                s = 0.85
                rgb = _hsl_to_rgb(h, s, l)
                ligne.append((_hsl_to_hex(h, s, l), rgb, (round(h), round(s*100), round(l*100))))
            grille.append(ligne)

    elif mode == "analogue":
        # Teintes analogues réparties sur ±60°, chaque ligne = une teinte
        for r in range(n_rows):
            h = (h_seed + (r - n_rows//2) * 20) % 360
            ligne = []
            for c in range(n_cols):
                l = 0.20 + (c / (n_cols - 1)) * 0.65
                s = 0.75
                rgb = _hsl_to_rgb(h, s, l)
                ligne.append((_hsl_to_hex(h, s, l), rgb, (round(h), round(s*100), round(l*100))))
            grille.append(ligne)

    elif mode == "complement":
        # Moitié des lignes = teinte de base, moitié = complémentaire
        for r in range(n_rows):
            h = h_seed if r < n_rows // 2 else (h_seed + 180) % 360
            ligne = []
            for c in range(n_cols):
                l = 0.20 + (c / (n_cols - 1)) * 0.65
                s = 0.80
                rgb = _hsl_to_rgb(h, s, l)
                ligne.append((_hsl_to_hex(h, s, l), rgb, (round(h), round(s*100), round(l*100))))
            grille.append(ligne)

    elif mode == "triade":
        # 3 teintes en triangle (0°, 120°, 240°) réparties sur les lignes
        for r in range(n_rows):
            h = (h_seed + (r % 3) * 120) % 360
            ligne = []
            for c in range(n_cols):
                l = 0.20 + (c / (n_cols - 1)) * 0.65
                s = 0.80
                rgb = _hsl_to_rgb(h, s, l)
                ligne.append((_hsl_to_hex(h, s, l), rgb, (round(h), round(s*100), round(l*100))))
            grille.append(ligne)

    elif mode == "ramp":
        # Une seule ligne, dégradé continu sur tout le spectre
        # On fait varier H sur 360°, S en cloche, L en cloche → dégradé naturel
        ligne = []
        for c in range(n_cols * n_rows):
            t = c / (n_cols * n_rows - 1)
            h = t * 360
            # S et L suivent une courbe douce
            s = 0.35 + 0.55 * math.sin(math.pi * t)
            l = 0.35 + 0.35 * math.sin(math.pi * t + 0.3)
            rgb = _hsl_to_rgb(h, s, l)
            ligne.append((_hsl_to_hex(h, s, l), rgb, (round(h), round(s*100), round(l*100))))
        grille = [ligne]

    elif mode == "terre":
        # Palette de pigments naturels : ocres, terres de Sienne, verts olive, bruns
        # On part d'une teinte de base dans les oranges/bruns (20-60°)
        h_base = 20 + random.uniform(0, 40)
        for r in range(n_rows):
            h = (h_base + r * 25) % 360
            ligne = []
            for c in range(n_cols):
                l = 0.18 + (c / (n_cols - 1)) * 0.60
                s = 0.45 + 0.25 * math.sin(math.pi * c / (n_cols - 1))
                rgb = _hsl_to_rgb(h, s, l)
                ligne.append((_hsl_to_hex(h, s, l), rgb, (round(h), round(s*100), round(l*100))))
            grille.append(ligne)

    elif mode == "pastel":
        # Teintes douces : saturation basse (20-45%), luminosité haute (65-90%)
        for r in range(n_rows):
            h = (h_seed + r * 30) % 360
            ligne = []
            for c in range(n_cols):
                l = 0.65 + (c / (n_cols - 1)) * 0.25
                s = 0.20 + (c / (n_cols - 1)) * 0.25
                rgb = _hsl_to_rgb(h, s, l)
                ligne.append((_hsl_to_hex(h, s, l), rgb, (round(h), round(s*100), round(l*100))))
            grille.append(ligne)

    elif mode == "nuit":
        # Palette sombre : L bas (10-45%), S élevée
        for r in range(n_rows):
            h = (h_seed + r * 40) % 360
            ligne = []
            for c in range(n_cols):
                l = 0.10 + (c / (n_cols - 1)) * 0.35
                s = 0.55 + (c / (n_cols - 1)) * 0.35
                rgb = _hsl_to_rgb(h, s, l)
                ligne.append((_hsl_to_hex(h, s, l), rgb, (round(h), round(s*100), round(l*100))))
            grille.append(ligne)

    else:
        # fallback
        grille = build_nuancier("peintre", n_cols, n_rows)["grille"]

    return {
        "mode": mode,
        "titre": MODES.get(mode, mode).split("(")[0].strip(),
        "grille": grille,
        "type": "ramp" if mode == "ramp" else "grille",
    }


# ================================================================================
# 🖼️ Rendu PNG du nuancier
# ================================================================================
def render_nuancier_png(nuancier: dict,
                        largeur: int = 1100,
                        hauteur_case: int = 90) -> io.BytesIO:
    """
    Dessine le nuancier. Pour une grille : chaque ligne = une famille de teinte.
    Pour une ramp : une seule ligne longue.
    Chaque case affiche son HEX (si assez large) et sa position.
    """
    grille = nuancier["grille"]
    n_rows = len(grille)
    n_cols = len(grille[0])

    marge = 40
    header_h = 100
    footer_h = 50
    gap = 4  # espace entre les cases

    largeur_case = (largeur - marge * 2 - gap * (n_cols - 1)) // n_cols
    hauteur = header_h + n_rows * hauteur_case + (n_rows - 1) * gap + footer_h + marge * 2

    img = Image.new("RGB", (largeur, hauteur), (18, 18, 22))
    draw = ImageDraw.Draw(img)

    font_title = _load_font(30, bold=True)
    font_sub   = _load_font(16)
    font_hex   = _load_font(13, bold=True)
    font_foot  = _load_font(13)

    # --- Header
    draw.text((marge, marge), "🎨 Nuancier", font=font_title, fill=(255, 255, 255))
    draw.text((marge, marge + 42), nuancier["titre"], font=font_sub, fill=(180, 180, 190))

    # --- Grille
    y = marge + header_h
    for row in grille:
        x = marge
        for (hex_str, rgb, hsl) in row:
            # Case colorée
            draw.rectangle([x, y, x + largeur_case, y + hauteur_case], fill=rgb)

            # Bordure légère
            draw.rectangle([x, y, x + largeur_case, y + hauteur_case],
                           outline=(0, 0, 0), width=1)

            # Texte : HEX si la case est assez large
            txt = _texte_sur(rgb)
            if largeur_case >= 80:
                bbox = draw.textbbox((0, 0), hex_str, font=font_hex)
                tw = bbox[2] - bbox[0]
                th = bbox[3] - bbox[1]
                draw.text(
                    (x + (largeur_case - tw) // 2, y + hauteur_case - th - 10),
                    hex_str, font=font_hex, fill=txt
                )

            x += largeur_case + gap
        y += hauteur_case + gap

    # --- Footer
    draw.text((marge, hauteur - marge - 18),
              "Nuancier structuré • Reiatsu Bot",
              font=font_foot, fill=(140, 140, 150))

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return buf


# ================================================================================
# 🗄️ Quête SQLite
# ================================================================================
def db_valider_quete(user_id: int) -> int | None:
    try:
        with get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT quetes, niveau FROM reiatsu WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if not row:
                return None
            quetes = json.loads(row[0] or "[]")
            niveau = row[1] or 1
            if "palette" in quetes:
                return None
            quetes.append("palette")
            new_lvl = niveau + 1
            cursor.execute(
                "UPDATE reiatsu SET quetes = ?, niveau = ? WHERE user_id = ?",
                (json.dumps(quetes), new_lvl, user_id)
            )
            conn.commit()
            return new_lvl
    except Exception as e:
        log.exception("[palette] Erreur validation quête SQLite : %s", e)
        return None


# ================================================================================
# 🎛️ Vue interactive
# ================================================================================
class PaletteView(discord.ui.View):
    def __init__(self, author: discord.User | discord.Member, mode: str | None = None):
        super().__init__(timeout=120)
        self.author = author
        self.mode = mode
        self.message: discord.Message | None = None

    def build_payload(self) -> tuple[discord.Embed, discord.File]:
        mode = self.mode or random.choice(list(MODES.keys()))
        self.mode = mode

        # Nombre de colonnes/lignes selon le mode
        if mode == "ramp":
            n_cols, n_rows = 10, 4   # 40 cases sur une ligne
        elif mode in ("terre", "pastel", "nuit"):
            n_cols, n_rows = 8, 4
        else:
            n_cols, n_rows = 8, 5

        nuancier = build_nuancier(mode, n_cols=n_cols, n_rows=n_rows)
        png = render_nuancier_png(nuancier)

        # Couleur d'accent = teinte du milieu
        mid_row = nuancier["grille"][len(nuancier["grille"]) // 2]
        accent_hex = mid_row[len(mid_row) // 2][0]
        accent = int(accent_hex[1:], 16)

        embed = discord.Embed(
            title=f"🎨 Nuancier — {nuancier['titre']}",
            description=(
                f"*{MODES.get(mode, '')}*\n\n"
                f"Structure : `{n_rows} lignes × {n_cols} colonnes`"
                + (" (dégradé continu)" if mode == "ramp" else "")
            ),
            color=accent,
        )
        embed.set_image(url="attachment://nuancier.png")
        embed.set_footer(text="🔁 régénérer • 🎲 autre mode")

        file = discord.File(png, filename="nuancier.png")
        return embed, file

    @discord.ui.button(label="🔁 Nouveau nuancier", style=discord.ButtonStyle.primary)
    async def regenerate(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            return await safe_interact(interaction, content="❌ Bouton réservé.", ephemeral=True)
        embed, file = self.build_payload()
        await safe_interact(interaction, edit=True, embed=embed, attachments=[file], view=self)

    @discord.ui.button(label="🎲 Autre mode", style=discord.ButtonStyle.secondary)
    async def change_mode(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            return await safe_interact(interaction, content="❌ Bouton réservé.", ephemeral=True)
        autres = [m for m in MODES if m != self.mode]
        self.mode = random.choice(autres)
        embed, file = self.build_payload()
        await safe_interact(interaction, edit=True, embed=embed, attachments=[file], view=self)

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message:
            await safe_edit(self.message, view=self)


# ================================================================================
# 🧠 Cog principal
# ================================================================================
class PaletteCommand(commands.Cog):
    """Commandes /palette et !palette — Nuancier d'artiste structuré."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _valider_quete(self, user, channel):
        new_lvl = db_valider_quete(user.id)
        if new_lvl is None:
            return
        embed = discord.Embed(
            title="🎉 Quête accomplie !",
            description=(
                f"Bravo **{user.display_name}** ! Quête **Palette** terminée 🎨\n\n"
                f"⭐ **Niveau +1 !** (Niveau {new_lvl})"
            ),
            color=0x00FF7F
        )
        await safe_send(channel, embed=embed)

    # ------------------------------------------------------------------ SLASH
    @app_commands.command(
        name="palette",
        description="Génère un nuancier d'artiste structuré (grille ou dégradé)."
    )
    @app_commands.describe(mode="Type de nuancier (aléatoire si vide)")
    @app_commands.choices(mode=[
        app_commands.Choice(name=label, value=key)
        for key, label in MODES.items()
    ])
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_palette(self, interaction: discord.Interaction, mode: str | None = None):
        view = PaletteView(interaction.user, mode=mode)
        embed, file = view.build_payload()
        await safe_interact(interaction, embed=embed, file=file, view=view)
        view.message = await interaction.original_response()
        await self._valider_quete(interaction.user, channel=interaction.channel)

    # ----------------------------------------------------------------- PREFIX
    @commands.command(
        name="palette",
        help="🎨 Nuancier d'artiste. Usage : !palette [peintre|analogue|complement|triade|ramp|terre|pastel|nuit]"
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def prefix_palette(self, ctx: commands.Context, mode: str | None = None):
        if mode and mode.lower() not in MODES:
            return await safe_send(
                ctx,
                content=f"❌ Mode inconnu. Choix : `{'`, `'.join(MODES)}`"
            )
        view = PaletteView(ctx.author, mode=mode.lower() if mode else None)
        embed, file = view.build_payload()
        view.message = await safe_send(ctx, embed=embed, file=file, view=view)
        await self._valider_quete(ctx.author, channel=ctx.channel)


# ================================================================================
# 🔌 Setup
# ================================================================================
async def setup(bot: commands.Bot):
    cog = PaletteCommand(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Fun&Random"
    await bot.add_cog(cog)
