# ────────────────────────────────────────────────────────────────────────────────
# 📌 pressing_under_pressure.py — Jeu Pressing Under Pressure (slash + préfixe)
# Objectif : Mini-jeu troll inspiré de The Impossible Quiz, énigmes aléatoires
# Catégorie : Jeux
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

import discord
from discord import app_commands
from discord.ext import commands
import json
import random
import asyncio
from utils.discord_utils import safe_send, safe_respond

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
        self.progress = {}

    def generate_timer(self, total=10, remaining=10):
        green = "🟩" * max(0, int(remaining))
        white = "⬜" * max(0, int(total - remaining))
        return green + white

    # ────────────────────────────────────────────────────────────────────────────
    # Envoi d’une énigme avec bouton
    # ────────────────────────────────────────────────────────────────────────────
    async def send_puzzle_embed(self, channel, puzzle, user):
        question = puzzle.get("question", "Énigme inconnue…")
        required_presses = puzzle.get("value", 0)
        total_time = 10
        remaining = total_time

        embed = discord.Embed(
            title="🧠 Pressing Under Pressure !",
            description=f"**Énigme :** {question}\n\n⏳ Temps restant :\n{self.generate_timer(total_time, remaining)}",
            color=discord.Color.orange()
        )
        embed.set_footer(text=f"Joueur : {user.display_name}")

        class PressButton(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=total_time)
                self.press_count = 0

            @discord.ui.button(label="Appuie ici !", style=discord.ButtonStyle.green)
            async def press(self, interaction: discord.Interaction, button: discord.ui.Button):
                if interaction.user.id != user.id:
                    try:
                        await interaction.response.send_message("❌ Ce n'est pas ton bouton !", ephemeral=True)
                    except: pass
                    return
                if self.is_finished():
                    try:
                        await interaction.response.send_message("⏳ Trop tard — le temps est écoulé.", ephemeral=True)
                    except: pass
                    return
                self.press_count += 1
                try:
                    await interaction.response.send_message(f"✅ Bouton pressé ! ({self.press_count})", ephemeral=True)
                except: pass

        view = PressButton()
        try:
            msg = await safe_send(channel, embed=embed, view=view)
        except: return False

        while remaining > 0 and not view.is_finished():
            await asyncio.sleep(1)
            remaining -= 1
            embed.description = f"**Énigme :** {question}\n\n⏳ Temps restant :\n{self.generate_timer(total_time, remaining)}"
            try:
                await msg.edit(embed=embed, view=view)
            except: break

        try:
            view.stop()
            for child in view.children:
                child.disabled = True
        except: pass

        # Vérification finale
        ptype = puzzle.get("type", "")
        if ptype in ["multi_click", "click_once", "click_if_true", "click_if_confused", "timed_click", "click_any"]:
            success = (view.press_count == int(required_presses))
        elif ptype in ["no_click", "no_click_time"]:
            success = (view.press_count == 0)
        else:
            success = True

        if success:
            embed.color = discord.Color.green()
            embed.description += f"\n\n🎉 Bravo ! Pressions : {view.press_count} (objectif : {required_presses})"
        else:
            embed.color = discord.Color.red()
            embed.description += f"\n\n❌ Échec — pressions : {view.press_count} / {required_presses}"

        try:
            await msg.edit(embed=embed, view=view)
        except: pass

        return success

    # ────────────────────────────────────────────────────────────────────────────
    # Jouer plusieurs énigmes à la suite avec ordre aléatoire
    # ────────────────────────────────────────────────────────────────────────────
    async def run_full_game(self, channel, user):
        # Regrouper les énigmes par difficulté
        puzzles_by_diff = {1: [], 2: [], 3: []}
        for p in PUZZLES:
            diff = p.get("difficulty", 1)
            if diff in puzzles_by_diff:
                puzzles_by_diff[diff].append(p)

        # Prendre la moitié des énigmes par difficulté
        selected = []
        for diff, puzzles in puzzles_by_diff.items():
            count = max(1, len(puzzles)//2)
            selected += random.sample(puzzles, count)  # tirage aléatoire

        # Mélanger toutes les énigmes sélectionnées
        random.shuffle(selected)

        # Enchaînement des énigmes
        for puzzle in selected:
            success = await self.send_puzzle_embed(channel, puzzle, user)
            if not success:
                await safe_send(channel, f"❌ Tu as échoué à l’énigme {puzzle.get('id')}… Jeu terminé !")
                return False

        # Toutes réussies
        await safe_send(channel, f"🏆 Félicitations {user.display_name} ! Tu as réussi toutes les énigmes !")
        return True

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="pressing",
        description="Lance le jeu Pressing Under Pressure !"
    )
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_pressing(self, interaction: discord.Interaction):
        if not PUZZLES:
            return await safe_respond(interaction, "❌ Aucune énigme trouvée dans le JSON.")
        await interaction.response.defer()
        await self.run_full_game(interaction.channel, interaction.user)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="pressing", aliases=["pup"])
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_pressing(self, ctx: commands.Context):
        if not PUZZLES:
            return await safe_send(ctx.channel, "❌ Aucune énigme trouvée dans le JSON.")
        await self.run_full_game(ctx.channel, ctx.author)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = PressingUnderPressure(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Jeux"
    await bot.add_cog(cog)



