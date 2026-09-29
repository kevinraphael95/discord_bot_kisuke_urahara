# ================================================================================
# 📌 mot_contraint.py — Commande interactive /mot_contraint et !mot_contraint
# Objectif : Trouver un mot qui commence et se termine par les lettres données
# Catégorie : Jeux
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ================================================================================

# ================================================================================
# 📦 Imports nécessaires
# ================================================================================
import random
import discord
from discord import app_commands
from discord.ext import commands
from spellchecker import SpellChecker
from utils.discord_utils import safe_send, safe_respond, safe_edit
from utils.jeux_utils import normalize_text, parse_mode, ReplyView, BuzzerView

# ================================================================================
# 🌐 Initialisation du SpellChecker français
# ================================================================================
spell = SpellChecker(language='fr')

DICTIONARY_WORDS = [w for w in spell.word_frequency.dictionary.keys() if len(w) >= 2 and w.isalpha()]

def get_random_letter_pair() -> tuple[str, str]:
    """Tire un mot aléatoire existant et extrait sa première et dernière lettre."""
    word = random.choice(DICTIONARY_WORDS)
    return word[0].upper(), word[-1].upper()

def is_valid_word(word: str) -> bool:
    """Vérifie si le mot existe en français"""
    return word.lower() in spell.word_frequency

# ================================================================================
# 🎮 Classe de gestion de la partie (Affichage & Logique)
# ================================================================================
class MotContraintGame:
    def __init__(self, start_letter: str, end_letter: str, author_id: int, multi: bool = False, duration: int = 180):
        self.start_letter = start_letter
        self.end_letter = end_letter
        self.author_id = author_id
        self.multi = multi
        self.duration = duration
        self.finished = False
        self.winner: str | None = None
        self.last_error: str | None = None
        self.attempts: list[str] = []
        self.scores: dict[str, int] = {}  # {display_name: points}
        self.rounds = 1
        self.max_rounds = 10 if multi else 1
        self.message = None
        self.start_time = discord.utils.utcnow()

    def build_embed(self) -> discord.Embed:
        mode_text = "Mode Multijoueur" if self.multi else "Mode Solo"
        title = f"🎯 Mots Contraints - {mode_text}"

        # Visuel exact : bannière bleu foncé ANSI + Gros titre de tirage
        description = (
            f"```ansi\n\x1b[1;37;44m                  **Manche {self.rounds} / {self.max_rounds}**                  \x1b[0m\n```"
            f"# ➡️ `{self.start_letter}` _ _ _ `{self.end_letter}`\n\n"
            f"Trouvez un mot commençant par **`{self.start_letter}`** et se terminant par **`{self.end_letter}`** !"
        )

        embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Color.from_rgb(230, 100, 40)
        )

        # Champ : Essais Récents (Manche X)
        if self.attempts:
            tries_text = "\n".join(self.attempts[-4:])
            embed.add_field(name=f"Essais Récents (Manche {self.rounds}) :", value=tries_text, inline=False)
        else:
            embed.add_field(name=f"Essais Récents (Manche {self.rounds}) :", value="_Aucun essai pour l'instant_", inline=False)

        # Champ : Classement Actuel (Points) avec tirets
        if self.scores:
            sorted_scores = sorted(self.scores.items(), key=lambda x: x[1], reverse=True)
            leaderboard = "\n".join([f"- **{name}**: {pts}" for name, pts in sorted_scores])
            embed.add_field(name="🏆 Classement Actuel (Points) :", value=leaderboard, inline=False)
        else:
            embed.add_field(name="🏆 Classement Actuel (Points) :", value="_Aucun point marqué_", inline=False)

        if self.last_error and not self.finished:
            embed.add_field(name="⚠️ Remarque", value=self.last_error, inline=False)

        if self.finished:
            if self.scores:
                sorted_scores = sorted(self.scores.items(), key=lambda x: x[1], reverse=True)
                top_name, top_score = sorted_scores[0]
                embed.title = f"{title} - Terminé !"
                embed.color = discord.Color.gold()
                embed.description = f"🎉 Victoire de **{top_name}** avec **{top_score} point(s)** !"
            else:
                embed.title = f"{title} - Terminé"
                embed.color = discord.Color.red()
                embed.description = "❌ Temps écoulé, la partie s'est terminée sans aucun point."
            embed.set_footer(text="Partie terminée")
        else:
            elapsed = (discord.utils.utcnow() - self.start_time).total_seconds()
            remaining = max(0, self.duration - elapsed)
            embed.set_footer(text=f"⏳ Temps restant : {int(remaining)} secondes")

        return embed

# ================================================================================
# 🧠 Cog principal
# ================================================================================
class MotContraint(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.SOLO_TIME = 120
        self.MULTI_TIME = 180

    # ============================================================================
    # 🔹 Fonction interne commune de lancement
    # ============================================================================
    async def _start_game(self, channel: discord.abc.Messageable, author_id: int, mode: str = "solo"):
        start, end = get_random_letter_pair()
        multi = parse_mode(mode)
        duration = self.MULTI_TIME if multi else self.SOLO_TIME

        game = MotContraintGame(start, end, author_id, multi, duration)
        state = {"finished": False}

        embed = game.build_embed()

        # == Callback de validation (partagé par Solo et Multi) ==
        async def on_submit(interaction: discord.Interaction, answer: str):
            if not interaction.response.is_done():
                await interaction.response.defer()

            if state["finished"]:
                return

            if not game.multi and interaction.user.id != game.author_id:
                return

            guess = answer.strip()
            word_clean = guess.lower()
            author_name = interaction.user.display_name
            game.last_error = None

            if not word_clean:
                return

            # Vérification du mot selon les critères exacts de l'image
            if not word_clean.startswith(game.start_letter.lower()):
                reason = f"❌ Incorrect: ne commence pas par {game.start_letter}"
                game.attempts.append(f"• **{author_name}** proposed '{guess.upper()}' ({reason})")
            elif not word_clean.endswith(game.end_letter.lower()):
                reason = f"❌ Incorrect: se termine par {word_clean[-1].upper()}"
                game.attempts.append(f"• **{author_name}** proposed '{guess.upper()}' ({reason})")
            elif not is_valid_word(word_clean):
                game.attempts.append(f"• **{author_name}** proposed '{guess.upper()}' (❌ Incorrect: mot inconnu)")
            else:
                # Mot valide !
                game.scores[author_name] = game.scores.get(author_name, 0) + 1
                game.attempts.append(f"• **{author_name}** proposed '{guess.upper()}' (✅ Correct !)")

                game.rounds += 1
                if game.rounds > game.max_rounds:
                    state["finished"] = True
                    game.finished = True
                    final_embed = game.build_embed()
                    return await view.mark_finished(embed=final_embed)

                # Manche suivante
                game.start_letter, game.end_letter = get_random_letter_pair()
                game.attempts.clear()

            if game.message:
                await safe_edit(game.message, embed=game.build_embed())

        # == Création de la view selon le mode ==
        if multi:
            async def on_buzz(user: discord.User | discord.Member):
                game.attempts.append(f"• **{user.display_name}** buzzed!")
                if view.message:
                    current_embed = game.build_embed()
                    await safe_edit(view.message, embed=current_embed, view=view)

            view = BuzzerView(
                modal_title="🔔 BUZZER — Proposer un mot",
                modal_label="Mot",
                modal_placeholder=f"Mot commençant par {game.start_letter} et finissant par {game.end_letter}",
                modal_max_length=30,
                on_submit=on_submit,
                on_buzz=on_buzz,
                buzz_timeout=30,
                view_timeout=duration,
            )
        else:
            view = ReplyView(
                user_id=author_id,
                modal_title="✍️ Proposer un mot",
                modal_label="Mot",
                modal_placeholder=f"Mot commençant par {game.start_letter} et finissant par {game.end_letter}",
                modal_max_length=30,
                on_submit=on_submit,
                timeout=duration,
            )

        # Ajout du bouton règles à côté du bouton principal
        rules_btn = discord.ui.Button(label="❓ Règles", style=discord.ButtonStyle.secondary)
        async def rules_callback(interaction: discord.Interaction):
            await safe_respond(
                interaction,
                "**Règles du jeu :**\n"
                "1. Propose un mot valide de la langue française.\n"
                f"2. Il doit impérativement commencer par la première lettre demandée et finir par la seconde.\n"
                "3. En mode multijoueur, buzze pour prendre la main !",
                ephemeral=True
            )
        rules_btn.callback = rules_callback
        view.add_item(rules_btn)

        view.message = await safe_send(channel, embed=embed, view=view)
        if view.message is None:
            return
        game.message = view.message

        # == Gestion du Timeout ==
        try:
            await self.bot.wait_for("interaction", timeout=duration + 2)
        except discord.utils.wait_for.TimeoutError:
            pass

        if state["finished"]:
            return

        game.finished = True
        final_embed = game.build_embed()
        await view.mark_finished(embed=final_embed)

    # ============================================================================
    # 🔹 Commande SLASH
    # ============================================================================
    @app_commands.command(name="mot_contraint", description="Devine un mot commençant et finissant par les lettres données.")
    @app_commands.describe(mode="Tapez 'm' ou 'multi' pour le mode multijoueur (buzzer)")
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_mot_contraint(self, interaction: discord.Interaction, mode: str = "solo"):
        await interaction.response.defer()
        await self._start_game(interaction.channel, author_id=interaction.user.id, mode=mode)
        await interaction.delete_original_response()

    # ============================================================================
    # 🔹 Commande PREFIX
    # ============================================================================
    @commands.command(name="mot_contraint", aliases=["mc"], help="Devine un mot commençant et finissant par des lettres données. !mc multi pour le buzzer.")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_mot_contraint(self, ctx: commands.Context, mode: str = "solo"):
        await self._start_game(ctx.channel, author_id=ctx.author.id, mode=mode)

# ================================================================================
# 🔌 Setup du Cog
# ================================================================================
async def setup(bot: commands.Bot):
    cog = MotContraint(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Jeux"
    await bot.add_cog(cog)
