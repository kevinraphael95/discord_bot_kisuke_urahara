# ────────────────────────────────────────────────────────────────────────────────
# 📌 pressing_under_pressure.py — Jeu Pressing Under Pressure (slash + préfixe)
# Objectif : Mini-jeu troll inspiré de The Impossible Quiz, progressif avec bouton et timer 10s
# Catégorie : Jeux
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
import json
import random
import asyncio
from utils.discord_utils import safe_send, safe_respond  # ✅ Utilitaires sécurisés

# Chargement des énigmes
try:
    with open("data/pressing_puzzles.json", "r", encoding="utf-8") as f:
        PUZZLES = json.load(f)
except FileNotFoundError:
    PUZZLES = []

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────

class PressingUnderPressure(commands.Cog):
    """Commande /pressing et !pressing — Jeu troll Pressing Under Pressure"""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.progress = {}  # stock progression par utilisateur

    # Génération d’un timer visuel
    def generate_timer(self, total=10, remaining=10):
        green = "🟩" * remaining
        white = "⬜" * (total - remaining)
        return green + white

    # Sélection d'une énigme progressive
    def pick_puzzle(self, user_id: int):
        stage = self.progress.get(user_id, 1)
        valid = [p for p in PUZZLES if p.get("difficulty", 1) <= stage]
        return random.choice(valid) if valid else random.choice(PUZZLES)

    async def send_puzzle_embed(self, channel, puzzle, user):
        question = puzzle.get("question", "Énigme inconnue…")
        required_presses = puzzle.get("press_count", 1)  # nombre de fois que le joueur doit appuyer
        total_time = 10
        remaining = total_time

        # Embed initial
        embed = discord.Embed(
            title="🧠 Pressing Under Pressure !",
            description=f"**Énigme :** {question}\n\n⏳ **Temps restant :**\n{self.generate_timer(total_time, remaining)}\n\nAppuie {required_presses} fois sur le bouton !",
            color=discord.Color.orange()
        )
        embed.set_footer(text=f"Joueur : {user.display_name}")

        # ──────────── Bouton ────────────
        class PressButton(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=total_time)
                self.press_count = 0

            @discord.ui.button(label="Appuie ici !", style=discord.ButtonStyle.green)
            async def press(self, button: discord.ui.Button, interaction_: discord.Interaction):
                if interaction_.user.id != user.id:
                    await interaction_.response.send_message("❌ Ce n'est pas ton bouton !", ephemeral=True)
                    return
                self.press_count += 1
                await interaction_.response.send_message(f"✅ Bouton pressé ! ({self.press_count}/{required_presses})", ephemeral=True)

        view = PressButton()
        msg = await channel.send(embed=embed, view=view)

        # Timer visuel animé
        while remaining > 0:
            await asyncio.sleep(1)
            remaining -= 1
            embed.description = f"**Énigme :** {question}\n\n⏳ **Temps restant :**\n{self.generate_timer(total_time, remaining)}\n\nAppuie {required_presses} fois sur le bouton !"
            await msg.edit(embed=embed, view=view)

        # Vérification finale après 10 secondes
        if view.press_count >= required_presses:
            embed.color = discord.Color.green()
            embed.description += f"\n\n🎉 **Bravo ! Tu as appuyé {view.press_count} fois et réussi l’énigme !**"
            success = True
        else:
            embed.color = discord.Color.red()
            embed.description += f"\n\n❌ **Trop peu de pressions ({view.press_count}/{required_presses}) ! Tu as échoué…**"
            success = False

        await msg.edit(embed=embed, view=None)
        return success

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="pressing",
        description="Lance le jeu Pressing Under Pressure !"
    )
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_pressing(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        if not PUZZLES:
            return await safe_respond(interaction, "❌ Aucune énigme trouvée dans le JSON.")
        puzzle = self.pick_puzzle(user_id)
        await interaction.response.defer()  # Pas de message immédiat
        result = await self.send_puzzle_embed(interaction.channel, puzzle, interaction.user)
        if result:
            self.progress[user_id] = self.progress.get(user_id, 1) + 1

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="pressing", aliases=["pup"])
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_pressing(self, ctx: commands.Context):
        user_id = ctx.author.id
        if not PUZZLES:
            return await safe_send(ctx.channel, "❌ Aucune énigme trouvée dans le JSON.")
        puzzle = self.pick_puzzle(user_id)
        result = await self.send_puzzle_embed(ctx.channel, puzzle, ctx.author)
        if result:
            self.progress[user_id] = self.progress.get(user_id, 1) + 1

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = PressingUnderPressure(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Jeux"
    await bot.add_cog(cog)



