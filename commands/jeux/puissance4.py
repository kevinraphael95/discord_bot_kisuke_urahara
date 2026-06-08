# ────────────────────────────────────────────────────────────────────────────────
# 📌 puissance4.py — Commande interactive !puissance4 /puissance4
# Objectif : Jeu Puissance 4 via boutons Discord avec mode solo (vs bot) et multi
# Catégorie : Jeux
# Accès : Public
# Cooldown : 1 utilisation / 15 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button
import random
from utils.discord_utils import safe_send, safe_edit, safe_respond

# ────────────────────────────────────────────────────────────────────────────────
# 🎨 Constantes du jeu
# ────────────────────────────────────────────────────────────────────────────────
ROWS = 6
COLS = 7
EMPTY = "⬛"
TOKENS = ["🔴", "🟡"]  # Joueur 1 = 🔴, Joueur 2 / Bot = 🟡
COL_EMOJIS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣"]

# ────────────────────────────────────────────────────────────────────────────────
# 🧩 Logique du plateau
# ────────────────────────────────────────────────────────────────────────────────
def make_board():
    return [[EMPTY] * COLS for _ in range(ROWS)]

def drop_token(board, col, token):
    """Pose le jeton dans la colonne. Retourne la ligne utilisée ou -1 si pleine."""
    for row in range(ROWS - 1, -1, -1):
        if board[row][col] == EMPTY:
            board[row][col] = token
            return row
    return -1

def check_win(board, token):
    """Vérifie si le token a gagné."""
    # Horizontale
    for r in range(ROWS):
        for c in range(COLS - 3):
            if all(board[r][c + i] == token for i in range(4)):
                return True
    # Verticale
    for r in range(ROWS - 3):
        for c in range(COLS):
            if all(board[r + i][c] == token for i in range(4)):
                return True
    # Diagonale ↘
    for r in range(ROWS - 3):
        for c in range(COLS - 3):
            if all(board[r + i][c + i] == token for i in range(4)):
                return True
    # Diagonale ↙
    for r in range(ROWS - 3):
        for c in range(3, COLS):
            if all(board[r + i][c - i] == token for i in range(4)):
                return True
    return False

def is_full(board):
    return all(board[0][c] != EMPTY for c in range(COLS))

def available_cols(board):
    return [c for c in range(COLS) if board[0][c] == EMPTY]

# ────────────────────────────────────────────────────────────────────────────────
# 🤖 IA du bot (algo minimax simplifié)
# ────────────────────────────────────────────────────────────────────────────────
def bot_move(board):
    """Choisit la meilleure colonne pour le bot."""
    bot_token = TOKENS[1]
    player_token = TOKENS[0]

    # 1. Gagner si possible
    for col in available_cols(board):
        b = [row[:] for row in board]
        drop_token(b, col, bot_token)
        if check_win(b, bot_token):
            return col

    # 2. Bloquer le joueur
    for col in available_cols(board):
        b = [row[:] for row in board]
        drop_token(b, col, player_token)
        if check_win(b, player_token):
            return col

    # 3. Préférer le centre, sinon aléatoire
    preferred = sorted(available_cols(board), key=lambda c: abs(c - COLS // 2))
    return preferred[0] if preferred else random.choice(available_cols(board))

# ────────────────────────────────────────────────────────────────────────────────
# 🧩 Vue principale du jeu Puissance 4
# ────────────────────────────────────────────────────────────────────────────────
class Puissance4View(View):
    def __init__(self, player1: discord.User, player2: discord.User | None, vs_bot: bool):
        """
        player1 = lanceur du jeu (🔴)
        player2 = second joueur en mode multi (🟡), None en mode solo
        vs_bot  = True → le bot joue en 🟡
        """
        super().__init__(timeout=300)
        self.player1 = player1
        self.player2 = player2
        self.vs_bot = vs_bot
        self.board = make_board()
        self.current_turn = 0  # 0 = player1, 1 = player2/bot
        self.message = None
        self.game_over = False

        for col in range(COLS):
            self.add_item(ColumnButton(col, self))

    @property
    def current_player(self):
        return self.player1 if self.current_turn == 0 else self.player2

    @property
    def current_token(self):
        return TOKENS[self.current_turn]

    def build_board_str(self):
        rows = ["".join(row) for row in self.board]
        header = "".join(COL_EMOJIS)
        return header + "\n" + "\n".join(rows)

    def build_embed(self):
        p1_name = self.player1.display_name
        p2_name = "🤖 Kisuke" if self.vs_bot else (self.player2.display_name if self.player2 else "?")

        if self.vs_bot:
            title = f"🔴 {p1_name} vs 🟡 {p2_name}"
        else:
            title = f"🔴 {p1_name} vs 🟡 {p2_name}"

        embed = discord.Embed(
            title=f"🟡🔴 Puissance 4 — {title}",
            description=self.build_board_str(),
            color=discord.Color.gold()
        )

        if not self.game_over:
            if self.current_turn == 0:
                turn_text = f"{self.current_token} C'est ton tour, **{p1_name}** !"
            elif self.vs_bot:
                turn_text = f"{self.current_token} Le bot réfléchit..."
            else:
                turn_text = f"{self.current_token} C'est ton tour, **{p2_name}** !"
            embed.set_footer(text=turn_text)

        return embed

    async def update_message(self):
        if self.message and not self.game_over:
            await safe_edit(self.message, embed=self.build_embed(), view=self)

    async def play_column(self, interaction: discord.Interaction, col: int):
        """Joue dans la colonne col, gère le tour et l'éventuelle réponse du bot."""
        token = self.current_token
        row = drop_token(self.board, col, token)
        if row == -1:
            return await safe_respond(interaction, "❗ Cette colonne est pleine !", ephemeral=True)

        # Vérif victoire ou nul
        if check_win(self.board, token):
            await self.end_game(interaction, winner_token=token)
            return
        if is_full(self.board):
            await self.end_game(interaction, winner_token=None)
            return

        # Changer de tour
        self.current_turn = 1 - self.current_turn
        await self.update_message()
        try:
            await interaction.response.defer()
        except discord.InteractionResponded:
            pass

        # Tour du bot
        if self.vs_bot and self.current_turn == 1:
            await self.do_bot_turn(interaction)

    async def do_bot_turn(self, interaction: discord.Interaction):
        col = bot_move(self.board)
        token = self.current_token
        drop_token(self.board, col, token)

        if check_win(self.board, token):
            await self.end_game(interaction, winner_token=token)
            return
        if is_full(self.board):
            await self.end_game(interaction, winner_token=None)
            return

        self.current_turn = 0
        await self.update_message()

    async def end_game(self, interaction: discord.Interaction, winner_token: str | None):
        self.game_over = True
        self.stop()
        for item in self.children:
            item.disabled = True

        embed = self.build_embed()

        if winner_token is None:
            result = "🤝 Match nul ! Le plateau est plein."
            embed.color = discord.Color.grayed_out()
        elif winner_token == TOKENS[0]:
            result = f"🎉 **{self.player1.display_name}** a gagné !"
            embed.color = discord.Color.red()
        else:
            name = "🤖 Kisuke" if self.vs_bot else (self.player2.display_name if self.player2 else "?")
            result = f"🎉 **{name}** a gagné !"
            embed.color = discord.Color.yellow()

        embed.add_field(name="🏁 Résultat", value=result, inline=False)

        try:
            await interaction.response.edit_message(embed=embed, view=self)
        except discord.InteractionResponded:
            await interaction.edit_original_response(embed=embed, view=self)

# ────────────────────────────────────────────────────────────────────────────────
# 🔵 Bouton de colonne
# ────────────────────────────────────────────────────────────────────────────────
class ColumnButton(Button):
    def __init__(self, col: int, view_ref: Puissance4View):
        super().__init__(emoji=COL_EMOJIS[col], style=discord.ButtonStyle.secondary, row=0)
        self.col = col
        self.view_ref = view_ref

    async def callback(self, interaction: discord.Interaction):
        v = self.view_ref
        if v.game_over:
            return await safe_respond(interaction, "La partie est terminée.", ephemeral=True)

        # Vérif joueur autorisé
        if v.vs_bot:
            if interaction.user != v.player1:
                return await safe_respond(interaction, "⛔ Ce jeu ne t'appartient pas.", ephemeral=True)
        else:
            # mode multi : seul le joueur dont c'est le tour peut jouer
            expected = v.player1 if v.current_turn == 0 else v.player2
            if v.player2 is None:
                # Partie pas encore rejointe
                return await safe_respond(interaction, "⛔ En attente du second joueur.", ephemeral=True)
            if interaction.user != expected:
                return await safe_respond(interaction, f"⛔ C'est au tour de **{expected.display_name}**.", ephemeral=True)

        await v.play_column(interaction, self.col)

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ Vue d'invitation (mode multi — attente du second joueur)
# ────────────────────────────────────────────────────────────────────────────────
class JoinView(View):
    def __init__(self, player1: discord.User):
        super().__init__(timeout=60)
        self.player1 = player1

    @discord.ui.button(label="Rejoindre la partie 🟡", style=discord.ButtonStyle.success)
    async def join(self, interaction: discord.Interaction, button: Button):
        if interaction.user == self.player1:
            return await safe_respond(interaction, "⛔ Tu ne peux pas jouer contre toi-même.", ephemeral=True)
        self.stop()
        view = Puissance4View(self.player1, interaction.user, vs_bot=False)
        embed = view.build_embed()
        await interaction.response.edit_message(embed=embed, view=view)
        view.message = interaction.message

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class Puissance4(commands.Cog):
    """Puissance 4 interactif avec commandes prefix et slash."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="puissance4", aliases=["p4", "c4"], help="Jouer au Puissance 4.")
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def prefix_puissance4(self, ctx: commands.Context, mode: str = "solo"):
        """
        mode = "solo" → contre le bot
        mode = "multi" → attend qu'un autre joueur rejoigne
        """
        await self._start_game(ctx.channel, ctx.author, mode)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(name="puissance4", description="Jouer au Puissance 4.")
    @app_commands.describe(mode="Mode de jeu : solo (vs bot) ou multi (vs joueur)")
    @app_commands.checks.cooldown(1, 15.0, key=lambda i: i.user.id)
    async def slash_puissance4(self, interaction: discord.Interaction, mode: str = "solo"):
        await self._start_game_slash(interaction, mode)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔧 Helpers internes
    # ────────────────────────────────────────────────────────────────────────────
    async def _start_game(self, channel, author: discord.User, mode: str):
        if mode.lower() == "multi":
            embed = discord.Embed(
                title="🟡🔴 Puissance 4 — Mode Multi",
                description=f"**{author.display_name}** lance une partie !\nClique sur le bouton pour rejoindre en 🟡.",
                color=discord.Color.orange()
            )
            view = JoinView(author)
            msg = await safe_send(channel, embed=embed, view=view)
        else:
            view = Puissance4View(author, None, vs_bot=True)
            embed = view.build_embed()
            msg = await safe_send(channel, embed=embed, view=view)
            view.message = msg

    async def _start_game_slash(self, interaction: discord.Interaction, mode: str):
        if mode.lower() == "multi":
            embed = discord.Embed(
                title="🟡🔴 Puissance 4 — Mode Multi",
                description=f"**{interaction.user.display_name}** lance une partie !\nClique sur le bouton pour rejoindre en 🟡.",
                color=discord.Color.orange()
            )
            view = JoinView(interaction.user)
            await interaction.response.send_message(embed=embed, view=view)
        else:
            view = Puissance4View(interaction.user, None, vs_bot=True)
            embed = view.build_embed()
            await interaction.response.send_message(embed=embed, view=view)
            view.message = await interaction.original_response()

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Puissance4(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Jeux"
    await bot.add_cog(cog)
