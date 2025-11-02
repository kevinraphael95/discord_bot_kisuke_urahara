# ────────────────────────────────────────────────────────────────────────────────
# 💡 lightsout.py — Commande interactive /lightsout et !lightsout
# Objectif : Jeu "Lights Out" avec suivi pas-à-pas et solution interactive
# Catégorie : Jeux
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

import discord
from discord import app_commands
from discord.ext import commands, tasks
import asyncio
import numpy as np
from utils.discord_utils import safe_send, safe_respond

TAILLE_GRILLE = 5
INACTIVITE_MAX = 180

class LightsOut(commands.Cog):
    """
    Commande /lightsout et !lightsout — Jeu interactif Lights Out 5x5 avec solution pas-à-pas
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.sessions = {}
        self.verif_inactivite.start()

    # ────────────────────────────────────────────────────────────────────────────
    # Génération d'une grille résoluble
    # ────────────────────────────────────────────────────────────────────────────
    def generate_grid(self):
        n = TAILLE_GRILLE
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
    # Calcul de la solution complète (Gauss-Jordan mod 2)
    # ────────────────────────────────────────────────────────────────────────────
    def solve_mod2(self, grid):
        n = TAILLE_GRILLE
        A = np.zeros((n*n, n*n), dtype=int)
        for y in range(n):
            for x in range(n):
                idx = y*n + x
                for dx, dy in [(0,0),(1,0),(-1,0),(0,1),(0,-1)]:
                    nx, ny = x+dx, y+dy
                    if 0 <= nx < n and 0 <= ny < n:
                        A[ny*n + nx, idx] = 1
        b = np.array([int(grid[y][x]) for y in range(n) for x in range(n)], dtype=int)
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
    # Création de l'embed
    # ────────────────────────────────────────────────────────────────────────────
    def get_embed(self, grid, highlight=None):
        desc = ""
        n = TAILLE_GRILLE
        for y in range(n):
            for x in range(n):
                if highlight and highlight[y][x]:
                    desc += "💡"
                else:
                    desc += "🔆" if grid[y][x] else "⬛"
            desc += "\n"
        embed = discord.Embed(title="💡 Jeu Lights Out", description=desc, color=discord.Color.gold())
        return embed

    # ────────────────────────────────────────────────────────────────────────────
    # Création de la vue avec boutons + solution pas-à-pas
    # ────────────────────────────────────────────────────────────────────────────
    def create_view(self, session_id):
        session = self.sessions[session_id]
        n = TAILLE_GRILLE
        view = discord.ui.View(timeout=None)

        for y in range(n):
            for x in range(n):
                button = discord.ui.Button(
                    label=" ",
                    emoji="🔆" if session['grid'][y][x] else "⬛",
                    style=discord.ButtonStyle.success if session['grid'][y][x] else discord.ButtonStyle.secondary
                )
                async def callback(interaction, xx=x, yy=y):
                    s = self.sessions.get(session_id)
                    if not s:
                        await interaction.response.send_message("❌ Partie terminée.", ephemeral=True)
                        return
                    for dx, dy in [(0,0),(1,0),(-1,0),(0,1),(0,-1)]:
                        nx, ny = xx+dx, yy+dy
                        if 0 <= nx < n and 0 <= ny < n:
                            s['grid'][ny][nx] = not s['grid'][ny][nx]
                    s['last_activity'] = asyncio.get_event_loop().time()
                    embed = self.get_embed(s['grid'])
                    await interaction.response.edit_message(embed=embed, view=self.create_view(session_id))
                    if all(not cell for row in s['grid'] for cell in row):
                        await interaction.followup.send("🎉 Bravo ! Toutes les lumières sont éteintes !", ephemeral=True)
                        self.sessions.pop(session_id, None)
                button.callback = callback
                view.add_item(button)

        # Bouton "Prochaine étape"
        solution_btn = discord.ui.Button(label="💡 Étape suivante", style=discord.ButtonStyle.primary)
        async def solution_callback(interaction):
            s = self.sessions.get(session_id)
            if not s:
                await interaction.response.send_message("❌ Partie terminée.", ephemeral=True)
                return
            solution = self.solve_mod2(s['grid'])
            # Cherche la première case de la solution qui est True
            highlight = np.zeros((n,n), dtype=bool)
            for y in range(n):
                for x in range(n):
                    if solution[y][x]:
                        highlight[y][x] = True
                        break
                if highlight.any():
                    break
            embed = self.get_embed(s['grid'], highlight=highlight)
            await interaction.response.edit_message(embed=embed, view=self.create_view(session_id))
        solution_btn.callback = solution_callback
        view.add_item(solution_btn)
        return view

    # ────────────────────────────────────────────────────────────────────────────
    # Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(name="lightsout", description="💡 Lance une partie Lights Out interactive")
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_lightsout(self, interaction: discord.Interaction):
        grid = self.generate_grid()
        session_id = interaction.channel_id
        self.sessions[session_id] = {'grid': grid, 'last_activity': asyncio.get_event_loop().time()}
        embed = self.get_embed(grid)
        view = self.create_view(session_id)
        await safe_respond(interaction, embed=embed, view=view)

    # ────────────────────────────────────────────────────────────────────────────
    # Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="lightsout")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_lightsout(self, ctx: commands.Context):
        grid = self.generate_grid()
        session_id = ctx.channel.id
        self.sessions[session_id] = {'grid': grid, 'last_activity': asyncio.get_event_loop().time()}
        embed = self.get_embed(grid)
        view = self.create_view(session_id)
        await safe_send(ctx.channel, embed=embed, view=view)

    # ────────────────────────────────────────────────────────────────────────────
    # Vérification inactivité
    # ────────────────────────────────────────────────────────────────────────────
    @tasks.loop(seconds=30)
    async def verif_inactivite(self):
        now = asyncio.get_event_loop().time()
        remove = []
        for sid, s in list(self.sessions.items()):
            if now - s.get('last_activity', now) > INACTIVITE_MAX:
                remove.append(sid)
        for sid in remove:
            self.sessions.pop(sid, None)

# ────────────────────────────────────────────────────────────────────────────────
# Setup Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = LightsOut(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Jeux"
    await bot.add_cog(cog)
