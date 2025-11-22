# ────────────────────────────────────────────────────────────────────────────────
# 📌 bleach_quiz.py — Commande /bleach_quiz et !bleach_quiz
# Objectif : Quiz Bleach mode survie : 3 questions faciles, 3 moyennes, 3 difficiles
# Catégorie : Bleach
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands, ui
from discord.ext import commands
import random, json, os, unicodedata
from utils.discord_utils import safe_send, safe_respond

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class BleachQuiz(commands.Cog):
    """Commande /bleach_quiz et !bleach_quiz — Quiz Bleach mode survie"""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        path = os.path.join("data", "bleach_quiz.json")
        with open(path, "r", encoding="utf-8") as f:
            self.quiz_data = json.load(f)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Normaliser la réponse
    # ────────────────────────────────────────────────────────────────────────────
    def normalize_answer(self, text: str):
        norm = unicodedata.normalize("NFD", text.lower())
        return "".join(c for c in norm if unicodedata.category(c) != "Mn").strip()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Modal pour la réponse
    # ────────────────────────────────────────────────────────────────────────────
    class AnswerModal(ui.Modal):
        def __init__(self, question_data, parent):
            super().__init__(title="💬 Réponds à la question")
            self.question_data = question_data
            self.parent = parent
            self.add_item(ui.TextInput(label="Ta réponse", placeholder="Tape ta réponse ici...", required=True, max_length=100))

        async def on_submit(self, interaction: discord.Interaction):
            user_answer = self.parent.normalize_answer(self.children[0].value)
            correct_answers = [self.parent.normalize_answer(a) for a in self.question_data["answers"]]
            if user_answer in correct_answers:
                self.parent.modal_result = True
                await interaction.response.send_message("✅ Correct !", ephemeral=True)
            else:
                self.parent.modal_result = False
                await interaction.response.send_message(f"❌ Faux ! La bonne réponse était : {self.question_data['answers'][0]}", ephemeral=True)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Poser une question dans l'embed unique
    # ────────────────────────────────────────────────────────────────────────────
    async def ask_question_modal(self, embed_msg, question_data):
        view = ui.View()
        view.add_item(ui.Button(label="Répondre", style=discord.ButtonStyle.primary, custom_id="answer_btn"))

        # Mettre à jour l'embed pour la question courante
        embed_msg.title = f"💠 Question : {question_data['question']}"
        embed_msg.description = "\n".join(f"{i+1}. {opt}" for i, opt in enumerate(question_data["options"]))
        await embed_msg.edit(embed=embed_msg, view=view)

        def check(i):
            return i.user.id == embed_msg.interaction.user.id if hasattr(embed_msg, "interaction") else True and i.data.get("custom_id") == "answer_btn"

        try:
            interaction = await self.bot.wait_for("interaction", check=check, timeout=60)
            modal = self.AnswerModal(question_data, self)
            self.modal_result = None
            await interaction.response.send_modal(modal)

            while self.modal_result is None:
                await discord.utils.sleep_until(discord.utils.utcnow() + discord.utils.timedelta(milliseconds=100))
            return self.modal_result
        except:
            await safe_send(embed_msg.channel, f"⏱ Temps écoulé ! La bonne réponse était : {question_data['answers'][0]}")
            return False

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Mode survie
    # ────────────────────────────────────────────────────────────────────────────
    async def run_survival_quiz(self, ctx_or_interaction):
        embed = discord.Embed(title="📝 Quiz mode survie", description="Répondez aux questions via le bouton ci-dessous.", color=0x00ffcc)
        msg = await safe_send(ctx_or_interaction, embed=embed)

        levels = ["easy", "medium", "hard"]
        for level in levels:
            questions = random.sample(self.quiz_data.get(level, []), k=min(3, len(self.quiz_data.get(level, []))))
            for q in questions:
                correct = await self.ask_question_modal(msg, q)
                if not correct:
                    embed.description = "💥 Vous avez échoué ! Le quiz s'arrête ici."
                    await msg.edit(embed=embed, view=None)
                    return
        embed.description = "🏆 Félicitations ! Vous avez terminé le quiz survie sans erreur !"
        await msg.edit(embed=embed, view=None)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="bleach_quiz",
        description="Quiz Bleach mode survie : répondez correctement à toutes les questions"
    )
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_bleach_quiz(self, interaction: discord.Interaction):
        await safe_respond(interaction, "📝 Quiz mode survie commencé !")
        await self.run_survival_quiz(interaction)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="bleach_quiz")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_bleach_quiz(self, ctx: commands.Context):
        await safe_send(ctx.channel, "📝 Quiz mode survie commencé !")
        await self.run_survival_quiz(ctx)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = BleachQuiz(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Bleach"
    await bot.add_cog(cog)
