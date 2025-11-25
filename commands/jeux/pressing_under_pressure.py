# ────────────────────────────────────────────────────────────────────────────────
# 📌 pressing_under_pressure.py — Jeu Pressing Under Pressure (slash + préfixe)
# Objectif : Mini-jeu troll inspiré de The Impossible Quiz, progressif avec bouton et timer 10s
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
        green = "🟩" * max(0, int(remaining))
        white = "⬜" * max(0, int(total - remaining))
        return green + white

    # Sélection d'une énigme progressive
    def pick_puzzle(self, user_id: int):
        stage = self.progress.get(user_id, 1)
        valid = [p for p in PUZZLES if p.get("difficulty", 1) <= stage]
        return random.choice(valid) if valid else random.choice(PUZZLES) if PUZZLES else {}

    async def send_puzzle_embed(self, channel, puzzle, user):
        question = puzzle.get("question", "Énigme inconnue…")
        required_presses = puzzle.get("value", 0)  # combien de fois le joueur doit appuyer
        total_time = 10
        remaining = total_time

        # Embed initial
        embed = discord.Embed(
            title="🧠 Pressing Under Pressure !",
            description=f"**Énigme :** {question}\n\n⏳ **Temps restant :**\n{self.generate_timer(total_time, remaining)}",
            color=discord.Color.orange()
        )
        embed.set_footer(text=f"Joueur : {user.display_name}")

        # ──────────── Bouton ────────────
        class PressButton(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=total_time)
                self.press_count = 0

            @discord.ui.button(label="Appuie ici !", style=discord.ButtonStyle.green)
            async def press(self, interaction: discord.Interaction, button: discord.ui.Button):
                # Vérification d'auteur
                if interaction.user.id != user.id:
                    try:
                        await interaction.response.send_message("❌ Ce n'est pas ton bouton !", ephemeral=True)
                    except:
                        pass
                    return

                # Si la vue est déjà terminée
                if self.is_finished():
                    try:
                        await interaction.response.send_message("⏳ Trop tard — le temps est écoulé.", ephemeral=True)
                    except:
                        pass
                    return

                # Incrément et retour à l'utilisateur
                self.press_count += 1
                try:
                    await interaction.response.send_message(f"✅ Bouton pressé ! ({self.press_count})", ephemeral=True)
                except:
                    pass

        view = PressButton()

        # Envoi du message via safe_send (sécurisé)
        try:
            msg = await safe_send(channel, embed=embed, view=view)
        except Exception:
            # Ne pas planter si envoi impossible
            return False

        # Timer visuel animé (sécurisé)
        while remaining > 0 and not view.is_finished():
            await asyncio.sleep(1)
            remaining -= 1

            embed.description = f"**Énigme :** {question}\n\n⏳ **Temps restant :**\n{self.generate_timer(total_time, remaining)}"

            try:
                await msg.edit(embed=embed, view=view)
            except discord.NotFound:
                # Message supprimé -> on abandonne proprement
                return False
            except Exception:
                # Autre erreur d'édition -> on sort proprement
                break

        # Arrêt propre de la view pour éviter les interactions concurrentes
        try:
            view.stop()
        except:
            pass

        # Désactivation des boutons (pour montrer que c'est fini)
        for child in view.children:
            child.disabled = True

        # ────────────────────────────────────────────────────────────────────────────
        # Vérification finale après 10 secondes
        # ────────────────────────────────────────────────────────────────────────────
        ptype = puzzle.get("type", "")

        if ptype in ["multi_click", "click_once", "click_if_true", "click_if_confused", "timed_click", "click_any"]:
            success = (view.press_count == int(required_presses))
        elif ptype in ["no_click", "no_click_time"]:
            success = (view.press_count == 0)
        else:
            # Cas par défaut : accepter (ou traiter selon ton JSON)
            success = True

        # Mise à jour finale de l'embed
        if success:
            embed.color = discord.Color.green()
            embed.description += f"\n\n🎉 **Bravo ! Tu as appuyé {view.press_count} fois (objectif : {required_presses})**"
        else:
            embed.color = discord.Color.red()
            embed.description += f"\n\n❌ **Échec — pressions : {view.press_count} / {required_presses}**"

        try:
            await msg.edit(embed=embed, view=view)
        except discord.NotFound:
            return success
        except Exception:
            pass

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
# ────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = PressingUnderPressure(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Jeux"
    await bot.add_cog(cog)
