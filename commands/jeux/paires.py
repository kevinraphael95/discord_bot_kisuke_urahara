# ────────────────────────────────────────────────────────────────────────────────
# 📌 memory_game.py — Jeu de paires (Memory) avec Discord
# Objectif : Jeu de memory temps réel avec emojis et thèmes
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
import random
import asyncio
from utils.discord_utils import safe_send, safe_edit

# ────────────────────────────────────────────────────────────────────────────────
# 🎨 Thèmes possibles
# ────────────────────────────────────────────────────────────────────────────────
THEMES = {
    "fruits": ["🍎","🍌","🍇","🍓","🍍","🥭","🍉","🍑"],
    "animaux": ["🐶","🐱","🐭","🐰","🦊","🐼","🦁","🐸"],
    "couleurs": ["🔴","🟢","🔵","🟡","🟣","🟠","⚫","⚪"]
}

# ────────────────────────────────────────────────────────────────────────────────
# 🧩 Memory Game View
# ────────────────────────────────────────────────────────────────────────────────
class MemoryGameView(View):
    def __init__(self, ctx_or_interaction, theme="fruits", size=4, mode="solo"):
        super().__init__(timeout=180)
        self.ctx_or_interaction = ctx_or_interaction
        self.mode = mode.lower()
        self.theme = theme if theme in THEMES else "fruits"
        self.size = size
        self.cards = THEMES[self.theme][: (size*size)//2] * 2
        random.shuffle(self.cards)
        self.board = [self.cards[i*self.size:(i+1)*self.size] for i in range(self.size)]
        self.buttons = {}
        self.flipped = []       # [(r, c, emoji)]
        self.found = set()      # positions déjà trouvées
        self.errors = {}        # erreurs par joueur
        self.scores = {}        # paires trouvées par joueur
        self.message = None     # message Discord contenant le plateau
        self.create_buttons()

    # ────────────────────────────────────────────────────────────────────────────
    # 🧱 Création des boutons
    # ────────────────────────────────────────────────────────────────────────────
    def create_buttons(self):
        for r in range(self.size):
            for c in range(self.size):
                btn = Button(label="❓", style=discord.ButtonStyle.secondary, row=r)
                btn.callback = self.make_callback(r, c)
                self.add_item(btn)
                self.buttons[(r, c)] = btn

    # ────────────────────────────────────────────────────────────────────────────
    # 🧠 Gestion du clic sur une carte
    # ────────────────────────────────────────────────────────────────────────────
    def make_callback(self, r, c):
        async def callback(interaction: discord.Interaction):
            # Mode solo : vérifier joueur
            if self.mode == "solo":
                player_id = getattr(self.ctx_or_interaction.user, "id", getattr(self.ctx_or_interaction.author, "id", None))
                if interaction.user.id != player_id:
                    await interaction.response.send_message(
                        "❌ Ce jeu est en mode **solo**, seul le joueur peut cliquer.", ephemeral=True
                    )
                    return

            pos = (r, c)
            if pos in self.found or any(pos == f[:2] for f in self.flipped):
                await interaction.response.defer()
                return

            if len(self.flipped) >= 2:
                await interaction.response.defer()
                return

            # Révéler la carte
            emoji = self.board[r][c]
            btn = self.buttons[pos]
            btn.label = emoji
            btn.style = discord.ButtonStyle.primary
            self.flipped.append((r, c, emoji))
            await safe_edit(interaction.message, view=self)

            # Vérification si deux cartes sont retournées
            if len(self.flipped) == 2:
                await asyncio.sleep(1.2)
                (r1, c1, e1), (r2, c2, e2) = self.flipped

                if e1 == e2:
                    # ✅ Paire trouvée
                    for rr, cc in [(r1, c1), (r2, c2)]:
                        self.buttons[(rr, cc)].style = discord.ButtonStyle.success
                        self.buttons[(rr, cc)].disabled = True
                    self.found.update({(r1, c1), (r2, c2)})

                    if self.mode == "multi":
                        uid = interaction.user.id
                        self.scores[uid] = self.scores.get(uid, 0) + 1

                else:
                    # ❌ Mauvaise paire
                    uid = interaction.user.id
                    self.errors[uid] = self.errors.get(uid, 0) + 1
                    for rr, cc in [(r1, c1), (r2, c2)]:
                        self.buttons[(rr, cc)].label = "❓"
                        self.buttons[(rr, cc)].style = discord.ButtonStyle.secondary

                self.flipped.clear()
                await safe_edit(interaction.message, view=self)

                # Fin de la partie
                if len(self.found) == self.size * self.size:
                    await self.end_game(interaction)

        return callback

    # ────────────────────────────────────────────────────────────────────────────
    # 🏁 Fin du jeu
    # ────────────────────────────────────────────────────────────────────────────
    async def end_game(self, interaction):
        content = ""
        if self.mode == "solo":
            player_id = getattr(self.ctx_or_interaction.user, "id", getattr(self.ctx_or_interaction.author, "id", None))
            errs = self.errors.get(player_id, 0)
            content = f"🎉 **Partie terminée !** Toutes les paires ont été trouvées.\n💡 Erreurs : **{errs}**"
        else:
            if self.scores:
                classement = sorted(self.scores.items(), key=lambda x: -x[1])
                content = "🎉 **Partie terminée ! Classement :**\n"
                for i, (uid, score) in enumerate(classement):
                    content += f"**{i+1}.** <@{uid}> — {score} paire(s)\n"
            else:
                content = "🎉 Partie terminée ! Aucune paire trouvée... 😅"

        # Désactiver tous les boutons
        for btn in self.children:
            btn.disabled = True

        await safe_edit(interaction.message, content=content, view=None)

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class MemoryGame(commands.Cog):
    """Jeu de paires Memory — Mode solo (moins d’erreurs) ou multi (plus de paires)"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def start_game(self, ctx_or_interaction, mode="solo", theme="fruits"):
        view = MemoryGameView(ctx_or_interaction, theme=theme, size=4, mode=mode)
        titre = "👤 Mode Solo" if mode == "solo" else "👥 Mode Multi"
        msg_content = f"🧩 **Memory Game — {titre}**\nThème : **{theme}**\n"
        msg_content += (
            "🎯 Objectif : Trouver toutes les paires avec le moins d’erreurs possibles !"
            if mode == "solo" else "🎯 Objectif : Faire le plus de paires possibles !"
        )
        await safe_send(
            getattr(ctx_or_interaction, "channel", ctx_or_interaction.channel),
            msg_content,
            view=view
        )

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(name="paires", description="Trouver les paires.")
    async def slash_memory(self, interaction: discord.Interaction, mode: str = "solo", theme: str = "fruits"):
        mode = "multi" if mode.lower() in ["multi", "m"] else "solo"
        await self.start_game(interaction, mode=mode, theme=theme)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="paires", help="Trouver les paires.")
    async def prefix_memory(self, ctx: commands.Context, mode: str = "solo", theme: str = "fruits"):
        mode = "multi" if mode.lower() in ["multi", "m"] else "solo"
        await self.start_game(ctx, mode=mode, theme=theme)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = MemoryGame(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Jeux"
    await bot.add_cog(cog)
