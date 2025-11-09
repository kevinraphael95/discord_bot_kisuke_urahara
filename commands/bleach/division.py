# ────────────────────────────────────────────────────────────────────────────────
# 📌 division.py — Commande interactive /division et !division
# Objectif : Déterminer ta division dans le Gotei 13 via un QCM avec boutons
# Catégorie : Bleach
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# Version : ✅ Optimisée + intègre la quête "division"
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import asyncio
import random
from collections import Counter
from utils.discord_utils import safe_send, safe_edit, safe_respond
from utils.supabase_client import supabase  # ✅ pour accès à la base

# ────────────────────────────────────────────────────────────────────────────────
# 📂 Chargement des données JSON
# ────────────────────────────────────────────────────────────────────────────────
DATA_JSON_PATH = os.path.join("data", "divisions_quiz.json")

def load_division_data():
    try:
        with open(DATA_JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERREUR JSON] Impossible de charger {DATA_JSON_PATH} : {e}")
        return {}

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Vue interactive pour les questions (A/B/C/D)
# ────────────────────────────────────────────────────────────────────────────────
class QuizView(discord.ui.View):
    def __init__(self, answers, author, timeout=60):
        super().__init__(timeout=timeout)
        self.author = author
        self.selected_traits = None

        emojis = ["🇦", "🇧", "🇨", "🇩"]
        for idx, (_, traits) in enumerate(answers):
            self.add_item(QuizButton(emojis[idx], traits))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.author.id

class QuizButton(discord.ui.Button):
    def __init__(self, emoji, traits):
        super().__init__(emoji=emoji, style=discord.ButtonStyle.primary)
        self.traits = traits

    async def callback(self, interaction: discord.Interaction):
        view: QuizView = self.view
        view.selected_traits = self.traits
        for child in view.children:
            child.disabled = True
        await interaction.response.edit_message(view=view)
        view.stop()

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class Division(commands.Cog):
    """Commande /division et !division — Détermine ta division dans le Gotei 13"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # ⚙️ Validation de la quête division
    # ────────────────────────────────────────────────────────────────────────────
    async def valider_quete_division(self, user: discord.User, channel: discord.abc.Messageable | None = None):
        try:
            data = supabase.table("reiatsu").select("quetes, niveau").eq("user_id", user.id).execute()
            if not data.data:
                return

            quetes = data.data[0].get("quetes", [])
            niveau = data.data[0].get("niveau", 1)

            if "division" in quetes:
                return

            quetes.append("division")
            new_lvl = niveau + 1
            supabase.table("reiatsu").update({"quetes": quetes, "niveau": new_lvl}).eq("user_id", user.id).execute()

            embed = discord.Embed(
                title="🎉 Quête accomplie !",
                description=f"Bravo **{user.name}** ! Tu as terminé la quête **Division** 🏆\n\n⭐ **Niveau +1 !** (Niveau {new_lvl})",
                color=0x1E90FF
            )

            if channel:
                await safe_send(channel, embed=embed)
            else:
                await safe_send(user, embed=embed)

        except Exception as e:
            print(f"[ERREUR validation quête division] {e}")

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction interne commune
    # ────────────────────────────────────────────────────────────────────────────
    async def _run_quiz(self, channel, author):
        data = load_division_data()
        if not data:
            await safe_send(channel, "❌ Données introuvables.")
            return

        all_questions = data["questions"]
        divisions = data["divisions"]
        personality_counter = Counter()

        # Tirer 10 questions aléatoires
        questions = random.sample(all_questions, k=10)
        message = None

        for q_index, q in enumerate(questions, start=1):
            all_answers = list(q["answers"].items())
            selected_answers = random.sample(all_answers, min(4, len(all_answers)))

            emojis = ["🇦", "🇧", "🇨", "🇩"]
            embed = discord.Embed(
                title=f"🧠 Test de division — Question {q_index}/10",
                description=f"**{q['question']}**\n\n" + "\n".join(
                    f"{emojis[idx]} {ans}" for idx, (ans, _) in enumerate(selected_answers)
                ),
                color=discord.Color.orange()
            )

            view = QuizView(selected_answers, author)

            if message is None:
                message = await safe_send(channel, embed=embed, view=view)
            else:
                await safe_edit(message, embed=embed, view=view)

            await view.wait()

            if view.selected_traits is None:
                await safe_edit(message, content="⏱️ Temps écoulé. Test annulé.", embed=None, view=None)
                return

            personality_counter.update(view.selected_traits)

        # Résultat final
        division_scores = {
            div: sum(personality_counter[trait] for trait in info["traits"])
            for div, info in divisions.items()
        }
        best_division = max(division_scores, key=division_scores.get)
        div_info = divisions[best_division]

        embed_result = discord.Embed(
            title="🧩 Résultat de ton test",
            description=f"Tu serais dans la **{best_division}** !\n\n{div_info['description']}",
            color=discord.Color.green()
        )
        embed_result.set_image(url=f"attachment://{os.path.basename(div_info['image'])}")

        await safe_edit(message, embed=embed_result, view=None)

        # ✅ Validation de la quête dans le salon
        await self.valider_quete_division(author, channel=channel)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="division",
        description="Réponds à un QCM pour savoir dans quelle division du Gotei 13 tu serais."
    )
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_division(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self._run_quiz(interaction.channel, interaction.user)
        await interaction.delete_original_response()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="division", help="Détermine ta division dans le Gotei 13")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_division(self, ctx: commands.Context):
        await self._run_quiz(ctx.channel, ctx.author)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Division(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Bleach"
    await bot.add_cog(cog)
