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
from discord.ui import View, Modal, TextInput, Button
from spellchecker import SpellChecker
from utils.discord_utils import safe_send, safe_respond, safe_edit
from utils.jeux_utils import normalize_text, parse_mode, ReplyView, BuzzerView

# ================================================================================
# 🌐 Initialisation du SpellChecker français
# ================================================================================
spell = SpellChecker(language='fr')

# On extrait les mots du dictionnaire ayant au moins 2 lettres pour garantir la faisabilité
DICTIONARY_WORDS = [w for w in spell.word_frequency.dictionary.keys() if len(w) >= 2 and w.isalpha()]

def get_random_letter_pair() -> tuple[str, str]:
    """Tire un mot aléatoire existant et extrait sa première et dernière lettre."""
    # Garantit à 100% qu'une solution existe
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
        self.attempts: list[dict] = []
        self.message = None
        self.start_time = discord.utils.utcnow()

    def build_embed(self) -> discord.Embed:
        mode_text = "Multi 🌍" if self.multi else "Solo 🧍‍♂️"
        title = f"🎯 Mot Contraint - {mode_text}"
        
        # Consigne dynamique selon le mode
        if self.multi:
            instructions = "Clique sur **🔔 Buzzer** pour prendre la main."
        else:
            instructions = "Clique sur **✍️ Répondre** pour proposer ta réponse."

        embed = discord.Embed(
            title=title,
            description=(
                f"➡️ Donne un mot qui **commence par** `{self.start_letter}` "
                f"et **se termine par** `{self.end_letter}`.\n\n"
                f"💡 **Comment jouer :**\n{instructions}"
            ),
            color=discord.Color.orange()
        )

        # Affichage de l'historique des essais
        if self.attempts:
            lines = []
            for entry in self.attempts:
                status = "✅" if entry.get('correct') else "❌"
                lines.append(f"{entry['author']}: **{entry['word']}** {status}")
            tries_text = "\n".join(lines[-5:]) # Affiche les 5 derniers
            embed.add_field(name=f"Essais ({len(self.attempts)})", value=tries_text, inline=False)
        else:
            embed.add_field(name="Essais", value="*(Aucun essai pour l'instant)*", inline=False)

        # Affichage des erreurs de validation (doublons, mauvaises lettres)
        if self.last_error and not self.finished:
            embed.add_field(name="⚠️ Remarque", value=self.last_error, inline=False)

        # Gestion de l'affichage de fin de partie
        if self.finished:
            if self.winner:
                embed.title = f"{title} - Gagné !"
                embed.color = discord.Color.green()
                embed.description = f"🏆 **{self.winner}** a trouvé ! C'était bien **{self.country}**." # Exemple, adapter description
                # Correction description pour ce jeu
                embed.description = (
                    f"➡️ Mot à trouver : `{self.start_letter}...{self.end_letter}`\n\n"
                    f"🏆 **{self.winner}** a trouvé un mot valide !"
                )
            else:
                embed.title = f"{title} - Terminé"
                embed.color = discord.Color.red()
                embed.description = (
                    f"➡️ Mot à trouver : `{self.start_letter}...{self.end_letter}`\n\n"
                    f"❌ Temps écoulé, personne n'a trouvé de mot valide."
                )
            embed.set_footer(text="Partie terminée")
        else:
            # Compte à rebours
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
        # Définit les temps par défaut (2 minutes pour les deux)
        self.SOLO_TIME = 120
        self.MULTI_TIME = 120

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
            # defer() immédiat pour éviter le spam et acquitter la modal
            if not interaction.response.is_done():
                await interaction.response.defer()

            if state["finished"]:
                return

            # En solo, seul l'auteur peut répondre
            if not game.multi and interaction.user.id != game.author_id:
                return

            guess = answer.strip()
            word_clean = guess.lower()
            game.last_error = None # Reset de l'erreur précédente

            # 1. Validation de base (vide)
            if not word_clean:
                return

            # 2. Validation anti-doublon (insensible casse/accents via normalize)
            if any(normalize_text(entry['word']) == normalize_text(guess) for entry in game.attempts):
                game.last_error = f"Le mot `{guess.upper()}` a déjà été proposé !"
                if game.message:
                    await safe_edit(game.message, embed=game.build_embed())
                return

            # 3. Validation des contraintes de lettres
            if not word_clean.startswith(game.start_letter.lower()):
                game.last_error = f"Le mot doit commencer par `{game.start_letter}`."
                if game.message:
                    await safe_edit(game.message, embed=game.build_embed())
                return
                
            if not word_clean.endswith(game.end_letter.lower()):
                game.last_error = f"Le mot doit se terminer par `{game.end_letter}`."
                if game.message:
                    await safe_edit(game.message, embed=game.build_embed())
                return

            # 4. Validation du dictionnaire
            if not is_valid_word(word_clean):
                game.last_error = f"`{guess.upper()}` n'est pas reconnu comme un mot français valide."
                if game.message:
                    await safe_edit(game.message, embed=game.build_embed())
                return

            # 🔥 Tout est bon, le mot est valide
            is_correct = True # Dans ce jeu, si on passe les étapes au-dessus, c'est forcément correct
            
            game.attempts.append({
                'word': guess.upper(),
                'author': interaction.user.display_name,
                'correct': is_correct
            })

            # Victoire immédiate (1 seul mot valide suffit pour finir la partie)
            state["finished"] = True
            game.finished = True
            game.winner = interaction.user.mention

            # Mise à jour finale de l'embed
            final_embed = game.build_embed()
            # mark_finished gère la désactivation des boutons
            await view.mark_finished(embed=final_embed)

        # == Création de la view selon le mode ==
        if multi:
            # En Multi, on utilise BuzzerView de jeux_utils
            async def on_buzz(user: discord.User | discord.Member):
                # Quand quelqu'un buzze, on grise temporairement le bouton buzzer pour les autres
                if view.message:
                    for child in view.children:
                        if isinstance(child, discord.ui.Button):
                            child.disabled = True
                    
                    current_embed = game.build_embed()
                    elapsed = (discord.utils.utcnow() - game.start_time).total_seconds()
                    remaining = max(0, game.duration - elapsed)
                    current_embed.set_footer(text=f"🎯 Main prise par {user.display_name} | ⏳ {int(remaining)}s restantes")
                    
                    await safe_edit(view.message, embed=current_embed, view=view)

            view = BuzzerView(
                modal_title="✍️ Propose ton mot",
                modal_label="Mot",
                modal_placeholder=f"Mot commençant par {game.start_letter} et finissant par {game.end_letter}",
                modal_max_length=30,
                on_submit=on_submit,
                on_buzz=on_buzz,
                buzz_timeout=30, # Le joueur a 30s pour remplir la modal après avoir buzzé
                view_timeout=duration,
            )
        else:
            # En Solo, on utilise ReplyView de jeux_utils
            view = ReplyView(
                user_id=author_id,
                modal_title="✍️ Propose ton mot",
                modal_label="Mot",
                modal_placeholder=f"Mot commençant par {game.start_letter} et finissant par {game.end_letter}",
                modal_max_length=30,
                on_submit=on_submit,
                timeout=duration,
            )

        # Envoi de l'embed de jeu
        view.message = await safe_send(channel, embed=embed, view=view)
        if view.message is None:
            return
        game.message = view.message

        # == Gestion du Timeout (Temps écoulé) ==
        # Les ReplyView/BuzzerView gèrent leur propre timeout interne, 
        # mais on ajoute une sécurité ici pour safe_edit l'embed si personne n'a répondu
        try:
            # On attend un peu plus que la durée pour laisser les views gérer leur timeout
            await self.bot.wait_for("interaction", timeout=duration + 2) 
        except discord.utils.wait_for.TimeoutError:
            pass # Le timeout est géré par la logique ci-dessous

        if state["finished"]:
            return

        # Si on arrive ici, c'est que le temps est écoulé sans victoire
        game.finished = True
        final_embed = game.build_embed()
        # mark_finished désactive les boutons
        await view.mark_finished(embed=final_embed)

    # ============================================================================
    # 🔹 Commande SLASH
    # ============================================================================
    @app_commands.command(name="mot_contraint", description="Devine un mot commençant et finissant par les lettres données.")
    @app_commands.describe(mode="Tapez 'm' ou 'multi' pour le mode multijoueur (buzzer)")
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_mot_contraint(self, interaction: discord.Interaction, mode: str = "solo"):
        await interaction.response.defer()
        # Lancement immédiat
        await self._start_game(interaction.channel, author_id=interaction.user.id, mode=mode)
        # Supprime le message "Le bot réfléchit"
        await interaction.delete_original_response()

    # ============================================================================
    # 🔹 Commande PREFIX
    # ============================================================================
    @commands.command(name="mot_contraint", aliases=["mc"], help="Devine un mot commençant et finissant par des lettres données. !mc multi pour le buzzer.")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_mot_contraint(self, ctx: commands.Context, mode: str = "solo"):
        # Lancement immédiat
        await self._start_game(ctx.channel, author_id=ctx.author.id, mode=mode)

# ================================================================================
# 🔌 Setup du Cog
# ================================================================================
async def setup(bot: commands.Bot):
    cog = MotContraint(bot)
    # Ajout de la catégorie pour l'aide
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Jeux"
    await bot.add_cog(cog)
