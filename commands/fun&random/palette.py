# ================================================================================
# 📌 palette.py — Palette de 6 couleurs pour dessiner
# Objectif : Générer une palette (libre ou thématique), rendu nuancier 2x3
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
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont

from utils.discord_utils import safe_send, safe_edit, safe_interact
from utils.init_db import get_conn

log = logging.getLogger(__name__)

# ================================================================================
# 🎨 Thèmes de palettes (chacun = 6 couleurs de base)
# ================================================================================
THEMES = {
    "paysage": [
        (210, 0.55, 0.75),  # ciel
        (200, 0.40, 0.55),  # horizon
        (110, 0.45, 0.40),  # herbe
        (95,  0.40, 0.25),  # feuillage sombre
        (35,  0.35, 0.45),  # terre
        (25,  0.30, 0.65),  # roche
    ],
    "personnage": [
        (25,  0.45, 0.75),  # carnation claire
        (20,  0.55, 0.60),  # carnation
        (15,  0.50, 0.45),  # ombre peau
        (30,  0.35, 0.30),  # cheveux
        (220, 0.40, 0.40),  # vêtement bleu
        (350, 0.35, 0.55),  # accent
    ],
    "urbain": [
        (210, 0.05, 0.55),  # béton
        (200, 0.03, 0.35),  # asphalte
        (220, 0.10, 0.75),  # métal clair
        (0,   0.00, 0.20),  # métal sombre
        (320, 0.70, 0.55),  # néon rose
        (180, 0.70, 0.55),  # néon cyan
    ],
    "pastel": [
        (350, 0.35, 0.85),  # rose poudré
        (30,  0.40, 0.85),  # pêche
        (55,  0.35, 0.85),  # jaune pâle
        (140, 0.30, 0.82),  # menthe
        (200, 0.35, 0.82),  # bleu layette
        (280, 0.30, 0.82),  # lavande
    ],
    "automne": [
        (10,  0.55, 0.35),  # rouille
        (25,  0.65, 0.50),  # orange
        (42,  0.70, 0.55),  # doré
        (70,  0.40, 0.35),  # olive
        (18,  0.50, 0.45),  # sienne
        (15,  0.40, 0.20),  # brun foncé
    ],
    "hiver": [
        (210, 0.15, 0.92),  # blanc cassé
        (205, 0.20, 0.75),  # bleu pâle
        (215, 0.35, 0.55),  # bleu froid
        (230, 0.40, 0.35),  # bleu nuit
        (260, 0.25, 0.60),  # violet givré
        (200, 0.10, 0.45),  # gris glacier
    ],
    "nuit": [
        (240, 0.55, 0.10),  # bleu nuit profond
        (260, 0.50, 0.20),  # violet sombre
        (280, 0.45, 0.35),  # pourpre
        (200, 0.60, 0.30),  # bleu électrique
        (330, 0.55, 0.45),  # rose néon
        (60,  0.70, 0.60),  # lune
    ],
    "pixel_art": [
        (0,   0.90, 0.55),  # rouge vif
        (55,  0.95, 0.55),  # jaune vif
        (130, 0.75, 0.50),  # vert vif
        (210, 0.85, 0.55),  # bleu vif
        (290, 0.75, 0.55),  # violet vif
        (0,   0.00, 0.15),  # noir profond
    ],
    "ocean": [
        (200, 0.65, 0.75),  # écume
        (195, 0.55, 0.60),  # turquoise
        (205, 0.65, 0.45),  # bleu océan
        (215, 0.70, 0.30),  # bleu profond
        (185, 0.40, 0.70),  # sable mouillé
        (40,  0.30, 0.75),  # sable
    ],
    "feu": [
        (0,   0.85, 0.25),  # braise sombre
        (10,  0.85, 0.45),  # rouge feu
        (25,  0.90, 0.55),  # orange
        (42,  0.95, 0.60),  # jaune
        (55,  0.85, 0.75),  # jaune clair
        (0,   0.00, 0.15),  # fumée
    ],
}

# ================================================================================
# 🔤 Polices
# ================================================================================
RACINE_BOT = Path(__file__).resolve().parents[2]
FONT_DIR = RACINE_BOT / "assets" / "fonts"


def _load_font(size: int, bold: bool = False):
    nom = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    candidates = [
        FONT_DIR / nom,
        FONT_DIR / ("Inter-Bold.ttf" if bold else "Inter-Regular.ttf"),
        Path("/data/data/com.termux/files/usr/share/fonts/TTF") / nom,
        Path("/usr/share/fonts/truetype/dejavu") / nom,
        Path("/system/fonts") / nom,
    ]
    for path in candidates:
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size)
            except Exception as e:
                log.warning("[palette] Échec chargement %s : %s", path, e)
    log.warning("[palette] Aucune police TTF → fallback")
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


def _luminance(rgb):
    r, g, b = [c / 255 for c in rgb]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _texte_sur(rgb):
    return (0, 0, 0) if _luminance(rgb) > 0.55 else (255, 255, 255)


def _clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, v))


# ================================================================================
# 🎨 Générateurs de palettes
# ================================================================================
def palette_libre() -> list[dict]:
    """6 couleurs cohérentes générées par harmonie aléatoire."""
    harmonies = ["analogue", "triadique", "complementaire", "split", "tetradique", "mono"]
    harmonie = random.choice(harmonies)
    h_base = random.uniform(0, 360)
    s_base = random.uniform(0.55, 0.85)
    l_base = random.uniform(0.45, 0.65)

    couleurs = []
    for i in range(6):
        if harmonie == "mono":
            h = h_base
            l = 0.20 + (i / 5) * 0.65
            s = s_base
        else:
            offsets = {
                "analogue":       [-50, -25, 0, 25, 50, 75],
                "triadique":      [0, 120, 240, 60, 180, 300],
                "complementaire": [0, 180, 30, 210, 90, 270],
                "split":          [0, 150, 210, 30, 180, 330],
                "tetradique":     [0, 90, 180, 270, 45, 135],
            }[harmonie]
            h = (h_base + offsets[i]) % 360
            l = _clamp(l_base + random.uniform(-0.18, 0.18), 0.20, 0.88)
            s = _clamp(s_base + random.uniform(-0.15, 0.15), 0.40, 1.0)

        rgb = _hsl_to_rgb(h, s, l)
        couleurs.append({
            "hex": _hsl_to_hex(h, s, l),
            "rgb": rgb,
            "hsl": (round(h), round(s * 100), round(l * 100)),
        })
    return couleurs, harmonie


def palette_theme(nom_theme: str) -> list[dict]:
    """6 couleurs d'un thème, avec de légères variations autour de chaque base."""
    base = THEMES[nom_theme]
    couleurs = []
    for (h, s, l) in base:
        # Petite variation pour éviter d'avoir exactement les mêmes à chaque fois
        h2 = (h + random.uniform(-6, 6)) % 360
        s2 = _clamp(s + random.uniform(-0.06, 0.06), 0.15, 1.0)
        l2 = _clamp(l + random.uniform(-0.06, 0.06), 0.10, 0.92)
        rgb = _hsl_to_rgb(h2, s2, l2)
        couleurs.append({
            "hex": _hsl_to_hex(h2, s2, l2),
            "rgb": rgb,
            "hsl": (round(h2), round(s2 * 100), round(l2 * 100)),
        })
    return couleurs


def generer_palette() -> tuple[list[dict], str, str | None]:
    """
    Retourne (couleurs, mode, nom_theme).
    mode = 'libre' ou 'thematique'. nom_theme = clé du thème ou None.
    """
    mode = random.choice(["libre", "thematique"])
    if mode == "libre":
        couleurs, _ = palette_libre()
        return couleurs, "libre", None
    else:
        nom_theme = random.choice(list(THEMES.keys()))
        couleurs = palette_theme(nom_theme)
        return couleurs, "thematique", nom_theme


# ================================================================================
# 🖼️ Rendu PNG — grille 2x3
# ================================================================================
def render_palette_png(couleurs: list[dict],
                       largeur: int = 1200,
                       hauteur: int = 800) -> io.BytesIO:
    """
    Grille 2 lignes x 3 colonnes. Chaque case : couleur de fond + HEX centré.
    """
    n_cols = 3
    n_rows = 2

    marge = 30
    gap = 8
    largeur_case = (largeur - marge * 2 - gap * (n_cols - 1)) // n_cols
    hauteur_case = (hauteur - marge * 2 - gap * (n_rows - 1)) // n_rows

    img = Image.new("RGB", (largeur, hauteur), (20, 20, 24))
    draw = ImageDraw.Draw(img)

    font_hex = _load_font(38, bold=True)

    for i, c in enumerate(couleurs):
        row = i // n_cols
        col = i % n_cols
        x0 = marge + col * (largeur_case + gap)
        y0 = marge + row * (hauteur_case + gap)
        x1 = x0 + largeur_case
        y1 = y0 + hauteur_case

        # Case colorée
        draw.rectangle([x0, y0, x1, y1], fill=c["rgb"])

        # Code HEX centré
        txt = c["hex"]
        txt_color = _texte_sur(c["rgb"])
        bbox = draw.textbbox((0, 0), txt, font=font_hex)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text(
            (x0 + (largeur_case - tw) // 2, y0 + (hauteur_case - th) // 2),
            txt, font=font_hex, fill=txt_color
        )

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
    def __init__(self, author: discord.User | discord.Member):
        super().__init__(timeout=120)
        self.author = author
        self.message: discord.Message | None = None

    def build_payload(self) -> tuple[discord.Embed, discord.File]:
        couleurs, mode, theme = generer_palette()
        png = render_palette_png(couleurs)

        # Couleur d'accent = 4e couleur
        accent = int(couleurs[3]["hex"][1:], 16)

        if mode == "libre":
            titre = "🎨 Palette libre"
            desc = "6 couleurs harmonieuses pour dessiner"
        else:
            titre = f"🎨 Palette — {theme.replace('_', ' ').capitalize()}"
            desc = f"6 couleurs du thème **{theme.replace('_', ' ')}**"

        codes = " • ".join(f"`{c['hex']}`" for c in couleurs)

        embed = discord.Embed(
            title=titre,
            description=f"{desc}\n\n{codes}",
            color=accent,
        )
        embed.set_image(url="attachment://palette.png")

        file = discord.File(png, filename="palette.png")
        return embed, file

    @discord.ui.button(label="🔁 Nouvelle palette", style=discord.ButtonStyle.primary)
    async def regenerate(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            return await safe_interact(interaction, content="❌ Bouton réservé.", ephemeral=True)
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
    """Commandes /palette et !palette — Palette de 6 couleurs pour dessiner."""

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

    @app_commands.command(
        name="palette",
        description="Génère une palette de 6 couleurs pour dessiner."
    )
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_palette(self, interaction: discord.Interaction):
        view = PaletteView(interaction.user)
        embed, file = view.build_payload()
        await safe_interact(interaction, embed=embed, file=file, view=view)
        view.message = await interaction.original_response()
        await self._valider_quete(interaction.user, channel=interaction.channel)

    @commands.command(
        name="palette",
        help="🎨 Génère une palette de 6 couleurs pour dessiner."
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def prefix_palette(self, ctx: commands.Context):
        view = PaletteView(ctx.author)
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
