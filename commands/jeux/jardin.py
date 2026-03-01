# ────────────────────────────────────────────────────────────────────────────────
# 📌 jardin.py
# Objectif : Jardin interactif avec grille de boutons et stockage SQLite
# Catégorie : Jeux
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
import datetime
import random
import json

from utils.init_db import get_conn

# ────────────────────────────────────────────────────────────────────────────────
# ⚙️ Configuration
# ────────────────────────────────────────────────────────────────────────────────
GRID_ROWS = 4
GRID_COLS = 4
EMPTY_CELL = "🌱"

FLEUR_EMOJIS = {
    "🌸": 5,
    "🌼": 4,
    "🌻": 6,
    "🌹": 8,
    "🌺": 7,
    "💐": 10,
    "🪷": 9,
}

FERTILIZE_PROBABILITY = 0.4
FERTILIZE_COOLDOWN_MINUTES = 5
TABLE_NAME = "gardens"

# ────────────────────────────────────────────────────────────────────────────────
# 🛠️ Fonctions Base de Données
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
        INSERT OR IGNORE INTO gardens 
        (user_id, username, garden_grid, inventory, argent, last_fertilize)
        VALUES (?, ?, ?, ?, 0, NULL)
    """, (user_id, username, json.dumps(default_grid), json.dumps(default_inv)))
    conn.commit()
    conn.close()

    return db_get_garden(user_id)


def db_update_garden(user_id: int, **fields):
    if not fields:
        return

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

    row["garden_grid"] = json.loads(row["garden_grid"])
    row["inventory"] = json.loads(row["inventory"])
    return row

# ────────────────────────────────────────────────────────────────────────────────
# 🌿 Logique du jeu
# ────────────────────────────────────────────────────────────────────────────────
def pousser_fleurs(grid):
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


def count_flowers(grid):
    return sum(1 for row in grid for cell in row if cell != EMPTY_CELL)


def count_empty(grid):
    return sum(1 for row in grid for cell in row if cell == EMPTY_CELL)


def format_garden_header(garden: dict) -> str:
    grid = garden["garden_grid"]
    flowers = count_flowers(grid)
    empty = count_empty(grid)
    argent = garden.get("argent", 0)

    return (
        f"🏡 **Jardin de {garden['username']}**\n"
        f"🌸 Fleurs : **{flowers}** | 🌱 Vides : **{empty}** | 💵 Argent : **{argent}**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ Vue interactive
# ────────────────────────────────────────────────────────────────────────────────
class JardinView(discord.ui.View):
    def __init__(self, garden: dict, user_id: int):
        super().__init__(timeout=300)
        self.garden = garden
        self.user_id = user_id
        self._build_buttons()

    def _build_buttons(self):
        self.clear_items()
        grid = self.garden["garden_grid"]

        for r, row in enumerate(grid):
            for c, cell in enumerate(row):
                style = discord.ButtonStyle.success if cell == EMPTY_CELL else discord.ButtonStyle.secondary
                btn = discord.ui.Button(label=cell, style=style, row=r)
                self.add_item(btn)

    async def guard(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ Ce jardin n'est pas à toi !",
                ephemeral=True
            )
            return False
        return True

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal avec cooldown centralisé
# ────────────────────────────────────────────────────────────────────────────────
class JardinCog(commands.Cog):
    """
    Commande /jardin et !jardin — Ouvre ton jardin interactif
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction interne commune
    # ────────────────────────────────────────────────────────────────────────────
    async def _open_garden(self, channel, user):
        garden = get_or_create_garden(user.id, user.name)
        view = JardinView(garden, user.id)
        header = format_garden_header(garden)
        await channel.send(content=header, view=view)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="jardin",
        description="Ouvre ton jardin interactif."
    )
    @app_commands.checks.cooldown(rate=1, per=5.0, key=lambda i: i.user.id)
    async def slash_jardin(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self._open_garden(interaction.channel, interaction.user)
        await interaction.delete_original_response()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="jardin")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_jardin(self, ctx: commands.Context):
        await self._open_garden(ctx.channel, ctx.author)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = JardinCog(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Jeux"
    await bot.add_cog(cog)
