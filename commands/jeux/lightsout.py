# ────────────────────────────────────────────────────────────────────────────────
# 💡 lightsout.py — Commande interactive !lightsout et /lightsout
# Objectif : Jeu "Lights Out" avec grille de boutons interactifs (toujours résoluble)
# Catégorie : Jeux
# Accès : Public
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands, tasks
import asyncio
import numpy as np
from utils.discord_utils import safe_send, safe_respond

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Constantes du jeu
# ────────────────────────────────────────────────────────────────────────────────
TAILLE_GRILLE = 5
INACTIVITE_MAX = 180
COULEUR_ACTIVE = 0xFFD700
COULEUR_INACTIVE = 0x2F3136

# ────────────────────────────────────────────────────────────────────────────────
# 🧩 Classe LightsOutGame
# ────────────────────────────────────────────────────────────────────────────────
class LightsOutGame:
    """Gestion de la grille et des règles du jeu Lights Out."""
    def __init__(self, size: int = TAILLE_GRILLE, mode: str = "solo"):
        self.size = size
        self.mode = mode
        self.terminee = False
        self.grid = self.generate_solvable_grid()

    def generate_solvable_grid(self):
        """Crée une grille toujours résoluble."""
        n = self.size
        x = np.random.randint(0, 2, size=(n*n), dtype=int)
        A = np.zeros((n*n, n*n), dtype=int)
        for y in range(n):
            for x0 in range(n):
                idx = y*n + x0
                for dx, dy in [(0,0),(1,0),(-1,0),(0,1),(0,-1)]:
                    nx, ny = x0+dx, y+dy
                    if 0 <= nx < n and 0 <= ny < n:
                        A[ny*n + nx, idx] = 1
        b = (A @ x) % 2
        return [[bool(b[y*n + x0]) for x0 in range(n)] for y in range(n)]

    def toggle(self, x: int, y: int):
        """Inverse l’état d’une case et de ses voisines."""
        if self.terminee:
            return
        for dx, dy in [(0,0),(1,0),(-1,0),(0,1),(0,-1)]:
            nx, ny = x+dx, y+dy
            if 0 <= nx < self.size and 0 <= ny < self.size:
                self.grid[ny][nx] = not self.grid[ny][nx]
        if self.check_win():
            self.terminee = True

    def check_win(self) -> bool:
        return all(not cell for row in self.grid for cell in row)

    def get_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=f"💡 Jeu Lights Out — mode {self.mode.capitalize()}",
            description="Clique sur les boutons pour éteindre toutes les lumières !",
            color=discord.Color.gold(),
        )
        status = "✅ Toutes les lumières sont éteintes ! Bravo !" if self.terminee else "🕹️ Clique sur les cases pour jouer."
        embed.add_field(name="État", value=status, inline=False)
        return embed

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ Classe LightsOutView
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
        self.clear_items()
        for y in range(self.game.size):
            row = []
            for x in range(self.game.size):
                style = discord.ButtonStyle.success if self.game.grid[y][x] else discord.ButtonStyle.secondary
                emoji = "🔆" if self.game.grid[y][x] else "⬛"
                button = discord.ui.Button(label=" ", emoji=emoji, style=style, custom_id=f"light_{x}_{y}")
                button.callback = self.make_callback(x, y)
                row.append(button)
            for b in row:
                self.add_item(b)

    def make_callback(self, x: int, y: int):
        async def callback(interaction: discord.Interaction):
            session = self.parent_cog.sessions.get(self.channel_id)
            if not session:
                await interaction.response.send_message("❌ Cette partie n'existe plus.", ephemeral=True)
                return
            if self.game.mode == "solo" and interaction.user.id != self.player_id:
                await interaction.response.send_message(
                    "❌ Seul le joueur ayant lancé la partie peut jouer en mode solo.", ephemeral=True
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
# 🕹️ Classe LightsOutSession
# ────────────────────────────────────────────────────────────────────────────────
class LightsOutSession:
    """Représente une session active de jeu Lights Out dans un salon."""
    def __init__(self, game: LightsOutGame, message: discord.Message, mode: str = "solo", author_id: int | None = None):
        self.game = game
        self.message = message
        self.mode = mode
        self.last_activity = asyncio.get_event_loop().time()
        self.author_id = author_id

# ────────────────────────────────────────────────────────────────────────────────
# 🧩 Cog principal — LightsOut
# ────────────────────────────────────────────────────────────────────────────────
class LightsOut(commands.Cog):
    """
    Commande !lightsout et /lightsout — Lancer une partie de Lights Out
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.sessions = {}
        self.verif_inactivite.start()

    def cog_unload(self):
        self.verif_inactivite.cancel()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="lightsout", aliases=["lo"])
    async def lightsout_cmd(self, ctx: commands.Context, mode: str = ""):
        await self.start_game(ctx.channel, ctx.author.id, mode, ctx)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(name="lightsout", description="Lancer une partie de Lights Out")
    async def slash_lightsout(self, interaction: discord.Interaction, mode: str = ""):
        await self.start_game(interaction.channel, interaction.user.id, mode, interaction)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Méthode commune pour lancer une partie
    # ────────────────────────────────────────────────────────────────────────────
    async def start_game(self, channel, author_id: int, mode: str, ctx_or_interaction):
        mode = mode.lower()
        if mode not in ("multi", "m"):
            mode = "solo"
        channel_id = channel.id
        if channel_id in self.sessions:
            msg = "❌ Une partie est déjà en cours dans ce salon."
            if isinstance(ctx_or_interaction, commands.Context):
                await safe_send(channel, msg)
            else:
                await safe_respond(ctx_or_interaction, msg)
            return
        game = LightsOutGame(mode=mode)
        embed = game.get_embed()
        view = LightsOutView(game, self, channel_id, player_id=author_id if mode=="solo" else None)
        if isinstance(ctx_or_interaction, commands.Context):
            message = await safe_send(channel, embed=embed, view=view)
        else:
            message = await ctx_or_interaction.channel.send(embed=embed, view=view)
            await ctx_or_interaction.response.send_message("✅ Partie lancée !", ephemeral=True)
        session = LightsOutSession(game, message, mode=mode, author_id=author_id)
        self.sessions[channel_id] = session

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Vérification d’inactivité
    # ────────────────────────────────────────────────────────────────────────────
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
