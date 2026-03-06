# ────────────────────────────────────────────────────────────────────────────────
# 📌 division.py — Commande interactive /division et !division
# Objectif : Déterminer ta division dans le Gotei 13 via un QCM avec boutons
# Catégorie : Bleach
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import json
import logging
import os
import random
from collections import Counter

import discord
from discord import app_commands
from discord.ext import commands

from utils.discord_utils import safe_send, safe_edit, safe_interact
from utils.init_db import get_conn

log = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────────────────────────
# 📂 Chargement des données JSON
# ────────────────────────────────────────────────────────────────────────────────
DATA_JSON_PATH = os.path.join("data", "divisions_quiz.json")

def load_division_data() -> dict:
    """Charge les questions et divisions depuis le fichier JSON."""
    try:
        with open(DATA_JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log.exception("[division] Impossible de charger %s : %s", DATA_JSON_PATH, e)
        return {}

# ────────────────────────────────────────────────────────────────────────────────
# 🗄️ Accès base de données locale
# ────────────────────────────────────────────────────────────────────────────────

def db_valider_quete(user_id: int) -> int | None:
    """
    Vérifie si la quête 'division' est déjà validée pour l'utilisateur.
    Si non, l'ajoute et incrémente le niveau.
    Retourne le nouveau niveau si la quête vient d'être validée, sinon None.
    """
    try:
        conn   = get_conn()
        cursor = conn.cursor()

        cursor.execute("SELECT quetes, niveau FROM reiatsu WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()

        if not row:
            conn.close()
            return None

        quetes = json.loads(row[0] or "[]")
        niveau = row[1] or 1

        if "division" in quetes:
            conn.close()
            return None

        quetes.append("division")
        new_lvl = niveau + 1
        cursor.execute(
            "UPDATE reiatsu SET quetes = ?, niveau = ? WHERE user_id = ?",
            (json.dumps(quetes), new_lvl, user_id)
        )
        conn.commit()
        conn.close()
        return new_lvl

    except Exception as e:
        log.exception("[division] Erreur validation quête SQLite : %s", e)
        return None

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ UI — Vue interactive pour les questions (A/B/C/D)
# ────────────────────────────────────────────────────────────────────────────────

class QuizView(discord.ui.View):
    def __init__(self, answers: list, author: discord.User | discord.Member, timeout: int = 60):
        super().__init__(timeout=timeout)
        self.author          = author
        self.selected_traits = None

        emojis = ["🇦", "🇧", "🇨", "🇩"]
        for idx, (_, traits) in enumerate(answers):
            self.add_item(QuizButton(emojis[idx], traits))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.author.id


class QuizButton(discord.ui.Button):
    def __init__(self, emoji: str, traits: list):
        super().__init__(emoji=emoji, style=discord.ButtonStyle.primary)
        self.traits = traits

    async def callback(self, interaction: discord.Interaction):
        view: QuizView = self.view
        view.selected_traits = self.traits
        for child in view.children:
            child.disabled = True
        await safe_interact(interaction, view=view, edit=True)
        view.stop()

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────

class Division(commands.Cog):
    """Commandes /division et !division — Détermine ta division dans le Gotei 13."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonctions internes communes
    # ────────────────────────────────────────────────────────────────────────────
    async def _valider_quete(self, user: discord.User | discord.Member, channel: discord.abc.Messageable | None = None):
        """Valide la quête 'division' et envoie un embed de félicitations si nécessaire."""
        new_lvl = db_valider_quete(user.id)
        if new_lvl is None:
            return

        embed = discord.Embed(
            title="🎉 Quête accomplie !",
            description=(
                f"Bravo **{user.display_name}** ! Tu as terminé la quête **Division** 🏆\n\n"
                f"⭐ **Niveau +1 !** (Niveau {new_lvl})"
            ),
            color=0x1E90FF
        )
        await safe_send(channel if channel else user, embed=embed)

    async def _run_quiz(self, channel: discord.abc.Messageable, author: discord.User | discord.Member):
        """Déroulement complet du quiz de division."""
        data = load_division_data()
        if not data:
            await safe_send(channel, "❌ Données introuvables.")
            return

        all_questions       = data["questions"]
        divisions           = data["divisions"]
        personality_counter = Counter()
        questions           = random.sample(all_questions, k=10)
        message             = None
        emojis              = ["🇦", "🇧", "🇨", "🇩"]

        for q_index, q in enumerate(questions, start=1):
            all_answers      = list(q["answers"].items())
            selected_answers = random.sample(all_answers, min(4, len(all_answers)))

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

        # ─── Résultat final ───
        division_scores = {
            div: sum(personality_counter[trait] for trait in info["traits"])
            for div, info in divisions.items()
        }
        best_division = max(division_scores, key=division_scores.get)
        div_info      = divisions[best_division]

        embed_result = discord.Embed(
            title="🧩 Résultat de ton test",
            description=f"Tu serais dans la **{best_division}** !\n\n{div_info['description']}",
            color=discord.Color.green()
        )
        embed_result.set_image(url=f"attachment://{os.path.basename(div_info['image'])}")

        await safe_edit(message, embed=embed_result, view=None)
        await self._valider_quete(author, channel=channel)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(name="division",description="Réponds à un QCM pour savoir dans quelle division du Gotei 13 tu serais.")
    @app_commands.checks.cooldown(rate=1, per=5.0, key=lambda i: i.user.id)
    async def slash_division(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self._run_quiz(interaction.channel, interaction.user)
        await interaction.delete_original_response()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="division",help="Détermine ta division dans le Gotei 13.")
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
