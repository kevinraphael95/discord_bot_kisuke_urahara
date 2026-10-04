# ================================================================================
# 📌 cube_visuel.py — Commande interactive /cubevisuel et !cubevisuel
# Objectif : Résolveur de Rubik's Cube 3x3 VISUEL
#            - éditeur à boutons (peins les stickers, face par face)
#            - patron du cube rendu en image (Pillow)
#            - solution affichée étape par étape (⏮ ◀ ▶ ⏭) avec la face tournée surlignée
# Catégorie : Fun & Random
# Accès : Tous
# Cooldown : 1 utilisation / 10 secondes / utilisateur
# Dépendances : pip install kociemba pillow
# Usage prefix : !cubevisuel [54 caractères optionnels]
# ================================================================================

# ================================================================================
# 📦 Imports nécessaires
# ================================================================================
import asyncio
import io
import logging
import random
from collections import Counter

import discord
import kociemba
from discord import app_commands
from discord.ext import commands
from PIL import Image, ImageDraw

log = logging.getLogger(__name__)

CATEGORY = "Fun & Random"

# ================================================================================
# 🧊 Modèle du cube
# ================================================================================
# Ordre des faces (notation Kociemba) : U R F D L B, 9 stickers chacune, lecture ligne par ligne.
FACES = "URFDLB"
FACE_START = {f: i * 9 for i, f in enumerate(FACES)}

# Couleurs : schéma standard, blanc dessus, vert devant
COLORS = "WRGYOB"
STD_COLOR = {"U": "W", "R": "R", "F": "G", "D": "Y", "L": "O", "B": "B"}
COLOR_TO_FACE = {v: k for k, v in STD_COLOR.items()}
ALIASES = {"J": "Y", "V": "G"}  # Jaune, Vert (français)

COLOR_NAMES = {"W": "Blanc", "R": "Rouge", "G": "Vert", "Y": "Jaune", "O": "Orange", "B": "Bleu"}
COLOR_EMOJI = {"W": "⬜", "R": "🟥", "G": "🟩", "Y": "🟨", "O": "🟧", "B": "🟦"}
COLOR_RGB = {
    "W": (240, 240, 240),
    "R": (214, 40, 40),
    "G": (0, 155, 72),
    "Y": (255, 213, 0),
    "O": (255, 120, 0),
    "B": (0, 70, 173),
}

FACE_NAMES = {"U": "Haut", "R": "Droite", "F": "Face", "D": "Bas", "L": "Gauche", "B": "Arrière"}
NAV_ORDER = ["U", "L", "F", "R", "B", "D"]  # ordre du patron
NET_POS = {"U": (1, 0), "L": (0, 1), "F": (1, 1), "R": (2, 1), "B": (3, 1), "D": (1, 2)}

SOLVED = [STD_COLOR[f] for f in FACES for _ in range(9)]

# ── Géométrie 3D pour générer les rotations de faces ──
# x = droite, y = haut, z = devant
_NORMAL = {"U": (0, 1, 0), "R": (1, 0, 0), "F": (0, 0, 1), "D": (0, -1, 0), "L": (-1, 0, 0), "B": (0, 0, -1)}
_RIGHT  = {"U": (1, 0, 0), "R": (0, 0, -1), "F": (1, 0, 0), "D": (1, 0, 0), "L": (0, 0, 1), "B": (-1, 0, 0)}
_DOWN   = {"U": (0, 0, 1), "R": (0, -1, 0), "F": (0, -1, 0), "D": (0, 0, -1), "L": (0, -1, 0), "B": (0, -1, 0)}


def _add(*vecs):
    return tuple(sum(c) for c in zip(*vecs))


def _scale(v, k):
    return tuple(k * c for c in v)


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _rot_cw(v, n):
    """Rotation de -90° autour de n (= sens horaire vu depuis l'extérieur de la face)."""
    return _add(_scale(_cross(n, v), -1), _scale(n, _dot(n, v)))


def _build_moves() -> dict[str, list[int]]:
    """Pour chaque face : perm[i] = index source tel que new[i] = old[perm[i]]."""
    sticker_at: dict[tuple, int] = {}
    pos_of: dict[int, tuple] = {}
    for f in FACES:
        for r in range(3):
            for c in range(3):
                p = _add(_NORMAL[f], _scale(_RIGHT[f], c - 1), _scale(_DOWN[f], r - 1))
                idx = FACE_START[f] + r * 3 + c
                sticker_at[(p, _NORMAL[f])] = idx
                pos_of[idx] = (p, _NORMAL[f])

    perms: dict[str, list[int]] = {}
    for f in FACES:
        n = _NORMAL[f]
        perm = list(range(54))
        for idx, (p, q) in pos_of.items():
            if _dot(p, n) == 1:  # sticker de la couche tournée
                dest = sticker_at[(_rot_cw(p, n), _rot_cw(q, n))]
                perm[dest] = idx
        perms[f] = perm
    return perms


MOVE_PERMS = _build_moves()


def apply_move(state: list[str], token: str) -> list[str]:
    """Applique un mouvement ('R', "R'", 'R2') à un état de 54 stickers."""
    face = token[0]
    times = 2 if token.endswith("2") else 3 if token.endswith("'") else 1
    perm = MOVE_PERMS[face]
    for _ in range(times):
        state = [state[perm[i]] for i in range(54)]
    return state


def scramble_state(length: int = 25) -> list[str]:
    state = list(SOLVED)
    last = None
    for _ in range(length):
        face = random.choice([f for f in FACES if f != last])
        last = face
        state = apply_move(state, face + random.choice(["", "'", "2"]))
    return state


def to_facelets(state: list[str]) -> str:
    return "".join(COLOR_TO_FACE[c] for c in state)


def count_error(state: list[str]) -> str | None:
    counts = Counter(state)
    bad = [f"{COLOR_EMOJI[c]} {counts[c]}" for c in COLORS if counts[c] != 9]
    if bad:
        return "Il faut exactement 9 stickers de chaque couleur. Actuellement : " + ", ".join(bad) + "."
    return None


def parse_state(raw: str) -> tuple[list[str] | None, str | None]:
    """Accepte 54 caractères en couleurs (WRGYOB / J / V) ou en faces (URFDLB)."""
    s = raw.replace(" ", "").upper()
    if len(s) != 54:
        return None, f"54 caractères attendus (6 faces × 9), tu en as donné {len(s)}."

    if s[4] == "U":  # notation URFDLB
        if not set(s) <= set(FACES):
            return None, "Caractères invalides. Utilise `U R F D L B` ou les couleurs `W R G Y O B`."
        state = [STD_COLOR[c] for c in s]
    else:
        s = "".join(ALIASES.get(c, c) for c in s)
        if not set(s) <= set(COLORS):
            return None, "Caractères invalides. Utilise `U R F D L B` ou les couleurs `W R G Y O B`."
        state = list(s)

    for f in FACES:
        if state[FACE_START[f] + 4] != STD_COLOR[f]:
            return None, (
                f"Le centre de la face {FACE_NAMES[f]} doit être {COLOR_NAMES[STD_COLOR[f]].lower()} "
                "(blanc dessus, vert devant)."
            )
    return state, None


# ================================================================================
# 🎨 Rendu image du patron
# ================================================================================
def draw_net(state: list[str], highlight: str | None = None) -> io.BytesIO:
    S, P, FG, M = 40, 4, 14, 16          # sticker, espace entre stickers, espace entre faces, marge
    FS = 3 * S + 2 * P                   # taille d'une face
    width = 2 * M + 4 * FS + 3 * FG
    height = 2 * M + 3 * FS + 2 * FG

    img = Image.new("RGB", (width, height), (43, 45, 49))
    d = ImageDraw.Draw(img)

    for face, (gc, gr) in NET_POS.items():
        ox = M + gc * (FS + FG)
        oy = M + gr * (FS + FG)
        for k in range(9):
            r, c = divmod(k, 3)
            x = ox + c * (S + P)
            y = oy + r * (S + P)
            d.rounded_rectangle(
                [x, y, x + S, y + S], radius=7,
                fill=COLOR_RGB[state[FACE_START[face] + k]], outline=(15, 15, 15), width=2,
            )
        if highlight == face:
            d.rounded_rectangle([ox - 7, oy - 7, ox + FS + 7, oy + FS + 7], radius=12, outline=(0, 229, 255), width=3)

    buf = io.BytesIO()
    img.save(buf, "PNG")
    buf.seek(0)
    return buf


# ================================================================================
# 🔹 Modal de saisie rapide d'une face
# ================================================================================
class FaceModal(discord.ui.Modal):
    def __init__(self, cube_view: "CubeView", face: str):
        super().__init__(title=f"Saisie — face {FACE_NAMES[face]}")
        self.cube_view = cube_view
        self.face = face
        self.field = discord.ui.TextInput(
            label="9 stickers, ordre de lecture",
            placeholder="Ex : WWWWWWWWW  (W R G Y O B)",
            min_length=9,
            max_length=20,
            required=True,
        )
        self.add_item(self.field)

    async def on_submit(self, interaction: discord.Interaction):
        s = "".join(ALIASES.get(c, c) for c in self.field.value.replace(" ", "").upper())
        if len(s) != 9 or not set(s) <= set(COLORS):
            await interaction.response.send_message(
                "❌ Il faut 9 lettres parmi `W R G Y O B` (blanc, rouge, vert, jaune, orange, bleu).", ephemeral=True
            )
            return
        if s[4] != STD_COLOR[self.face]:
            await interaction.response.send_message(
                f"❌ Le centre (5e lettre) de cette face doit être **{STD_COLOR[self.face]}** "
                f"({COLOR_NAMES[STD_COLOR[self.face]].lower()}).",
                ephemeral=True,
            )
            return

        start = FACE_START[self.face]
        self.cube_view.stickers[start:start + 9] = list(s)
        await self.cube_view.refresh(interaction)


# ================================================================================
# 🎮 View principale : éditeur + visionneuse de solution
# ================================================================================
class CubeView(discord.ui.View):
    def __init__(self, author_id: int):
        super().__init__(timeout=600)
        self.author_id = author_id
        self.message = None                      # PartialMessage / Message à éditer
        self.mode = "edit"                       # "edit" | "solution"
        self.stickers: list[str] = list(SOLVED)
        self.face_pos = 0                        # index dans NAV_ORDER
        self.brush = "W"
        self.moves: list[str] = []
        self.states: list[list[str]] = []
        self.step = 0
        self.notice: str | None = None

    # ── Sécurité : seul l'auteur interagit ──
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ Ce n'est pas ta session. Lance `/cubevisuel` !", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except Exception:
                pass

    @property
    def face(self) -> str:
        return NAV_ORDER[self.face_pos]

    # ── Résolution ──
    async def solve(self) -> str | None:
        """Retourne un message d'erreur, ou None si la solution est prête (mode solution activé)."""
        err = count_error(self.stickers)
        if err:
            return err
        try:
            if self.stickers == SOLVED:
                solution = ""  # kociemba renvoie une séquence inutile sur un cube déjà résolu
            else:
                solution = await asyncio.to_thread(kociemba.solve, to_facelets(self.stickers))
        except Exception:
            return (
                "Configuration impossible à résoudre : un sticker est mal placé, un coin est tourné "
                "ou deux pièces sont échangées. Vérifie ta saisie."
            )

        self.moves = solution.split()
        self.states = [list(self.stickers)]
        for m in self.moves:
            self.states.append(apply_move(self.states[-1], m))
        if self.states[-1] != SOLVED:
            log.warning("[cubevisuel] La simulation ne retombe pas sur le cube résolu (%s)", solution)
        self.step = 0
        self.mode = "solution"
        return None

    # ── Construction des composants ──
    def build_items(self):
        self.clear_items()
        if self.mode == "edit":
            self._build_edit_items()
        else:
            self._build_solution_items()

    def _build_edit_items(self):
        face = self.face
        start = FACE_START[face]

        # Lignes 0-2 : les 9 stickers de la face active
        for k in range(9):
            idx = start + k
            btn = discord.ui.Button(
                emoji=COLOR_EMOJI[self.stickers[idx]],
                style=discord.ButtonStyle.secondary,
                row=k // 3,
                disabled=(k == 4),  # le centre est fixe
            )

            async def on_sticker(interaction: discord.Interaction, idx=idx):
                self.stickers[idx] = self.brush
                await self.refresh(interaction)

            btn.callback = on_sticker
            self.add_item(btn)

        # Ligne 3 : pinceau
        select = discord.ui.Select(
            placeholder="🎨 Couleur du pinceau",
            options=[
                discord.SelectOption(label=COLOR_NAMES[c], value=c, emoji=COLOR_EMOJI[c], default=(c == self.brush))
                for c in COLORS
            ],
            row=3,
        )

        async def on_brush(interaction: discord.Interaction):
            self.brush = select.values[0]
            await self.refresh(interaction)

        select.callback = on_brush
        self.add_item(select)

        # Ligne 4 : navigation + actions
        def make_button(label, style, callback):
            b = discord.ui.Button(label=label, style=style, row=4)
            b.callback = callback
            self.add_item(b)

        async def on_prev(interaction):
            self.face_pos = (self.face_pos - 1) % 6
            await self.refresh(interaction)

        async def on_next(interaction):
            self.face_pos = (self.face_pos + 1) % 6
            await self.refresh(interaction)

        async def on_type(interaction):
            await interaction.response.send_modal(FaceModal(self, self.face))

        async def on_scramble(interaction):
            self.stickers = scramble_state()
            self.notice = "🎲 Cube mélangé au hasard. Clique sur **Résoudre** !"
            await self.refresh(interaction)

        async def on_solve(interaction):
            await interaction.response.defer()
            err = await self.solve()
            if err:
                self.notice = err
            await self.refresh(interaction)

        make_button("◀", discord.ButtonStyle.secondary, on_prev)
        make_button("▶", discord.ButtonStyle.secondary, on_next)
        make_button("⌨️ Saisie", discord.ButtonStyle.secondary, on_type)
        make_button("🎲 Mélange", discord.ButtonStyle.secondary, on_scramble)
        make_button("🧩 Résoudre", discord.ButtonStyle.success, on_solve)

    def _build_solution_items(self):
        total = len(self.moves)

        def make_button(label, style, disabled, callback):
            b = discord.ui.Button(label=label, style=style, disabled=disabled, row=0)
            b.callback = callback
            self.add_item(b)

        async def go(interaction, step):
            self.step = max(0, min(total, step))
            await self.refresh(interaction)

        async def on_first(interaction):
            await go(interaction, 0)

        async def on_prev(interaction):
            await go(interaction, self.step - 1)

        async def on_next(interaction):
            await go(interaction, self.step + 1)

        async def on_last(interaction):
            await go(interaction, total)

        async def on_edit(interaction):
            self.mode = "edit"
            self.stickers = list(self.states[0])
            await self.refresh(interaction)

        make_button("⏮", discord.ButtonStyle.secondary, self.step == 0, on_first)
        make_button("◀", discord.ButtonStyle.primary, self.step == 0, on_prev)
        make_button("▶", discord.ButtonStyle.primary, self.step >= total, on_next)
        make_button("⏭", discord.ButtonStyle.secondary, self.step >= total, on_last)
        make_button("✏️ Éditer", discord.ButtonStyle.secondary, False, on_edit)

    # ── Embed + image ──
    def build_payload(self) -> tuple[discord.Embed, discord.File]:
        self.build_items()

        if self.mode == "edit":
            embed = self._edit_embed()
            buf = draw_net(self.stickers, highlight=self.face)
        else:
            embed, buf = self._solution_embed()

        embed.set_image(url="attachment://cube.png")
        if self.notice:
            embed.add_field(name="⚠️ Remarque", value=self.notice, inline=False)
            self.notice = None
        return embed, discord.File(buf, filename="cube.png")

    def _edit_embed(self) -> discord.Embed:
        face = self.face
        counts = Counter(self.stickers)
        counts_line = " · ".join(
            f"{COLOR_EMOJI[c]} {counts[c]}" + ("" if counts[c] == 9 else " ⚠️") for c in COLORS
        )
        embed = discord.Embed(
            title="🧊 Rubik's Cube visuel — Éditeur",
            description=(
                "1️⃣ Choisis une **couleur** dans le menu\n"
                "2️⃣ Clique sur les **stickers** de la face active (contour cyan sur l'image)\n"
                "3️⃣ **◀ ▶** change de face, **⌨️ Saisie** remplit une face d'un coup\n"
                "4️⃣ **🧩 Résoudre** quand ton cube est prêt\n\n"
                "Tiens ton cube avec le **blanc dessus** et le **vert devant**."
            ),
            color=discord.Color.blurple(),
        )
        embed.add_field(
            name="Face active",
            value=f"**{FACE_NAMES[face]}** (centre {COLOR_EMOJI[STD_COLOR[face]]}) — pinceau : {COLOR_EMOJI[self.brush]}",
            inline=False,
        )
        embed.add_field(name="Stickers par couleur", value=counts_line, inline=False)
        embed.set_footer(text="Les centres sont fixes. Saisie : W blanc · R rouge · G vert · Y jaune · O orange · B bleu")
        return embed

    def _solution_embed(self) -> tuple[discord.Embed, io.BytesIO]:
        total = len(self.moves)

        if total == 0:
            embed = discord.Embed(
                title="🧊 Rubik's Cube visuel — Déjà résolu !",
                description="🎉 Ce cube est déjà résolu, il n'y a rien à faire.",
                color=discord.Color.green(),
            )
            return embed, draw_net(self.states[0])

        tokens = []
        for i, m in enumerate(self.moves):
            if i < self.step - 1:
                tokens.append(f"~~{m}~~")
            elif i == self.step - 1:
                tokens.append(f"**[{m}]**")
            else:
                tokens.append(m)

        finished = self.step == total
        embed = discord.Embed(
            title=f"🧊 Rubik's Cube visuel — {total} mouvements",
            description=" ".join(tokens),
            color=discord.Color.green() if finished else discord.Color.blurple(),
        )
        if self.step == 0:
            embed.add_field(name="Départ", value="Cube blanc dessus, vert face à toi. Clique sur **▶** pour commencer.", inline=False)
        elif finished:
            embed.add_field(name="🎉 Terminé", value="Le cube est résolu !", inline=False)
        else:
            embed.add_field(name="Mouvement en cours", value=f"`{self.moves[self.step - 1]}`", inline=False)

        embed.add_field(
            name="📖 Notation",
            value=(
                "`R` = face **R**droite, `L` = **L**gauche, `U` = **U**p/haut, `D` = **D**own/bas, "
                "`F` = **F**ace, `B` = **B**ack/arrière\n"
                "`X` = quart de tour horaire · `X'` = anti-horaire · `X2` = demi-tour"
            ),
            inline=False,
        )
        embed.set_footer(text=f"Étape {self.step}/{total}")

        highlight = self.moves[self.step - 1][0] if self.step > 0 else None
        return embed, draw_net(self.states[self.step], highlight=highlight)

    # ── Mise à jour du message ──
    async def refresh(self, interaction: discord.Interaction):
        if not interaction.response.is_done():
            await interaction.response.defer()
        embed, file = self.build_payload()
        try:
            await self.message.edit(embed=embed, attachments=[file], view=self)
        except discord.HTTPException as e:
            log.exception("[cubevisuel] Édition du message impossible : %s", e)


# ================================================================================
# 🧠 Cog principal
# ================================================================================
class CubeVisuel(commands.Cog):
    """Commande /cubevisuel et !cubevisuel — Résolveur de Rubik's Cube visuel"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ============================================================================
    # 🔧 Logique commune
    # ============================================================================
    async def _launch(self, send, channel, author_id: int, raw_state: str | None):
        view = CubeView(author_id)

        # État fourni directement : on essaie de résoudre tout de suite
        if raw_state:
            stickers, err = parse_state(raw_state)
            if err:
                view.notice = err
            else:
                view.stickers = stickers
                err = await view.solve()
                if err:
                    view.notice = err

        embed, file = view.build_payload()
        msg = await send(embed=embed, file=file, view=view)

        # PartialMessage : l'édition passe par le token du bot (pas d'expiration à 15 min)
        if channel is not None and hasattr(channel, "get_partial_message"):
            view.message = channel.get_partial_message(msg.id)
        else:
            view.message = msg

    # ============================================================================
    # 🔹 Commande SLASH
    # ============================================================================
    @app_commands.command(
        name="cubevisuel",
        description="Résolveur de Rubik's Cube visuel : peins ton cube, puis suis la solution étape par étape.",
    )
    @app_commands.describe(state="(Optionnel) 54 caractères : couleurs WRGYOB ou faces URFDLB")
    @app_commands.checks.cooldown(1, 10.0, key=lambda i: i.user.id)
    async def slash_cubevisuel(self, interaction: discord.Interaction, state: str = None):
        await interaction.response.defer()

        async def send(**kwargs):
            return await interaction.followup.send(wait=True, **kwargs)

        await self._launch(send, interaction.channel, interaction.user.id, state)

    # ============================================================================
    # 🔹 Commande PREFIX
    # ============================================================================
    @commands.command(
        name="cubevisuel",
        aliases=["cubev"],
        help="Résolveur de Rubik's Cube visuel. Optionnel : 54 caractères (WRGYOB ou URFDLB).",
    )
    @commands.cooldown(1, 10.0, commands.BucketType.user)
    async def prefix_cubevisuel(self, ctx: commands.Context, *, state: str = None):
        async def send(**kwargs):
            return await ctx.send(**kwargs)

        await self._launch(send, ctx.channel, ctx.author.id, state)


# ================================================================================
# 🔌 Setup du Cog
# ================================================================================
async def setup(bot: commands.Bot):
    cog = CubeVisuel(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = CATEGORY
    await bot.add_cog(cog)
