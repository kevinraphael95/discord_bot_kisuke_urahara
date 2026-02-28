# ────────────────────────────────────────────────────────────────────────────────
# 📌 jardin2.py — Jardin interactif (SQLite)
# Objectif : Jardin avec grille de boutons interactive, stockage SQLite local
# Catégorie : Jeux
# Accès : Public
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands
import datetime
import random
import json

from utils.init_db import get_conn

# ────────────────────────────────────────────────────────────────────────────────
# ⚙️ Config
# ────────────────────────────────────────────────────────────────────────────────
GRID_ROWS = 4
GRID_COLS = 4

EMPTY_CELL = "🌱"

# Fleurs disponibles : emoji → valeur en argent
FLEUR_EMOJIS = {
    "🌸": 5,
    "🌼": 4,
    "🌻": 6,
    "🌹": 8,
    "🌺": 7,
    "💐": 10,
    "🪷": 9,
}

FERTILIZE_PROBABILITY = 0.4       # chance de pousser par case vide
FERTILIZE_COOLDOWN_MINUTES = 5    # cooldown engrais en minutes
TABLE_NAME = "gardens"


# ────────────────────────────────────────────────────────────────────────────────
# 🛠️ Fonctions DB
# ────────────────────────────────────────────────────────────────────────────────
def db_get_garden(user_id: int):
    conn = get_conn()
    conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
    cur = conn.cursor()
    cur.execute("SELECT * FROM gardens WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row


def db_create_garden(user_id: int, username: str) -> dict:
    default_grid = [[EMPTY_CELL] * GRID_COLS for _ in range(GRID_ROWS)]
    default_inv = {e: 0 for e in FLEUR_EMOJIS}

    conn = get_conn()
    conn.execute("""
        INSERT OR IGNORE INTO gardens (user_id, username, garden_grid, inventory, argent, last_fertilize)
        VALUES (?, ?, ?, ?, 0, NULL)
    """, (user_id, username, json.dumps(default_grid), json.dumps(default_inv)))
    conn.commit()
    conn.close()

    return db_get_garden(user_id)


def db_update_garden(user_id: int, **fields):
    if not fields:
        return
    # Sérialise les listes/dicts
    for k, v in fields.items():
        if isinstance(v, (list, dict)):
            fields[k] = json.dumps(v)

    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [user_id]

    conn = get_conn()
    conn.execute(f"UPDATE gardens SET {set_clause} WHERE user_id = ?", values)
    conn.commit()
    conn.close()


def get_or_create_garden(user_id: int, username: str) -> dict:
    row = db_get_garden(user_id)
    if not row:
        row = db_create_garden(user_id, username)

    # Désérialise les champs JSON
    row["garden_grid"] = json.loads(row["garden_grid"])
    row["inventory"]   = json.loads(row["inventory"])
    return row


# ────────────────────────────────────────────────────────────────────────────────
# 🌿 Logique de jeu
# ────────────────────────────────────────────────────────────────────────────────
def pousser_fleurs(grid: list[list[str]]) -> tuple[list[list[str]], int]:
    """Fait pousser des fleurs aléatoirement sur les cases vides. Retourne (nouvelle grille, nb poussé)."""
    count = 0
    new_grid = []
    fleurs = list(FLEUR_EMOJIS.keys())
    for row in grid:
        new_row = []
        for cell in row:
            if cell == EMPTY_CELL and random.random() < FERTILIZE_PROBABILITY:
                new_row.append(random.choice(fleurs))
                count += 1
            else:
                new_row.append(cell)
        new_grid.append(new_row)
    return new_grid, count


def count_flowers(grid: list[list[str]]) -> int:
    return sum(1 for row in grid for cell in row if cell != EMPTY_CELL)


def count_empty(grid: list[list[str]]) -> int:
    return sum(1 for row in grid for cell in row if cell == EMPTY_CELL)


def harvest_all(garden: dict) -> tuple[dict, int]:
    """Coupe toutes les fleurs d'un coup et les met en inventaire."""
    grid = garden["garden_grid"]
    inv  = garden["inventory"]
    cut  = 0
    new_grid = []
    for row in grid:
        new_row = []
        for cell in row:
            if cell != EMPTY_CELL:
                inv[cell] = inv.get(cell, 0) + 1
                new_row.append(EMPTY_CELL)
                cut += 1
            else:
                new_row.append(cell)
        new_grid.append(new_row)
    garden["garden_grid"] = new_grid
    garden["inventory"]   = inv
    return garden, cut


def sell_inventory(garden: dict) -> tuple[dict, int]:
    """Vend tout l'inventaire. Retourne (garden mis à jour, argent gagné)."""
    inv = garden["inventory"]
    gained = 0
    for emoji, qty in inv.items():
        gained += qty * FLEUR_EMOJIS.get(emoji, 1)
    garden["inventory"] = {e: 0 for e in FLEUR_EMOJIS}
    garden["argent"] = garden.get("argent", 0) + gained
    return garden, gained


# ────────────────────────────────────────────────────────────────────────────────
# 📐 Formatage du message
# ────────────────────────────────────────────────────────────────────────────────
def format_garden_header(garden: dict) -> str:
    grid = garden["garden_grid"]
    flowers = count_flowers(grid)
    empty   = count_empty(grid)
    argent  = garden.get("argent", 0)
    return (
        f"🏡 **Jardin de {garden['username']}**\n"
        f"🌸 Fleurs : **{flowers}** | 🌱 Vides : **{empty}** | 💵 Argent : **{argent}**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )


# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ Vue principale du jardin
# ────────────────────────────────────────────────────────────────────────────────
class JardinView(discord.ui.View):
    def __init__(self, garden: dict, user_id: int):
        super().__init__(timeout=300)
        self.garden  = garden
        self.user_id = user_id
        self._build_buttons()

    def _build_buttons(self):
        """(Re)construit tous les boutons selon l'état actuel de la grille."""
        self.clear_items()
        grid = self.garden["garden_grid"]

        # ── Grille (rows 0–3)
        for r, row in enumerate(grid):
            for c, cell in enumerate(row):
                btn = CellButton(r, c, cell)
                self.add_item(btn)

        # ── Actions globales (row 4)
        self.add_item(ActionButton("💩", "engrais",    discord.ButtonStyle.primary,   row=4))
        self.add_item(ActionButton("✂️",  "couper_tout", discord.ButtonStyle.secondary, row=4))
        self.add_item(ActionButton("🛍️", "inventaire", discord.ButtonStyle.secondary, row=4))
        self.add_item(ActionButton("💵", "vendre",     discord.ButtonStyle.success,   row=4))
        self.add_item(ActionButton("❓", "aide",       discord.ButtonStyle.secondary, row=4))

    async def refresh(self, interaction: discord.Interaction, notice: str = ""):
        """Reconstruit la vue et édite le message."""
        self._build_buttons()
        header = format_garden_header(self.garden)
        content = f"{header}\n{notice}" if notice else header
        await interaction.response.edit_message(content=content, view=self)

    async def guard(self, interaction: discord.Interaction) -> bool:
        """Vérifie que c'est bien le propriétaire. Retourne False si bloqué."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Ce jardin n'est pas à toi !", ephemeral=True)
            return False
        return True


# ────────────────────────────────────────────────────────────────────────────────
# 🔘 Bouton d'une case de la grille
# ────────────────────────────────────────────────────────────────────────────────
class CellButton(discord.ui.Button):
    def __init__(self, row: int, col: int, cell: str):
        # Style visuel : vert si vide, gris si fleur
        style = discord.ButtonStyle.success if cell == EMPTY_CELL else discord.ButtonStyle.secondary
        super().__init__(label=cell, style=style, row=row)
        self.r = row
        self.c = col

    async def callback(self, interaction: discord.Interaction):
        view: JardinView = self.view
        if not await view.guard(interaction):
            return

        grid = view.garden["garden_grid"]
        cell = grid[self.r][self.c]

        if cell == EMPTY_CELL:
            # Case vide → rien à faire
            await interaction.response.send_message(
                "🌱 Cette case est vide, utilise 💩 pour faire pousser des fleurs !",
                ephemeral=True
            )
            return

        # Récolte de la fleur
        inv = view.garden["inventory"]
        inv[cell] = inv.get(cell, 0) + 1
        grid[self.r][self.c] = EMPTY_CELL
        view.garden["inventory"]   = inv
        view.garden["garden_grid"] = grid

        db_update_garden(view.user_id, garden_grid=grid, inventory=inv)
        await view.refresh(interaction, f"✂️ Tu as coupé **{cell}** et l'as mis en inventaire !")


# ────────────────────────────────────────────────────────────────────────────────
# 🔘 Boutons d'action globaux
# ────────────────────────────────────────────────────────────────────────────────
class ActionButton(discord.ui.Button):
    def __init__(self, label: str, action: str, style: discord.ButtonStyle, row: int):
        super().__init__(label=label, style=style, row=row)
        self.action = action

    async def callback(self, interaction: discord.Interaction):
        view: JardinView = self.view
        if not await view.guard(interaction):
            return

        # ── 💩 Engrais
        if self.action == "engrais":
            now  = datetime.datetime.now(datetime.timezone.utc)
            last = view.garden.get("last_fertilize")

            if last:
                last_dt = datetime.datetime.fromisoformat(last)
                if last_dt.tzinfo is None:
                    last_dt = last_dt.replace(tzinfo=datetime.timezone.utc)
                delta = now - last_dt
                cooldown = datetime.timedelta(minutes=FERTILIZE_COOLDOWN_MINUTES)
                if delta < cooldown:
                    remaining = int((cooldown - delta).total_seconds())
                    mins, secs = divmod(remaining, 60)
                    await interaction.response.send_message(
                        f"⏳ Engrais en cooldown ! Encore **{mins}m {secs}s** à attendre.",
                        ephemeral=True
                    )
                    return

            new_grid, pushed = pousser_fleurs(view.garden["garden_grid"])
            view.garden["garden_grid"]  = new_grid
            view.garden["last_fertilize"] = now.isoformat()

            db_update_garden(view.user_id, garden_grid=new_grid, last_fertilize=now.isoformat())

            notice = (
                f"💩 Engrais appliqué ! **{pushed}** fleur(s) ont poussé."
                if pushed else
                "💩 Engrais appliqué… mais rien n'a poussé cette fois !"
            )
            await view.refresh(interaction, notice)

        # ── ✂️ Couper tout
        elif self.action == "couper_tout":
            if count_flowers(view.garden["garden_grid"]) == 0:
                await interaction.response.send_message(
                    "🌱 Aucune fleur à couper pour l'instant !",
                    ephemeral=True
                )
                return

            view.garden, cut = harvest_all(view.garden)
            db_update_garden(
                view.user_id,
                garden_grid=view.garden["garden_grid"],
                inventory=view.garden["inventory"]
            )
            await view.refresh(interaction, f"✂️ **{cut}** fleur(s) récoltée(s) et ajoutée(s) à l'inventaire !")

        # ── 🛍️ Inventaire
        elif self.action == "inventaire":
            inv = view.garden["inventory"]
            total = sum(inv.values())

            if total == 0:
                lines = ["🛍️ **Inventaire vide** — commence par faire pousser des fleurs !"]
            else:
                lines = ["🛍️ **Inventaire :**"]
                for emoji, qty in inv.items():
                    if qty > 0:
                        valeur = FLEUR_EMOJIS.get(emoji, 1) * qty
                        lines.append(f"  {emoji} × {qty}  *(vaut {valeur} 💵)*")
                lines.append(f"\n💵 Argent actuel : **{view.garden.get('argent', 0)}**")

            await interaction.response.send_message("\n".join(lines), ephemeral=True)

        # ── 💵 Vendre tout l'inventaire
        elif self.action == "vendre":
            inv = view.garden["inventory"]
            if sum(inv.values()) == 0:
                await interaction.response.send_message(
                    "🛍️ Ton inventaire est vide, rien à vendre !",
                    ephemeral=True
                )
                return

            view.garden, gained = sell_inventory(view.garden)
            db_update_garden(
                view.user_id,
                inventory=view.garden["inventory"],
                argent=view.garden["argent"]
            )
            await view.refresh(
                interaction,
                f"💵 Tu as vendu toutes tes fleurs pour **{gained} 💵** !\n"
                f"💰 Total en poche : **{view.garden['argent']} 💵**"
            )

        # ── ❓ Aide
        elif self.action == "aide":
            aide = (
                "**🏡 Aide — Jardin Interactif**\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "**Cliquer sur une case fleurie** → récolte la fleur\n"
                "**💩 Engrais** → fait pousser des fleurs sur les cases vides *(cooldown 5min)*\n"
                "**✂️ Couper tout** → récolte toutes les fleurs d'un coup\n"
                "**🛍️ Inventaire** → affiche les fleurs récoltées et leur valeur\n"
                "**💵 Vendre** → vend tout l'inventaire contre de l'argent\n\n"
                "**Valeur des fleurs :**\n"
                + "\n".join(f"  {e} → {v} 💵" for e, v in FLEUR_EMOJIS.items())
            )
            await interaction.response.send_message(aide, ephemeral=True)


# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class Jardin2Cog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="jardin2")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_jardin2(self, ctx: commands.Context):
        garden = get_or_create_garden(ctx.author.id, ctx.author.name)
        view   = JardinView(garden, ctx.author.id)
        header = format_garden_header(garden)
        await ctx.send(content=header, view=view)


# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Jardin2Cog(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Jeux"
    await bot.add_cog(cog)
