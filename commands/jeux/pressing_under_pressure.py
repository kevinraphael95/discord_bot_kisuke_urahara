# ────────────────────────────────────────────────────────────────────────────────
# 📌 pressing_under_pressure.py — Jeu Pressing Under Pressure (slash + préfixe)
# Objectif : Mini-jeu troll inspiré de The Impossible Quiz, progressif avec timer visuel + vraie validation
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
    with open("pressing_puzzles.json", "r", encoding="utf-8") as f:
        PUZZLES = json.load(f)
except FileNotFoundError:
    PUZZLES = []


# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class PressingUnderPressure(commands.Cog):
    """
    Commande /pressing et !pressing — Jeu troll Pressing Under Pressure
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.progress = {}  # stock progression par utilisateur

    # Génération d’un timer visuel
    def generate_timer(self, total=15, remaining=15):
        green = "🟩" * remaining
        white = "⬜" * (total - remaining)
        return green + white

    # Sélection d'une énigme progressive
    def pick_puzzle(self, user_id: int):
        stage = self.progress.get(user_id, 1)
        valid = [p for p in PUZZLES if p.get("difficulty", 1) <= stage]
        return random.choice(valid) if valid else random.choice(PUZZLES)

    async def evaluate_user_action(self, message, puzzle):
        """Analyse la réponse du joueur en fonction du type d’énigme"""
        ptype = puzzle.get("type", "text")

        # RÉPONSE TEXTUELLE EXACTE
        if ptype == "text":
            valid = puzzle.get("answers", [])
            if isinstance(valid, str):
                valid = [valid]
            return message.content.lower().strip() in [a.lower() for a in valid]

        # ACTION : par exemple envoyer un emoji, ping, dire un mot précis
        if ptype == "action":
            action = puzzle.get("action")
            if action == "ping_bot":
                return message.content.strip() == f"<@{message.guild.me.id}>"
            if action == "emoji":
                return any(char in puzzle.get("emojis", []) for char in message.content)
            if action == "say":
                return puzzle.get("word", "").lower() in message.content.lower()
            return False

        # NE RIEN DIRE
        if ptype == "silence":
            return False  # si un message arrive → perdu

        # ENIGME TROLL (automatique perte)
        if ptype == "fake":
            return False

        return False

    async def send_puzzle_embed(self, channel, puzzle, user):
        question = puzzle.get("question", "Énigme inconnue…")
        total_time = 15
        remaining = total_time

        embed = discord.Embed(
            title="🧠 Pressing Under Pressure !",
            description=f"**Énigme :** {question}\n\n⏳ **Temps restant :**\n{self.generate_timer(total_time, remaining)}",
            color=discord.Color.orange()
        )
        embed.set_footer(text=f"Joueur : {user.display_name}")

        msg = await channel.send(embed=embed)

        def check(m):
            return m.author.id == user.id and m.channel == channel

        user_responded = False
        user_message = None

        while remaining > 0:
            try:
                user_message = await self.bot.wait_for("message", timeout=1.0, check=check)
                user_responded = True
                break
            except asyncio.TimeoutError:
                remaining -= 1
                embed.description = f"**Énigme :** {question}\n\n⏳ **Temps restant :**\n{self.generate_timer(total_time, remaining)}"
                await msg.edit(embed=embed)

        # Fin du timer visuel
        if not user_responded and puzzle.get("type") != "silence":
            embed.description = f"**Énigme :** {question}\n\n⛔ **Temps écoulé !**"
            embed.color = discord.Color.red()
            await msg.edit(embed=embed)
            return False

        # Silence : si le joueur a parlé → défaite
        if puzzle.get("type") == "silence":
            if user_responded:
                await channel.send("❌ Tu as parlé… alors qu'il fallait **ne rien dire** !")
                return False
            await channel.send("✅ Tu as réussi ! Tu n'as rien dit.")
            return True

        # Validation classique
        success = await self.evaluate_user_action(user_message, puzzle)

        if success:
            await channel.send("🎉 **Bonne réponse !** Tu passes à l'étape suivante !")
        else:
            await channel.send("❌ **Mauvaise réponse !** Tu échoues dans la pression.")

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

        await safe_respond(interaction, "🎮 **L'énigme arrive !**")
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

        await safe_send(ctx.channel, "🎮 **L'énigme arrive !**")
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
