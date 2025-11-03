# ────────────────────────────────────────────────────────────────────────────────
# 📌 labyrinthe.py — Mini labyrinthe interactif (vision locale 3x3)
# ────────────────────────────────────────────────────────────────────────────────

import discord
from discord.ext import commands
from discord.ui import View, Button
from utils.discord_utils import safe_send
import random
import copy

class Labyrinthe(commands.Cog):
    """Mini jeu : explore un labyrinthe et trouve la sortie, le trésor ou évite le piège."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.size = 9  # Taille du labyrinthe (9x9 pour un peu d'espace)

    # ────────────────────────────────────────────────
    # Génération du labyrinthe
    # ────────────────────────────────────────────────
    def generate_maze(self):
        maze = [['⬜' for _ in range(self.size)] for _ in range(self.size)]

        # Bordures extérieures
        for i in range(self.size):
            maze[0][i] = maze[self.size - 1][i] = '⬛'
            maze[i][0] = maze[i][self.size - 1] = '⬛'

        # Murs aléatoires
        for _ in range(self.size * 2):
            x, y = random.randint(1, self.size - 2), random.randint(1, self.size - 2)
            maze[y][x] = '⬛'

        # Emplacements spéciaux
        positions = [(x, y) for x in range(1, self.size - 1)
                     for y in range(1, self.size - 1) if maze[y][x] == '⬜']
        random.shuffle(positions)
        treasure, trap, exit_, start = positions[:4]

        maze[treasure[1]][treasure[0]] = '💎'
        maze[trap[1]][trap[0]] = '⚠️'
        maze[exit_[1]][exit_[0]] = '🏁'
        maze[start[1]][start[0]] = '🟦'

        return maze, start

    # ────────────────────────────────────────────────
    # Rendu du labyrinthe (vision 3x3 autour du joueur)
    # ────────────────────────────────────────────────
    def render_maze(self, maze, player_pos):
        rendered = ""
        px, py = player_pos
        for y, row in enumerate(maze):
            for x, cell in enumerate(row):
                # Si la case est dans un carré 3x3 autour du joueur → visible
                if abs(x - px) <= 1 and abs(y - py) <= 1:
                    rendered += cell
                else:
                    rendered += '⬛'
            rendered += '\n'
        return rendered

    # ────────────────────────────────────────────────
    # Classe View (boutons directionnels)
    # ────────────────────────────────────────────────
    class MazeView(View):
        def __init__(self, maze, player_pos, cog):
            super().__init__(timeout=120)
            self.maze = maze
            self.player_pos = player_pos
            self.cog = cog
            self.finished = False

        async def update(self, interaction):
            """Met à jour l'affichage."""
            if not self.finished:
                content = self.cog.render_maze(self.maze, self.player_pos)
                await interaction.message.edit(content=content, view=self)

        def move_player(self, dx, dy):
            """Déplace le joueur si possible."""
            x, y = self.player_pos
            nx, ny = x + dx, y + dy
            if self.maze[ny][nx] == '⬛':
                return "mur"

            # Déplacement
            current = self.maze[ny][nx]
            self.maze[y][x] = '⬜'
            self.player_pos = (nx, ny)
            self.maze[ny][nx] = '🟦'

            if current == '💎':
                return "trésor"
            elif current == '⚠️':
                return "piège"
            elif current == '🏁':
                return "sortie"
            return "vide"

        async def handle_result(self, interaction, result):
            """Réactions selon la case atteinte."""
            if result == "mur":
                await interaction.followup.send("🚧 Tu ne peux pas passer ici !", ephemeral=True)
                return
            elif result == "trésor":
                msg = "💎 Tu as trouvé le **trésor** ! Félicitations !"
            elif result == "piège":
                msg = "⚠️ Oh non ! Tu es tombé dans un **piège**..."
            elif result == "sortie":
                msg = "🏁 Bravo ! Tu as trouvé la **sortie** !"
            else:
                await self.update(interaction)
                return

            self.finished = True
            for item in self.children:
                item.disabled = True
            await interaction.message.edit(content=self.cog.render_maze(self.maze, self.player_pos), view=self)
            await interaction.followup.send(msg, ephemeral=True)
            self.stop()

        async def on_timeout(self):
            """Fin de partie après inactivité."""
            self.finished = True
            for item in self.children:
                item.disabled = True

        # ── Boutons directionnels ──────────────────────
        @discord.ui.button(label="⬆️", style=discord.ButtonStyle.primary)
        async def up(self, _, interaction):
            result = self.move_player(0, -1)
            await self.handle_result(interaction, result)

        @discord.ui.button(label="⬇️", style=discord.ButtonStyle.primary)
        async def down(self, _, interaction):
            result = self.move_player(0, 1)
            await self.handle_result(interaction, result)

        @discord.ui.button(label="⬅️", style=discord.ButtonStyle.primary)
        async def left(self, _, interaction):
            result = self.move_player(-1, 0)
            await self.handle_result(interaction, result)

        @discord.ui.button(label="➡️", style=discord.ButtonStyle.primary)
        async def right(self, _, interaction):
            result = self.move_player(1, 0)
            await self.handle_result(interaction, result)

    # ────────────────────────────────────────────────
    # Commande principale
    # ────────────────────────────────────────────────
    @commands.hybrid_command(
        name="labyrinthe",
        description="🕹️ Explore un mini labyrinthe avec une vision limitée (3x3) !"
    )
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def labyrinthe_cmd(self, ctx: commands.Context):
        maze, start = self.generate_maze()
        view = self.MazeView(copy.deepcopy(maze), start, self)
        content = self.render_maze(maze, start)
        await safe_send(ctx, content, view=view)


async def setup(bot: commands.Bot):
    cog = Labyrinthe(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Jeux"
    await bot.add_cog(cog)
