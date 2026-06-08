# ────────────────────────────────────────────────────────────────────────────────
# 📌 puissance4.py — Puissance 4 Ultra Pro
# ────────────────────────────────────────────────────────────────────────────────

import discord
from discord.ext import commands
from discord.ui import View, Button
import copy
import random
import asyncio

from utils.discord_utils import safe_send, safe_edit, safe_respond

# ────────────────────────────────────────────────────────────────────────────────
# 🎨 CONSTANTES
# ────────────────────────────────────────────────────────────────────────────────
ROWS = 6
COLS = 7
EMPTY = "⬛"
TOKENS = ["🔴", "🟡"]
COL_EMOJIS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣"]

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 BOARD CORE
# ────────────────────────────────────────────────────────────────────────────────
def make_board():
    return [[EMPTY for _ in range(COLS)] for _ in range(ROWS)]

def available_cols(board):
    return [c for c in range(COLS) if board[0][c] == EMPTY]

def drop_token(board, col, token):
    for r in range(ROWS - 1, -1, -1):
        if board[r][col] == EMPTY:
            board[r][col] = token
            return r
    return -1

def is_full(board):
    return all(board[0][c] != EMPTY for c in range(COLS))

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

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 IA ULTRA (minimax + heuristique)
# ────────────────────────────────────────────────────────────────────────────────
def score_position(board, token):
    score = 0
    center = COLS // 2

    # centre bonus
    for r in range(ROWS):
        if board[r][center] == token:
            score += 3

    return score


def minimax(board, depth, alpha, beta, maximizing, token, enemy):
    valid = available_cols(board)

    if depth == 0 or not valid:
        return score_position(board, token), None

    if maximizing:
        best_score = -999999
        best_col = random.choice(valid)

        for col in valid:
            temp = copy.deepcopy(board)
            drop_token(temp, col, token)

            if check_win(temp, token):
                return 100000, col

            score, _ = minimax(temp, depth-1, alpha, beta, False, token, enemy)

            if score > best_score:
                best_score = score
                best_col = col

            alpha = max(alpha, score)
            if beta <= alpha:
                break

        return best_score, best_col

    else:
        best_score = 999999
        best_col = random.choice(valid)

        for col in valid:
            temp = copy.deepcopy(board)
            drop_token(temp, col, enemy)

            if check_win(temp, enemy):
                return -100000, col

            score, _ = minimax(temp, depth-1, alpha, beta, True, token, enemy)

            if score < best_score:
                best_score = score
                best_col = col

            beta = min(beta, score)
            if beta <= alpha:
                break

        return best_score, best_col


def bot_move(board):
    _, col = minimax(board, 3, -999999, 999999, True, TOKENS[1], TOKENS[0])
    return col if col is not None else random.choice(available_cols(board))

# ────────────────────────────────────────────────────────────────────────────────
# 🎮 VIEW
# ────────────────────────────────────────────────────────────────────────────────
class Puissance4View(View):
    def __init__(self, p1, p2=None, vs_bot=True):
        super().__init__(timeout=300)

        self.p1 = p1
        self.p2 = p2
        self.vs_bot = vs_bot

        self.board = make_board()
        self.turn = 0
        self.game_over = False
        self.message = None

        for i in range(COLS):
            self.add_item(ColumnButton(i, self))

    def current_token(self):
        return TOKENS[self.turn]

    def render(self):
        return "".join(COL_EMOJIS) + "\n" + "\n".join("".join(r) for r in self.board)

    def embed(self):
        enemy = "🤖 Bot" if self.vs_bot else self.p2.display_name
        return discord.Embed(
            title="🟡🔴 Puissance 4",
            description=f"{self.p1.display_name} vs {enemy}\n\n{self.render()}",
            color=discord.Color.gold()
        )

    async def update(self):
        if self.message and not self.game_over:
            await safe_edit(self.message, embed=self.embed(), view=self)

    # ───────────────────────────────────────────────────────────────────────────
    # 🎬 DROP ANIMATION
    # ───────────────────────────────────────────────────────────────────────────
    async def animated_drop(self, col, token):
        temp = copy.deepcopy(self.board)

        for r in range(ROWS):
            if r > 0:
                temp[r-1][col] = EMPTY
            if r < ROWS:
                temp[r][col] = token

            if self.message:
                await safe_edit(self.message, embed=self.embed(), view=self)
                await asyncio.sleep(0.05)

# ────────────────────────────────────────────────────────────────────────────────
# 🎯 GAME LOGIC
# ────────────────────────────────────────────────────────────────────────────────
    async def play(self, interaction, col):
        if self.game_over:
            return

        token = self.current_token()

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
            await asyncio.sleep(0.4)
            await self.bot_turn(interaction)

    async def bot_turn(self, interaction):
        col = bot_move(self.board)
        token = self.current_token()

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
            e.add_field(name="Résultat", value=f"🏆 {self.p1.display_name}")
        else:
            name = "🤖 Bot" if self.vs_bot else self.p2.display_name
            e.add_field(name="Résultat", value=f"🏆 {name}")

        await interaction.response.edit_message(embed=e, view=self)

# ────────────────────────────────────────────────────────────────────────────────
# 🔵 BUTTON
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

        if v.vs_bot:
            if interaction.user != v.p1:
                return await safe_respond(interaction, "Pas ton jeu", ephemeral=True)
        else:
            expected = v.p1 if v.turn == 0 else v.p2
            if interaction.user != expected:
                return await safe_respond(interaction, "Pas ton tour", ephemeral=True)

        await v.play(interaction, self.col)

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 COG
# ────────────────────────────────────────────────────────────────────────────────
class Puissance4(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="puissance4", aliases=["p4"])
    async def p4(self, ctx, mode="solo"):
        await self.start(ctx.channel, ctx.author, mode)

    async def start(self, channel, author, mode):
        if mode == "multi":
            await safe_send(channel, "Mode multi pas inclus ici (ajout possible)")
        else:
            view = Puissance4View(author, vs_bot=True)
            msg = await safe_send(channel, embed=view.embed(), view=view)
            view.message = msg

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 SETUP PRO
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Puissance4(bot)

    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Jeux"

    await bot.add_cog(cog)
