# ────────────────────────────────────────────────────────────────────────────────
# 📌 tram_probleme.py — Commande /tram_probleme et !tram_probleme
# Objectif : Quiz interactif du dilemme du tramway avec bouton "Commencer" et "Continuer"
# Catégorie : Fun
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
from utils.discord_utils import safe_send, safe_respond, safe_edit
import json
import random
import os

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class TramProbleme(commands.Cog):
    """Commande /tram_probleme et !tram_probleme — Quiz du dilemme du tramway"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.questions_path = os.path.join("data", "tram_questions.json")

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Chargement du JSON
    # ────────────────────────────────────────────────────────────────────────────
    def load_questions(self):
        try:
            with open(self.questions_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("questions", [])
        except Exception as e:
            print(f"[ERREUR JSON] {e}")
            return []

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="tram_probleme",
        description="Teste ta morale dans un quiz absurde du dilemme du tramway."
    )
    @app_commands.describe(story="Active le mode histoire complète (enchaînement total des questions).")
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_tram_probleme(self, interaction: discord.Interaction, story: bool = False):
        await self.run_tram_quiz(interaction, story)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="tram_probleme", aliases=["tp"])
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_tram_probleme(self, ctx: commands.Context, *args):
        story = any(arg.lower() in ["story", "histoire", "mode_story"] for arg in args)
        await self.run_tram_quiz(ctx, story)

    # ────────────────────────────────────────────────────────────────────────────
    # 🎮 Fonction principale
    # ────────────────────────────────────────────────────────────────────────────
    async def run_tram_quiz(self, ctx_or_inter, story: bool = False):
        is_inter = isinstance(ctx_or_inter, discord.Interaction)
        send = safe_respond if is_inter else safe_send
        edit = safe_edit

        questions = self.load_questions()
        if not questions:
            await send(ctx_or_inter, "❌ Aucune question trouvée dans le JSON.")
            return

        if not story:
            random.shuffle(questions)

        utilitarisme = 0
        deontologie = 0
        total_saved = {"humain": 0, "enfant": 0, "pa": 0, "animal": 0, "robot": 0}
        total_killed = {"humain": 0, "enfant": 0, "pa": 0, "animal": 0, "robot": 0}

        # ──────────────────────────────────────────────────────────────
        # Message d’intro avec bouton "Commencer"
        # ──────────────────────────────────────────────────────────────
        embed = discord.Embed(
            title="🚋 Dilemme du Tramway",
            description=(
                "Bienvenue dans le test moral ultime.\n"
                "Tu devras faire des choix... difficiles.\n\n"
                f"🧩 Mode story : {'✅ Activé (ordre fixe)' if story else '❌ Désactivé (aléatoire)'}\n\n"
                "Appuie sur **▶️ Commencer** quand tu es prêt."
            ),
            color=discord.Color.orange()
        )

        view_start = discord.ui.View(timeout=60)
        started = False

        async def start_callback(interaction):
            nonlocal started
            started = True
            await interaction.response.defer()
            view_start.stop()

        start_button = discord.ui.Button(label="▶️ Commencer", style=discord.ButtonStyle.green)
        start_button.callback = start_callback
        view_start.add_item(start_button)

        msg = await send(ctx_or_inter, embed=embed, view=view_start)
        await view_start.wait()

        if not started:
            embed.description = "⛔ Le tram s’arrête... tu n’as pas pris le départ à temps."
            embed.color = discord.Color.red()
            await edit(msg, embed=embed, view=None)
            return

        # ──────────────────────────────────────────────────────────────
        # Boucle des questions avec timeout pour tous les modes
        # ──────────────────────────────────────────────────────────────
        total_q = len(questions) if story else min(5, len(questions))

        for i, question in enumerate(questions[:total_q], start=1):
            embed.title = f"🚨 Question {i}/{total_q}"
            embed.description = question["question"]
            embed.clear_fields()
            embed.color = discord.Color.orange()
            embed.set_footer(text="Fais ton choix moral... ou pas 😈")

            view = discord.ui.View(timeout=60)
            answered = False
            next_question = False

            for option in question["options"]:
                button = discord.ui.Button(label=option["text"], style=discord.ButtonStyle.primary)

                async def button_callback(interaction, choice=option):
                    nonlocal utilitarisme, deontologie, answered, next_question
                    answered = True

                    result = choice.get("result", "🤔 Choix étrange...")
                    ethics = choice.get("ethics")

                    if ethics == "utilitarisme":
                        utilitarisme += 1
                    elif ethics == "déontologie":
                        deontologie += 1

                    for key in total_saved:
                        total_saved[key] += choice.get("saved", {}).get(key, 0)
                        total_killed[key] += choice.get("killed", {}).get(key, 0)

                    embed.add_field(name="🧠 Ton choix", value=f"**{choice['text']}**\n{result}", inline=False)
                    embed.set_footer(text="Appuie sur ➡️ Continuer pour passer à la suite.")
                    await edit(msg, embed=embed, view=None)
                    await interaction.response.defer()

                    # Bouton "Continuer"
                    view_continue = discord.ui.View(timeout=60)

                    async def continue_callback(inter2):
                        nonlocal next_question
                        next_question = True
                        await inter2.response.defer()
                        view_continue.stop()

                    cont_btn = discord.ui.Button(label="➡️ Continuer", style=discord.ButtonStyle.green)
                    cont_btn.callback = continue_callback
                    view_continue.add_item(cont_btn)
                    await edit(msg, embed=embed, view=view_continue)
                    await view_continue.wait()
                    view.stop()

                button.callback = button_callback
                view.add_item(button)

            await edit(msg, embed=embed, view=view)
            await view.wait()

            if not answered:
                embed.description = "⛔ Le tram s’arrête... tu n’as pas répondu à temps."
                embed.color = discord.Color.red()
                await edit(msg, embed=embed, view=None)
                return

            if not next_question:
                embed.description = "🚋 Le tram s’arrête... tu n’as pas continué à temps."
                embed.color = discord.Color.red()
                await edit(msg, embed=embed, view=None)
                return

        # ──────────────────────────────────────────────────────────────
        # Résultats finaux
        # ──────────────────────────────────────────────────────────────
        embed = discord.Embed(
            title="🎉 Résultats du Dilemme du Tramway",
            color=discord.Color.green()
        )
        embed.add_field(
            name="⚖️ Équilibre éthique",
            value=f"Utilitarisme : {utilitarisme}\nDéontologie : {deontologie}",
            inline=False
        )

        if utilitarisme > deontologie:
            profil = "Tu es plutôt **utilitariste** – tu cherches à maximiser le bien global, quitte à te salir les mains. 🤔"
        elif deontologie > utilitarisme:
            profil = "Tu es plutôt **déontologique** – tu respectes les principes moraux, même face au chaos. 🧘"
        else:
            profil = "Ton équilibre moral est parfait : un tram entre la raison et la règle. ⚖️🚋"

        embed.add_field(name="🧭 Profil moral", value=profil, inline=False)

        saved = (
            f"🕊️ **Tu as sauvé :** {total_saved['humain']} adultes, "
            f"{total_saved['enfant']} enfants, {total_saved['pa']} personnes âgées, "
            f"{total_saved['animal']} animaux et {total_saved['robot']} robots."
        )
        killed = (
            f"💀 **Tu as tué :** {total_killed['humain']} adultes, "
            f"{total_killed['enfant']} enfants, {total_killed['pa']} personnes âgées, "
            f"{total_killed['animal']} animaux et {total_killed['robot']} robots."
        )

        embed.add_field(name="📊 Bilan moral", value=f"{saved}\n{killed}", inline=False)
        embed.set_footer(text="Fin du test moral 🛤️")

        await edit(msg, embed=embed, view=None)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = TramProbleme(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Jeux"
    await bot.add_cog(cog)
