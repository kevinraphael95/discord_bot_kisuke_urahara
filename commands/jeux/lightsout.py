# ────────────────────────────────────────────────────────────────────────────────
# 💡 lightsout.py — Commande interactive !lightsout
# Objectif : Jeu "Lights Out" avec grille de boutons interactifs (résoluble)
# Catégorie : Jeux
# Accès : Public
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands, tasks
import asyncio
import random
from utils.discord_utils import safe_send, safe_edit
import numpy as np  # Pour la génération résoluble

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Paramètres
# ────────────────────────────────────────────────────────────────────────────────
TAILLE_GRILLE = 5           # Taille de la grille (5x5)
INACTIVITE_MAX = 180        # 3 minutes (en secondes)
COULEUR_ACTIVE = 0xFFD700   # Couleur jaune (lumière allumée)
COULEUR_INACTIVE = 0x2F3136 # Couleur sombre (lumière éteinte)

# ────────────────────────────────────────────────────────────────────────────────
# 🧩 Classe LightsOutGame
# ────────────────────────────────────────────────────────────────────────────────
class LightsOutGame:
    def __init__(self, size: int = TAILLE_GRILLE, mode: str = "solo", resolvable: bool = True):
        self.size = size
        self.terminee = False
        self.mode = mode

        if resolvable:
            self.grid = self.generate_solvable_grid()
        else:
            self.grid = [[random.choice([True, False]) for _ in range(size)] for _ in range(size)]

    def generate_solvable_grid(self):
        """Crée une grille résoluble via un vecteur de coups aléatoire."""
        n = self.size
        x = np.random.randint(0, 2, size=(n*n), dtype=int)  # vecteur de coups aléatoire
        A = np.zeros((n*n, n*n), dtype=int)
        for y in range(n):
            for x0 in range(n):
                idx = y*n + x0
                for dx, dy in [(0,0),(1,0),(-1,0),(0,1),(0,-1)]:
                    nx, ny = x0+dx, y+dy
                    if 0 <= nx < n and 0 <= ny < n:
                        A[ny*n+nx, idx] = 1
        b = A @ x % 2  # grille finale solvable
        grid = [[bool(b[y*n + x0]) for x0 in range(n)] for y in range(n)]
        return grid

    def toggle(self, x: int, y: int):
        """Inverse l’état d’une case et de ses voisines."""
        if self.terminee:
            return
        directions = [(0,0),(1,0),(-1,0),(0,1),(0,-1)]
        for dx, dy in directions:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.size and 0 <= ny < self.size:
                self.grid[ny][nx] = not self.grid[ny][nx]
        if self.check_win():
            self.terminee = True

    def check_win(self) -> bool:
        """Retourne True si toutes les lumières sont éteintes."""
        return all(not cell for row in self.grid for cell in row)

    def get_embed(self) -> discord.Embed:
        """Crée un embed représentant l’état du jeu."""
        embed = discord.Embed(
            title=f"💡 Jeu Lights Out — mode {self.mode.capitalize()}",
            description="Clique sur les boutons pour éteindre toutes les lumières !",
            color=discord.Color.gold(),
        )
        status = "✅ Toutes les lumières sont éteintes ! Bravo !" if self.terminee else "🕹️ Clique sur les cases pour jouer."
        embed.add_field(name="État", value=status, inline=False)
        return embed

# ────────────────────────────────────────────────────────────────────────────────
# 🎮 Classe LightsOutView (interface de jeu)
# ────────────────────────────────────────────────────────────────────────────────
class LightsOutView(discord.ui.View):
    def __init__(self, game: LightsOutGame, parent_cog, channel_id: int, player_id: int | None = None):
        super().__init__(timeout=None)
        self.game = game
        self.parent_cog = parent_cog
        self.channel_id = channel_id
        self.player_id = player_id
        self.update_buttons()

    def update_buttons(self):
        """Met à jour les boutons selon l’état de la grille."""
        self.clear_items()
        for y in range(self.game.size):
            row = []
            for x in range(self.game.size):
                style = (
                    discord.ButtonStyle.success if self.game.grid[y][x]
                    else discord.ButtonStyle.secondary
                )
                emoji = "🔆" if self.game.grid[y][x] else "⬛"
                button = discord.ui.Button(
                    label=" ",
                    emoji=emoji,
                    style=style,
                    custom_id=f"light_{x}_{y}",
                )
                button.callback = self.make_callback(x, y)
                row.append(button)
            for b in row:
                self.add_item(b)

    def make_callback(self, x: int, y: int):
        async def callback(interaction: discord.Interaction):
            session = self.parent_cog.sessions.get(self.channel_id)
            if not session:
                await interaction.response.send_message(
                    "❌ Cette partie n'existe plus.", ephemeral=True
                )
                return

            if self.game.mode == "solo" and interaction.user.id != self.player_id:
                await interaction.response.send_message(
                    "❌ Seul le joueur ayant lancé la partie peut jouer en mode solo.",
                    ephemeral=True
                )
                return

            session.last_activity = asyncio.get_event_loop().time()
            self.game.toggle(x, y)
            self.update_buttons()

            embed = self.game.get_embed()
            await interaction.response.edit_message(embed=embed, view=self)

            if self.game.terminee:
                await safe_send(interaction.channel, f"🎉 Bravo {interaction.user.mention} ! Toutes les lumières sont éteintes !")
                self.parent_cog.sessions.pop(self.channel_id, None)

        return callback

# ────────────────────────────────────────────────────────────────────────────────
# 🧩 Classe LightsOutSession
# ────────────────────────────────────────────────────────────────────────────────
class LightsOutSession:
    def __init__(self, game: LightsOutGame, message: discord.Message, mode: str = "solo", author_id: int | None = None):
        self.game = game
        self.message = message
        self.mode = mode
        self.last_activity = asyncio.get_event_loop().time()
        self.author_id = author_id

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class LightsOut(commands.Cog):
    """Commande !lightsout — Jeu Lights Out interactif."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.sessions = {}
        self.verif_inactivite.start()

    def cog_unload(self):
        self.verif_inactivite.cancel()

    @commands.command(
        name="lightsout", aliases=["lo"],
        help="Joue au jeu des lumières à éteindre (solo ou multi).",
        description="!lightsout [multi] — Éteins toutes les lumières !",
    )
    async def lightsout_cmd(self, ctx: commands.Context, mode: str = ""):
        mode = mode.lower()
        if mode not in ("multi", "m"):
            mode = "solo"

        channel_id = ctx.channel.id
        if channel_id in self.sessions:
            await safe_send(ctx.channel, "❌ Une partie est déjà en cours dans ce salon.")
            return

        game = LightsOutGame(mode=mode, resolvable=True)
        embed = game.get_embed()
        view = LightsOutView(game, self, channel_id, player_id=ctx.author.id if mode == "solo" else None)
        message = await safe_send(ctx.channel, embed=embed, view=view)
        session = LightsOutSession(game, message, mode=mode, author_id=ctx.author.id)
        self.sessions[channel_id] = session

    @tasks.loop(seconds=30)
    async def verif_inactivite(self):
        now = asyncio.get_event_loop().time()
        a_supprimer = []
        for cid, session in list(self.sessions.items()):
            if now - session.last_activity > INACTIVITE_MAX:
                a_supprimer.append(cid)
        for cid in a_supprimer:
            session = self.sessions.pop(cid, None)
            if session:
                await safe_send(session.message.channel, "⏰ Partie terminée pour inactivité (3 minutes sans action).")

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = LightsOut(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Jeux"
    await bot.add_cog(cog)
