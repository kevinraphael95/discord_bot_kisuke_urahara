# ────────────────────────────────────────────────────────────────────────────────
# 📌 tram_probleme.py — Commande /tram_probleme et !tram_probleme
# Objectif : Quiz interactif du dilemme du tramway avec choix du mode (court / complet)
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

        # ⚡ Charge le JSON une fois au démarrage
        self.questions = self.load_questions()

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
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_tram_probleme(self, interaction: discord.Interaction):
        await self.run_tram_quiz(interaction)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="tram_probleme", aliases=["tp"], help="Teste ta morale dans un quiz absurde du dilemme du tramway.")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_tram_probleme(self, ctx: commands.Context):
        await self.run_tram_quiz(ctx)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔧 Helper : récupère l'id de l'auteur, que ce soit un ctx ou une interaction
    # ────────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _author_id(ctx_or_inter):
        if isinstance(ctx_or_inter, discord.Interaction):
            return ctx_or_inter.user.id
        return ctx_or_inter.author.id

    # ────────────────────────────────────────────────────────────────────────────
    # 🎮 Fonction principale
    # ────────────────────────────────────────────────────────────────────────────
    async def run_tram_quiz(self, ctx_or_inter):
        is_inter = isinstance(ctx_or_inter, discord.Interaction)
        send = safe_respond if is_inter else safe_send
        edit = safe_edit
        author_id = self._author_id(ctx_or_inter)

        def is_author(interaction: discord.Interaction) -> bool:
            return interaction.user.id == author_id

        questions_all = list(self.questions)
        if not questions_all:
            await send(ctx_or_inter, "❌ Aucune question trouvée dans le JSON.")
            return

        utilitarisme = 0
        deontologie = 0
        total_saved = {"humain": 0, "enfant": 0, "pa": 0, "animal": 0, "robot": 0}
        total_killed = {"humain": 0, "enfant": 0, "pa": 0, "animal": 0, "robot": 0}

        # ──────────────────────────────────────────────────────────────
        # Message d'intro avec choix du mode
        # ──────────────────────────────────────────────────────────────
        embed = discord.Embed(
            title="🚋 Dilemme du Tramway",
            description=(
                "Bienvenue dans le test moral ultime.\n"
                "Tu devras faire des choix... difficiles.\n\n"
                "Choisis ton mode de jeu :\n"
                "🏃 **Mode court** — 5 dilemmes tirés au hasard\n"
                "📖 **Mode complet** — tous les dilemmes, dans l'ordre"
            ),
            color=discord.Color.orange()
        )

        view_start = discord.ui.View(timeout=60)
        started = False
        story = False

        async def make_start_callback(is_story: bool):
            async def _callback(interaction: discord.Interaction):
                nonlocal started, story
                if not is_author(interaction):
                    await interaction.response.send_message("❌ Ce n'est pas ton quiz !", ephemeral=True)
                    return
                started = True
                story = is_story
                try:
                    await interaction.response.defer()
                except Exception:
                    pass
                view_start.stop()
            return _callback

        short_button = discord.ui.Button(label="🏃 Mode court (5 dilemmes)", style=discord.ButtonStyle.green)
        full_button = discord.ui.Button(label="📖 Mode complet", style=discord.ButtonStyle.blurple)
        short_button.callback = await make_start_callback(False)
        full_button.callback = await make_start_callback(True)
        view_start.add_item(short_button)
        view_start.add_item(full_button)

        msg = await send(ctx_or_inter, embed=embed, view=view_start)
        await view_start.wait()

        if not started:
            embed.description = "⛔ Le tram s'arrête... tu n'as pas choisi de mode à temps."
            embed.color = discord.Color.red()
            await edit(msg, embed=embed, view=None)
            return

        # ──────────────────────────────────────────────────────────────
        # Préparation des questions selon le mode choisi
        # ──────────────────────────────────────────────────────────────
        questions = list(questions_all)
        if story:
            total_q = len(questions)
        else:
            random.shuffle(questions)
            total_q = min(5, len(questions))

        # ──────────────────────────────────────────────────────────────
        # Boucle des questions
        # ──────────────────────────────────────────────────────────────
        quiz_aborted = False

        for i, question in enumerate(questions[:total_q], start=1):
            embed.title = f"🚨 Question {i}/{total_q}"
            embed.description = question["question"]
            embed.clear_fields()
            embed.color = discord.Color.orange()
            embed.set_footer(text="Fais ton choix moral... ou pas 😈")

            answered = False
            view = discord.ui.View(timeout=60)

            for opt in question["options"]:
                button = discord.ui.Button(label=opt["text"], style=discord.ButtonStyle.primary)

                async def callback(interaction, choice=opt):
                    nonlocal utilitarisme, deontologie, answered, quiz_aborted
                    if not is_author(interaction):
                        await interaction.response.send_message("❌ Ce n'est pas ton quiz !", ephemeral=True)
                        return
                    if answered:
                        return
                    answered = True

                    # Désactive les boutons
                    for b in view.children:
                        b.disabled = True

                    try:
                        await interaction.response.defer()
                    except Exception:
                        pass

                    # Score moral
                    ethics = choice.get("ethics")
                    if ethics == "utilitarisme":
                        utilitarisme += 1
                    elif ethics == "déontologie":
                        deontologie += 1

                    # Sauvé / tué
                    for key in total_saved:
                        total_saved[key] += choice.get("saved", {}).get(key, 0)
                        total_killed[key] += choice.get("killed", {}).get(key, 0)

                    # Ajout du texte du choix
                    result = choice.get("result", "🤔 Choix étrange...")
                    embed.add_field(
                        name="🧠 Ton choix",
                        value=f"**{choice['text']}**\n{result}",
                        inline=False
                    )

                    # Bouton "Continuer" immédiatement
                    continue_view = discord.ui.View(timeout=60)
                    next_question = False

                    async def continue_callback(inter2):
                        nonlocal next_question
                        if not is_author(inter2):
                            await inter2.response.send_message("❌ Ce n'est pas ton quiz !", ephemeral=True)
                            return
                        next_question = True
                        try:
                            await inter2.response.defer()
                        except Exception:
                            pass
                        continue_view.stop()

                    cont_btn = discord.ui.Button(label="➡️ Continuer", style=discord.ButtonStyle.green)
                    cont_btn.callback = continue_callback
                    continue_view.add_item(cont_btn)

                    embed.set_footer(text="Appuie sur ➡️ Continuer pour passer à la suite.")
                    await edit(msg, embed=embed, view=continue_view)
                    await continue_view.wait()

                    if not next_question:
                        # Timeout sur le bouton "Continuer" → on arrête le quiz proprement
                        quiz_aborted = True
                        embed.set_footer(text="⛔ Temps écoulé, le tram s'arrête ici.")
                        await edit(msg, embed=embed, view=None)

                    view.stop()

                button.callback = callback
                view.add_item(button)

            await edit(msg, embed=embed, view=view)
            await view.wait()

            if not answered:
                embed.description = "⛔ Le tram s'arrête... tu n'as pas répondu à temps."
                embed.color = discord.Color.red()
                await edit(msg, embed=embed, view=None)
                return

            if quiz_aborted:
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
