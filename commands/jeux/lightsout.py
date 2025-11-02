# ────────────────────────────────────────────────────────────────────────────────
# 💡 lightsout.py — Commande interactive /lightsout et !lightsout
# Objectif : Jeu "Lights Out" avec grille de boutons interactifs (toujours résoluble)
# Catégorie : Jeux
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
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
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class LightsOut(commands.Cog):
    """
    Commande /lightsout et !lightsout — Jeu interactif Lights Out 5x5 avec solution
    """
    TAILLE_GRILLE = 5
    INACTIVITE_MAX = 180

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.sessions = {}
        self.verif_inactivite.start()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Génération de la grille
    # ────────────────────────────────────────────────────────────────────────────
    def generate_solvable_grid(self, n):
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

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Calcul de la solution
    # ────────────────────────────────────────────────────────────────────────────
    def solve_mod2(self, grid):
        n = self.TAILLE_GRILLE
        A = np.zeros((n*n, n*n), dtype=int)
        for y in range(n):
            for x in range(n):
                idx = y*n + x
                for dx, dy in [(0,0),(1,0),(-1,0),(0,1),(0,-1)]:
                    nx, ny = x+dx, y+dy
                    if 0 <= nx < n and 0 <= ny < n:
                        A[ny*n + nx, idx] = 1
        b = np.array([int(grid[y][x]) for y in range(n) for x in range(n)], dtype=int)
        # Gauss-Jordan modulo 2
        A = A.copy() % 2
        b = b.copy() % 2
        for col in range(n*n):
            pivot = None
            for row in range(col, n*n):
                if A[row, col] == 1:
                    pivot = row
                    break
            if pivot is None:
                continue
            if pivot != col:
                A[[col, pivot]] = A[[pivot, col]]
                b[[col, pivot]] = b[[pivot, col]]
            for row in range(n*n):
                if row != col and A[row, col] == 1:
                    A[row] = (A[row] + A[col]) % 2
                    b[row] = (b[row] + b[col]) % 2
        return b.reshape((n,n))

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Embed de la grille
    # ────────────────────────────────────────────────────────────────────────────
    def get_embed(self, grid, solution_highlight=None):
        desc = ""
        n = self.TAILLE_GRILLE
        for y in range(n):
            for x in range(n):
                if solution_highlight is not None and solution_highlight[y][x]:
                    desc += "💡"
                else:
                    desc += "🔆" if grid[y][x] else "⬛"
            desc += "\n"
        embed = discord.Embed(
            title="💡 Jeu Lights Out",
            description=desc,
            color=discord.Color.gold()
        )
        return embed

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Création de la vue avec boutons
    # ────────────────────────────────────────────────────────────────────────────
    def create_view(self, grid, channel_id, player_id=None):
        view = discord.ui.View(timeout=None)
        n = self.TAILLE_GRILLE
        for y in range(n):
            for x in range(n):
                button = discord.ui.Button(label=" ", emoji="🔆" if grid[y][x] else "⬛",
                                           style=discord.ButtonStyle.success if grid[y][x] else discord.ButtonStyle.secondary)
                async def callback(interaction, xx=x, yy=y):
                    session = self.sessions.get(channel_id)
                    if not session:
                        await interaction.response.send_message("❌ Partie terminée.", ephemeral=True)
                        return
                    session['grid'][yy][xx] = not session['grid'][yy][xx]
                    for dx, dy in [(1,0),(-1,0),(0,1),(0,-1)]:
                        nx, ny = xx+dx, yy+dy
                        if 0<=nx<n and 0<=ny<n:
                            session['grid'][ny][nx] = not session['grid'][ny][nx]
                    embed = self.get_embed(session['grid'])
                    await interaction.response.edit_message(embed=embed, view=self)
                button.callback = callback
                view.add_item(button)
        # Bouton solution
        solution_button = discord.ui.Button(label="💡 Solution", style=discord.ButtonStyle.primary)
        async def solution_callback(interaction):
            session = self.sessions.get(channel_id)
            if not session:
                await interaction.response.send_message("❌ Partie terminée.", ephemeral=True)
                return
            sol = self.solve_mod2(session['grid'])
            embed = self.get_embed(session['grid'], solution_highlight=sol)
            await interaction.response.edit_message(embed=embed, view=view)
        solution_button.callback = solution_callback
        view.add_item(solution_button)
        return view

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(name="lightsout", description="💡 Lance une partie Lights Out")
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_lightsout(self, interaction: discord.Interaction):
        n = self.TAILLE_GRILLE
        grid = self.generate_solvable_grid(n)
        view = self.create_view(grid, interaction.channel_id, player_id=interaction.user.id)
        self.sessions[interaction.channel_id] = {'grid': grid, 'player_id': interaction.user.id}
        embed = self.get_embed(grid)
        await safe_respond(interaction, embed=embed, view=view)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="lightsout")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_lightsout(self, ctx: commands.Context):
        n = self.TAILLE_GRILLE
        grid = self.generate_solvable_grid(n)
        view = self.create_view(grid, ctx.channel.id, player_id=ctx.author.id)
        self.sessions[ctx.channel.id] = {'grid': grid, 'player_id': ctx.author.id}
        embed = self.get_embed(grid)
        await safe_send(ctx.channel, embed=embed, view=view)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Vérification inactivité
    # ────────────────────────────────────────────────────────────────────────────
    @tasks.loop(seconds=30)
    async def verif_inactivite(self):
        now = asyncio.get_event_loop().time()
        to_remove = []
        for cid, session in list(self.sessions.items()):
            if now - session.get('last_activity', now) > self.INACTIVITE_MAX:
                to_remove.append(cid)
        for cid in to_remove:
            self.sessions.pop(cid, None)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = LightsOut(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Jeux"
    await bot.add_cog(cog)
