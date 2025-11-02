# ────────────────────────────────────────────────────────────────────────────────
# 📌 labyrinthe.py — Mini labyrinthe interactif avec trésor, piège et sortie
# Objectif : Permettre à l’utilisateur de se déplacer dans un labyrinthe sur Discord
# Catégorie : Jeux
# Accès : Tous
# Cooldown : 1 utilisation / 10 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands
from discord.ui import View, Button
from utils.discord_utils import safe_send, safe_respond
import random
import copy

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class Labyrinthe(commands.Cog):
    """
    Commande /labyrinthe et !labyrinthe — Mini jeu interactif Discord
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.size = 7  # Taille du labyrinthe (7x7)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Génération du labyrinthe
    # ────────────────────────────────────────────────────────────────────────────
    def generate_maze(self):
        """Génère un labyrinthe avec murs, trésor, piège, sortie et joueur."""
        maze = [['⬜' for _ in range(self.size)] for _ in range(self.size)]

        # Bordures extérieures
        for i in range(self.size):
            maze[0][i] = maze[self.size - 1][i] = '⬛'
            maze[i][0] = maze[i][self.size - 1] = '⬛'

        # Murs aléatoires
        for _ in range(self.size * 2):
            x, y = random.randint(1, self.size - 2), random.randint(1, self.size - 2)
            maze[y][x] = '⬛'

        # Trésor, piège, sortie
        positions = [(x, y) for x in range(1, self.size - 1)
                     for y in range(1, self.size - 1) if maze[y][x] == '⬜']
        treasure = random.choice(positions); positions.remove(treasure)
        trap = random.choice(positions); positions.remove(trap)
        exit_ = random.choice(positions)

        maze[treasure[1]][treasure[0]] = '💎'
        maze[trap[1]][trap[0]] = '⚠️'
        maze[exit_[1]][exit_[0]] = '🏁'

        # Position du joueur
        start = random.choice(positions)
        maze[start[1]][start[0]] = '🟦'

        return maze, start

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Rendu du labyrinthe avec vision limitée
    # ────────────────────────────────────────────────────────────────────────────
    def render_maze(self, maze, player_pos, vision=1):
        """Affiche le labyrinthe autour du joueur avec une vision limitée."""
        rendered = ""
        px, py = player_pos
        for y, row in enumerate(maze):
            for x, cell in enumerate(row):
                if abs(x - px) <= vision and abs(y - py) <= vision:
                    rendered += cell
                else:
                    rendered += '⬛'
            rendered += '\n'
        return rendered

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Classe View interactive (déplacements)
    # ────────────────────────────────────────────────────────────────────────────
    class MazeView(View):
        """Vue interactive du labyrinthe avec boutons directionnels."""
        def __init__(self, maze, player_pos, cog):
            super().__init__(timeout=120)
            self.maze = maze
            self.player_pos = player_pos
            self.cog = cog
            self.finished = False
            self.interaction_done = False  # Évite les erreurs d'interaction initiale

        async def update(self, interaction):
            """Met à jour le message affichant le labyrinthe."""
            if self.finished:
                return
            content = self.cog.render_maze(self.maze, self.player_pos)
            await interaction.message.edit(content=content, view=self)

        async def check_cell(self, x, y):
            """Vérifie le contenu de la case actuelle."""
            cell = self.maze[y][x]
            if cell == '💎':
                return "trésor"
            elif cell == '⚠️':
                return "piège"
            elif cell == '🏁':
                return "sortie"
            return "vide"

        def move_player(self, dx, dy):
            """Déplace le joueur si possible et retourne le type de case atteinte."""
            x, y = self.player_pos
            nx, ny = x + dx, y + dy
            if self.maze[ny][nx] != '⬛':
                self.maze[y][x] = '⬜'
                self.player_pos = (nx, ny)
                self.maze[ny][nx] = '🟦'
                return self.check_cell(nx, ny)
            return "mur"

        async def handle_result(self, interaction, result):
            """Gère le résultat d'une case spéciale."""
            if result == "trésor":
                self.finished = True
                await interaction.followup.send("💎 Tu as trouvé le trésor ! Félicitations !", ephemeral=True)
                self.stop()
            elif result == "piège":
                self.finished = True
                await interaction.followup.send("⚠️ Oh non ! Tu es tombé dans un piège...", ephemeral=True)
                self.stop()
            elif result == "sortie":
                self.finished = True
                await interaction.followup.send("🏁 Bravo ! Tu as trouvé la sortie !", ephemeral=True)
                self.stop()

        async def on_timeout(self):
            """Arrête la vue après inactivité prolongée."""
            self.finished = True

        # ── Boutons directionnels ───────────────────────────────────────────────
        @discord.ui.button(label='⬆️', style=discord.ButtonStyle.primary)
        async def up(self, button: Button, interaction: discord.Interaction):
            result = self.move_player(0, -1)
            if not self.interaction_done:
                await interaction.response.edit_message(content=self.cog.render_maze(self.maze, self.player_pos), view=self)
                self.interaction_done = True
            else:
                await self.update(interaction)
            if result != "mur":
                await self.handle_result(interaction, result)

        @discord.ui.button(label='⬇️', style=discord.ButtonStyle.primary)
        async def down(self, button: Button, interaction: discord.Interaction):
            result = self.move_player(0, 1)
            if not self.interaction_done:
                await interaction.response.edit_message(content=self.cog.render_maze(self.maze, self.player_pos), view=self)
                self.interaction_done = True
            else:
                await self.update(interaction)
            if result != "mur":
                await self.handle_result(interaction, result)

        @discord.ui.button(label='⬅️', style=discord.ButtonStyle.primary)
        async def left(self, button: Button, interaction: discord.Interaction):
            result = self.move_player(-1, 0)
            if not self.interaction_done:
                await interaction.response.edit_message(content=self.cog.render_maze(self.maze, self.player_pos), view=self)
                self.interaction_done = True
            else:
                await self.update(interaction)
            if result != "mur":
                await self.handle_result(interaction, result)

        @discord.ui.button(label='➡️', style=discord.ButtonStyle.primary)
        async def right(self, button: Button, interaction: discord.Interaction):
            result = self.move_player(1, 0)
            if not self.interaction_done:
                await interaction.response.edit_message(content=self.cog.render_maze(self.maze, self.player_pos), view=self)
                self.interaction_done = True
            else:
                await self.update(interaction)
            if result != "mur":
                await self.handle_result(interaction, result)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande HYBRIDE (Slash + Préfixe)
    # ────────────────────────────────────────────────────────────────────────────
    @commands.hybrid_command(
        name="labyrinthe",
        description="🕹️ Joue au mini labyrinthe interactif avec trésor et pièges !"
    )
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def labyrinthe_cmd(self, ctx: commands.Context):
        """Lance une nouvelle partie de labyrinthe."""
        maze, start = self.generate_maze()
        view = self.MazeView(copy.deepcopy(maze), start, self)
        content = self.render_maze(maze, start)
        await safe_send(ctx, content, view=view)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Labyrinthe(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Jeux"
    await bot.add_cog(cog)
