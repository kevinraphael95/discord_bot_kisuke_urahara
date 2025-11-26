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

    def generate_timer(self, total=10, remaining=10):
        green = "🟩" * max(0, int(remaining))
        white = "⬜" * max(0, int(total - remaining))
        return green + white

    # Ajouter un peu d’aléatoire automatique
    def randomize_puzzle(self, puzzle):
        p = puzzle.copy()

        # Randomisation du nombre de clics pour certains types
        if p["type"] in ["click_once", "multi_click"]:
            p["value"] = max(1, p.get("value", 1) + random.choice([-1, 0, 1]))

        # Variation aléatoire de la question
        variations = [
            " (tu crois être prêt ?)",
            " (j'espère que tu lis bien...)",
            " (ne rate pas ça.)",
            " (facile... ou pas.)",
            " (je te surveille 👀)",
        ]
        p["question"] += random.choice(variations)

        return p

    # ────────────────────────────────────────────────────────────────────────
    # Envoi + gestion d’une énigme avec embed unique
    # ────────────────────────────────────────────────────────────────────────
    async def send_puzzle_embed(self, channel, base_puzzle, user):

        puzzle = self.randomize_puzzle(base_puzzle)

        question = puzzle.get("question", "Énigme inconnue…")
        required_presses = puzzle.get("value", 0)
        total_time = 10
        remaining = total_time

        embed = discord.Embed(
            title="🧠 Pressing Under Pressure !",
            description=f"**Énigme :** {question}\n\n"
                        f"⏳ Temps restant :\n{self.generate_timer(total_time, remaining)}",
            color=discord.Color.orange()
        )
        embed.set_footer(text=f"Énigme #{puzzle.get('id')} — Joueur : {user.display_name}")

        class PressButton(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=total_time)
                self.press_count = 0

            @discord.ui.button(label="Appuie ici !", style=discord.ButtonStyle.green)
            async def press(self, interaction: discord.Interaction, button: discord.ui.Button):

                if interaction.user.id != user.id:
                    return

                self.press_count += 1

                # MAJ embed direct
                embed.description = (
                    f"**Énigme :** {question}\n\n"
                    f"👉 Pressions actuelles : **{self.press_count}**\n\n"
                    f"⏳ Temps restant :\n{self.generate_timer(total_time, remaining)}"
                )
                try:
                    await msg.edit(embed=embed, view=self)
                except:
                    pass

        view = PressButton()
        msg = await safe_send(channel, embed=embed, view=view)

        # TIMER LIVE
        while remaining > 0 and not view.is_finished():
            await asyncio.sleep(1)
            remaining -= 1

            embed.description = (
                f"**Énigme :** {question}\n\n"
                f"👉 Pressions actuelles : **{view.press_count}**\n\n"
                f"⏳ Temps restant :\n{self.generate_timer(total_time, remaining)}"
            )

            try:
                await msg.edit(embed=embed, view=view)
            except:
                break

        # Fin timer
        view.stop()
        for child in view.children:
            child.disabled = True

        # Vérification finale
        ptype = puzzle.get("type", "")
        presses = view.press_count

        if ptype in ["multi_click", "click_once"]:
            success = (presses == required_presses)

        elif ptype in ["no_click", "no_click_time"]:
            success = (presses == 0)

        elif ptype == "click_any":
            success = True

        elif ptype == "click_if_true":
            success = bool(puzzle.get("value", True))

        elif ptype == "click_if_confused":
            success = random.choice([True, False])  # troll

        else:
            success = True

        # Résultat final
        if success:
            embed.color = discord.Color.green()
            embed.add_field(name="🎉 Succès !", value=f"Pressions : **{presses}** / {required_presses}")
        else:
            embed.color = discord.Color.red()
            embed.add_field(name="❌ Échec", value=f"Pressions : **{presses}** / {required_presses}")

        await msg.edit(embed=embed, view=view)
        return success

    # ────────────────────────────────────────────────────────────────────────
    # Jeu complet : plusieurs énigmes
    # ────────────────────────────────────────────────────────────────────────
    async def run_full_game(self, channel, user):

        puzzles = PUZZLES.copy()
        random.shuffle(puzzles)

        for puzzle in puzzles:
            success = await self.send_puzzle_embed(channel, puzzle, user)
            if not success:
                await safe_send(channel, f"❌ Tu as échoué à l’énigme {puzzle['id']}…")
                return

        await safe_send(channel, f"🏆 **Félicitations {user.display_name} !** Tu as réussi toutes les énigmes !")

    # ────────────────────────────────────────────────────────────────────────
    # Commande SLASH
    # ────────────────────────────────────────────────────────────────────────
    @app_commands.command(name="pressing", description="Lance le jeu Pressing Under Pressure !")
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_pressing(self, interaction: discord.Interaction):
        if not PUZZLES:
            return await safe_respond(interaction, "❌ Aucune énigme trouvée dans le JSON.")
        await interaction.response.defer()
        await self.run_full_game(interaction.channel, interaction.user)

    # ────────────────────────────────────────────────────────────────────────
    # Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────
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




