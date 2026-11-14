# ================================================================================
# 📌 bonbonbataille.py — Commande interactive /bonbonbataille et !bonbonbataille
# Objectif : Mini-jeu de retournement de cases avec des bonbons et des pièges
# Catégorie : Reiatsu
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ================================================================================

# ================================================================================
# 📦 Modules standards
# ================================================================================
import random

# ================================================================================
# 📦  Modules tiers
# ================================================================================
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button

# ================================================================================
# 📦 Modules internes
# ================================================================================
from utils.discord_anti429 import safe_send, safe_edit, safe_respond, safe_interact
from utils.init_db import get_conn

# ================================================================================
# 🍬 Configuration du jeu
# ================================================================================
# Discord : 5 rangées x 5 boutons max. Avec les indicateurs (ligne + colonne),
# la grille de jeu est donc limitée à 4x4.
GRID_SIZE = 4
BOMBS_COUNT = 4
NB_X1 = 6
NB_X2 = 4
NB_X3 = 2  # 4 + 6 + 4 + 2 = 16 cases

# --- Score ---
FIRST_GAIN = 1     # score du tout premier bonbon, quel que soit son niveau
MULT_BASE = 1.0    # multiplicateur de départ
MULT_STEP = 0.5    # +0.5 par niveau : niveau 1 = x1.5, niveau 2 = x2, niveau 3 = x2.5

def multiplicateur(niveau: int) -> float:
    """Multiplicateur appliqué au score quand on mange un bonbon de ce niveau."""
    return MULT_BASE + MULT_STEP * niveau

# ================================================================================
# 🗄️ Helpers DB pour le Reiatsu
# ================================================================================
def add_reiatsu(user_id: int, username: str, points_to_add: int):
    """Ajoute du Reiatsu au joueur dans la base de données."""
    if points_to_add <= 0:
        return
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT points FROM reiatsu WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()

        if row:
            new_total = (row[0] or 0) + points_to_add
            cursor.execute("UPDATE reiatsu SET points = ? WHERE user_id = ?", (new_total, user_id))
        else:
            cursor.execute(
                "INSERT INTO reiatsu (user_id, username, points) VALUES (?, ?, ?)",
                (user_id, username, points_to_add)
            )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[ERREUR DB] Impossible d'ajouter du Reiatsu : {e}")

# ================================================================================
# 🧩 Génération du plateau
# ================================================================================
def generer_plateau():
    """Génère une grille 4x4 avec des niveaux de bonbon (1,2,3) et des bombes (0)."""
    pool = [0] * BOMBS_COUNT + [1] * NB_X1 + [2] * NB_X2 + [3] * NB_X3
    random.shuffle(pool)
    return [pool[i * GRID_SIZE:(i + 1) * GRID_SIZE] for i in range(GRID_SIZE)]

def calculer_indicateurs(grid):
    """Calcule les sommes et le nombre de bombes par ligne et colonne."""
    rows_info = []
    cols_info = []

    for i in range(GRID_SIZE):
        row_sum = sum(val for val in grid[i] if val > 0)
        row_bombs = sum(1 for val in grid[i] if val == 0)
        rows_info.append((row_sum, row_bombs))

    for j in range(GRID_SIZE):
        col_sum = sum(grid[i][j] for i in range(GRID_SIZE) if grid[i][j] > 0)
        col_bombs = sum(1 for i in range(GRID_SIZE) if grid[i][j] == 0)
        cols_info.append((col_sum, col_bombs))

    return rows_info, cols_info

# ================================================================================
# 🎛️ UI — La vue du jeu
# ================================================================================
class BonbonView(View):
    def __init__(self, author: discord.User | discord.Member, grid: list, rows_info: list, cols_info: list):
        super().__init__(timeout=300)
        self.author = author
        self.grid = grid
        self.rows_info = rows_info
        self.cols_info = cols_info
        self.score = 0.0
        self.cases_revelees = set()
        self.is_dead = False
        self.message = None

        # 1. Rangée 0 : bouton Encaisser (coin) + indicateurs de colonnes
        self.btn_encaisser = Button(label="💰", style=discord.ButtonStyle.success, row=0)
        self.btn_encaisser.callback = self.encaisser_callback
        self.add_item(self.btn_encaisser)

        for j in range(GRID_SIZE):
            self.add_item(Button(
                label=f"{cols_info[j][0]}|{cols_info[j][1]}",
                style=discord.ButtonStyle.secondary, disabled=True, row=0
            ))

        # 2. Rangées 1..4 : indicateur de ligne + cases du jeu
        for i in range(GRID_SIZE):
            self.add_item(Button(
                label=f"{rows_info[i][0]}|{rows_info[i][1]}",
                style=discord.ButtonStyle.secondary, disabled=True, row=i + 1
            ))

            for j in range(GRID_SIZE):
                btn = Button(label="❓", style=discord.ButtonStyle.primary, row=i + 1)
                btn.callback = self.create_callback(i, j, btn)
                self.add_item(btn)

    # ------------------------------------------------------------------
    # 💰 Encaisser
    # ------------------------------------------------------------------
    async def encaisser_callback(self, interaction: discord.Interaction):
        if interaction.user != self.author:
            return await safe_respond(interaction, "❌ Ce n'est pas ta partie !", ephemeral=True)
        if self.is_dead:
            return

        self.is_dead = True
        self.disable_all_game_buttons()
        gain = int(self.score)
        add_reiatsu(self.author.id, self.author.name, gain)
        embed = self.generate_embed(f"💰 Tu encaisses **{gain} Reiatsu** !", discord.Color.green())
        await safe_interact(interaction, edit=True, embed=embed, view=self)
        self.stop()

    # ------------------------------------------------------------------
    # 🍬 Clic sur une case
    # ------------------------------------------------------------------
    def create_callback(self, i, j, btn):
        async def callback(interaction: discord.Interaction):
            if interaction.user != self.author:
                return await safe_respond(interaction, "❌ Ce n'est pas ta partie !", ephemeral=True)
            if self.is_dead:
                return

            val = self.grid[i][j]

            if val == 0:
                # BOUM ! Bonbon épicé
                self.is_dead = True
                btn.label = "🌶️"
                btn.style = discord.ButtonStyle.danger
                btn.disabled = True
                self.score = 0.0
                self.disable_all_game_buttons()
                embed = self.generate_embed(
                    "💥 **AÏE AÏE AÏE !** Tu es tombé sur un bonbon super épicé. Tu perds tous tes points !",
                    discord.Color.red()
                )
                await safe_interact(interaction, edit=True, embed=embed, view=self)
                self.stop()
                return

            # Bonbon normal
            btn.style = discord.ButtonStyle.success
            btn.label = f"🍬 {val}"
            btn.disabled = True
            self.cases_revelees.add((i, j))

            # Logique de score : 1er bonbon = FIRST_GAIN, ensuite on multiplie
            if len(self.cases_revelees) == 1:
                self.score = float(FIRST_GAIN)
                detail = f"Premier bonbon : **{FIRST_GAIN}** Reiatsu de départ."
            else:
                self.score *= multiplicateur(val)
                detail = f"Bonbon de niveau **{val}** (×{multiplicateur(val):g}) !"

            embed = self.generate_embed(f"{detail} Ton score est de **{int(self.score)}** Reiatsu.")

            # Victoire : toutes les cases de niveau > 1 ont été révélées
            total_high_cases = sum(1 for row in self.grid for v in row if v > 1)
            revealed_high_cases = sum(1 for c in self.cases_revelees if self.grid[c[0]][c[1]] > 1)

            if revealed_high_cases == total_high_cases:
                self.is_dead = True
                self.disable_all_game_buttons()
                gain = int(self.score)
                add_reiatsu(self.author.id, self.author.name, gain)
                embed = self.generate_embed(
                    f"🎉 **INCROYABLE !** Tu as trouvé tous les bons bonbons ! Tu remportes **{gain} Reiatsu** !",
                    discord.Color.green()
                )
                await safe_interact(interaction, edit=True, embed=embed, view=self)
                self.stop()
            else:
                await safe_interact(interaction, edit=True, embed=embed, view=self)

        return callback

    # ------------------------------------------------------------------
    # 🔒 Utilitaires
    # ------------------------------------------------------------------
    def disable_all_game_buttons(self):
        """Désactive les cases non révélées et le bouton Encaisser."""
        for child in self.children:
            if child.label == "❓" or child is self.btn_encaisser:
                child.disabled = True

    async def on_timeout(self):
        """Fin de partie par inactivité : on désactive tout (rien n'est encaissé)."""
        if self.is_dead:
            return
        self.is_dead = True
        self.disable_all_game_buttons()
        if self.message:
            embed = self.generate_embed("⌛ Temps écoulé, la partie est terminée sans encaissement.", discord.Color.dark_grey())
            await safe_edit(self.message, embed=embed, view=self)

    def generate_embed(self, action_text, color=discord.Color.orange()):
        desc = f"**Score actuel :** {int(self.score)} Reiatsu\n\n{action_text}"
        embed = discord.Embed(
            title="🍬 La Bonbonbataille de Urahara",
            description=desc,
            color=color
        )
        embed.set_footer(text="Indicateurs : somme des niveaux | nombre de bombes. 💰 pour encaisser.")
        return embed

# ================================================================================
# 🧠 Cog principal
# ================================================================================
class BonbonBataille(commands.Cog):
    """Commandes /bonbonbataille et !bb — Mini-jeu de la boutique de Urahara."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ============================================================================
    # 🔹 Commande SLASH
    # ============================================================================
    @app_commands.command(name="bonbonbataille", description="🍬 Joue à la Bonbonbataille de Urahara !")
    @app_commands.checks.cooldown(rate=1, per=5.0, key=lambda i: i.user.id)
    async def slash_bonbonbataille(self, interaction: discord.Interaction):
        grid = generer_plateau()
        rows_info, cols_info = calculer_indicateurs(grid)

        view = BonbonView(interaction.user, grid, rows_info, cols_info)
        embed = view.generate_embed("Bienvenue dans la **Bonbonbataille** !\nClique sur une case pour manger un bonbon. Si tu tombes sur un bonbon super épicé, tu perds tout ! Encaisse avant de tout perdre.")

        await safe_respond(interaction, embed=embed, view=view)
        view.message = await interaction.original_response()

    # ============================================================================
    # 🔹 Commande PREFIX
    # ============================================================================
    @commands.command(name="bonbonbataille", aliases=["bb"], help="🍬 Joue à la Bonbonbataille de Urahara !")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_bonbonbataille(self, ctx: commands.Context):
        grid = generer_plateau()
        rows_info, cols_info = calculer_indicateurs(grid)

        view = BonbonView(ctx.author, grid, rows_info, cols_info)
        embed = view.generate_embed("Bienvenue dans la **Bonbonbataille** !\nClique sur une case pour manger un bonbon. Si tu tombes sur un bonbon super épicé, tu perds tout ! Encaisse avant de tout perdre.")

        view.message = await safe_send(ctx.channel, embed=embed, view=view)

    # ============================================================================
    # 🔹 Gestion des cooldowns (sinon l'utilisateur ne voit rien)
    # ============================================================================
    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                f"⏳ Doucement ! Réessaie dans {error.retry_after:.1f}s.", ephemeral=True
            )
            return
        raise error

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.CommandOnCooldown):
            await safe_send(ctx.channel, f"⏳ Doucement ! Réessaie dans {error.retry_after:.1f}s.")
            return
        raise error

# ================================================================================
# 🔌 Setup du Cog
# ================================================================================
async def setup(bot: commands.Bot):
    cog = BonbonBataille(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Reiatsu"
    await bot.add_cog(cog)
