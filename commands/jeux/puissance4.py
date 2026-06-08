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
TOKENS = ["🔴", "🟡"]
COL_EMOJIS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣"]

# ────────────────────────────────────────────────────────────────────────────────
# 🧩 Logique du plateau
# ────────────────────────────────────────────────────────────────────────────────
def make_board():
    return [[EMPTY for _ in range(COLS)] for _ in range(ROWS)]

def drop_token(board, col, token):
    for row in range(ROWS - 1, -1, -1):
        if board[row][col] == EMPTY:
            board[row][col] = token
            return row
    return -1

def check_win(board, token):
    for r in range(ROWS):
        for c in range(COLS - 3):
            if all(board[r][c+i] == token for i in range(4)):
                return True

    for r in range(ROWS - 3):
        for c in range(COLS):
            if all(board[r+i][c] == token for i in range(4)):
                return True

    for r in range(ROWS - 3):
        for c in range(COLS - 3):
            if all(board[r+i][c+i] == token for i in range(4)):
                return True

    for r in range(3, ROWS):
        for c in range(COLS - 3):
            if all(board[r-i][c+i] == token for i in range(4)):
                return True

    return False

def is_full(board):
    return all(board[0][c] != EMPTY for c in range(COLS))

def available_cols(board):
    return [c for c in range(COLS) if board[0][c] == EMPTY]

# ────────────────────────────────────────────────────────────────────────────────
# 🤖 IA SIMPLE
# ────────────────────────────────────────────────────────────────────────────────
def bot_move(board):
    bot = TOKENS[1]
    player = TOKENS[0]

    cols = available_cols(board)
    if not cols:
        return None

    # win direct bot
    for col in cols:
        b = [row[:] for row in board]
        drop_token(b, col, bot)
        if check_win(b, bot):
            return col

    # block player
    for col in cols:
        b = [row[:] for row in board]
        drop_token(b, col, player)
        if check_win(b, player):
            return col

    # center play
    return min(cols, key=lambda c: abs(c - COLS // 2))

# ────────────────────────────────────────────────────────────────────────────────
# 🔵 BOUTON (DOIT ÊTRE AVANT LA VIEW)
# ────────────────────────────────────────────────────────────────────────────────
class ColumnButton(Button):
    def __init__(self, col, view):
        super().__init__(emoji=COL_EMOJIS[col], style=discord.ButtonStyle.secondary)
        self.col = col
        self.view_ref = view

    async def callback(self, interaction):
        v = self.view_ref

        if v.game_over:
            return await safe_respond(interaction, "Partie terminée", ephemeral=True)

        # check turn
        expected = v.player1 if v.turn == 0 else v.player2

        if v.vs_bot:
            if interaction.user != v.player1:
                return await safe_respond(interaction, "Pas ton jeu", ephemeral=True)
        else:
            if interaction.user != expected:
                return await safe_respond(interaction, "Pas ton tour", ephemeral=True)

        await v.play(interaction, self.col)

# ────────────────────────────────────────────────────────────────────────────────
# 🧩 VIEW
# ────────────────────────────────────────────────────────────────────────────────
class Puissance4View(View):
    def __init__(self, player1, player2=None, vs_bot=True):
        super().__init__(timeout=300)

        self.player1 = player1
        self.player2 = player2
        self.vs_bot = vs_bot

        self.board = make_board()
        self.turn = 0
        self.message = None
        self.game_over = False

        for i in range(COLS):
            self.add_item(ColumnButton(i, self))

    @property
    def current_token(self):
        return TOKENS[self.turn]

    def render(self):
        header = "".join(COL_EMOJIS)
        rows = ["".join(r) for r in self.board]
        return header + "\n" + "\n".join(rows)

    def embed(self):
        p2 = "🤖 Bot" if self.vs_bot else self.player2.display_name
        return discord.Embed(
            title="🟡🔴 Puissance 4",
            description=f"🔴 {self.player1.display_name} vs 🟡 {p2}\n\n{self.render()}",
            color=discord.Color.gold()
        )

    async def update(self):
        if self.message and not self.game_over:
            await safe_edit(self.message, embed=self.embed(), view=self)

    async def play(self, interaction, col):
        token = self.current_token

        row = drop_token(self.board, col, token)
        if row == -1:
            return await safe_respond(interaction, "Colonne pleine", ephemeral=True)

        if check_win(self.board, token):
            return await self.end(interaction, token)

        if is_full(self.board):
            return await self.end(interaction, None)

        self.turn = 1 - self.turn
        await self.update()

        if not interaction.response.is_done():
            await interaction.response.defer()

        if self.vs_bot and self.turn == 1:
            await self.bot_turn(interaction)

    async def bot_turn(self, interaction):
        col = bot_move(self.board)
        if col is None:
            return await self.end(interaction, None)

        token = self.current_token
        drop_token(self.board, col, token)

        if check_win(self.board, token):
            return await self.end(interaction, token)

        if is_full(self.board):
            return await self.end(interaction, None)

        self.turn = 0
        await self.update()

    async def end(self, interaction, winner):
        self.game_over = True
        self.stop()

        for c in self.children:
            c.disabled = True

        e = self.embed()

        if winner is None:
            e.add_field(name="Résultat", value="🤝 Match nul")
        elif winner == TOKENS[0]:
            e.add_field(name="Résultat", value=f"🏆 {self.player1.display_name}")
        else:
            name = "Bot" if self.vs_bot else self.player2.display_name
            e.add_field(name="Résultat", value=f"🏆 {name}")

        await interaction.response.edit_message(embed=e, view=self)

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 COG
# ────────────────────────────────────────────────────────────────────────────────
class Puissance4(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="puissance4", aliases=["p4"])
    async def p4(self, ctx, mode: str = "solo"):
        mode = mode.lower()

        if mode == "multi":
            view = JoinView(ctx.author)
            await safe_send(ctx.channel, "Clique pour rejoindre", view=view)
        else:
            view = Puissance4View(ctx.author, vs_bot=True)
            msg = await safe_send(ctx.channel, embed=view.embed(), view=view)
            view.message = msg

    @app_commands.command(name="puissance4")
    async def slash(self, interaction, mode: str = "solo"):
        mode = mode.lower()

        if mode == "multi":
            view = JoinView(interaction.user)
            await interaction.response.send_message("Clique pour rejoindre", view=view)
        else:
            view = Puissance4View(interaction.user, vs_bot=True)
            await interaction.response.send_message(embed=view.embed(), view=view)
            view.message = await interaction.original_response()

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ JOIN VIEW
# ────────────────────────────────────────────────────────────────────────────────
class JoinView(View):
    def __init__(self, p1):
        super().__init__(timeout=60)
        self.p1 = p1

    @discord.ui.button(label="Rejoindre", style=discord.ButtonStyle.green)
    async def join(self, interaction, button):
        if interaction.user == self.p1:
            return await safe_respond(interaction, "Impossible", ephemeral=True)

        view = Puissance4View(self.p1, interaction.user, vs_bot=False)
        await interaction.response.edit_message(embed=view.embed(), view=view)
        view.message = interaction.message

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 SETUP
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Puissance4(bot)

    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Jeux"

    await bot.add_cog(cog)
