# ================================================================================
# 📌 jeux_utils.py — Fonctions utilitaires communes aux jeux
# Objectif : Standardiser le comportement des jeux (modes, embeds, réponses, fin)
# Catégorie : Utils
# Accès : Interne
# ================================================================================

# ================================================================================
# 📦 Imports nécessaires
# ================================================================================
import asyncio
import logging
import unicodedata
import discord

from utils.discord_utils import safe_send, safe_edit, safe_respond, safe_followup

log = logging.getLogger(__name__)


# ================================================================================
# 🔹 Normalisation de texte (accents + tirets + espaces)
# ================================================================================
def normalize_text(text: str) -> str:
    """
    Retire les accents, tirets, espaces et apostrophes, puis met en minuscules.
    Ex : "Arc-en-Ciel" → "arcenciel"
    """
    text = ''.join(
        c for c in unicodedata.normalize('NFD', text.lower())
        if unicodedata.category(c) != 'Mn'
    )
    for ch in ("-", " ", "'", "’", "_"):
        text = text.replace(ch, "")
    return text.strip()


# ================================================================================
# 🔹 Parsing du mode (solo / multi)
# ================================================================================
def parse_mode(mode: str | None) -> bool:
    """Retourne True si le mode est multi."""
    return bool(mode and mode.lower() in ("m", "multi", "multijoueur"))


# ================================================================================
# 🔹 Vérification de l'auteur
# ================================================================================
def is_author(user_id: int, author_id: int | None) -> bool:
    """True si user_id == author_id (ou si author_id est None = multi)."""
    return author_id is None or user_id == author_id


# ================================================================================
# 🔹 Création d'embed standardisé
# ================================================================================
def make_game_embed(
    title: str,
    description: str,
    color: discord.Color | None = None,
    footer: str | None = None,
) -> discord.Embed:
    """Crée un embed standardisé pour un jeu."""
    embed = discord.Embed(
        title=title,
        description=description,
        color=color or discord.Color.blurple(),
    )
    if footer:
        embed.set_footer(text=footer)
    return embed


# ================================================================================
# 🔹 Envoi d'embed de jeu
# ================================================================================
async def send_game_embed(channel, embed, view=None):
    """Envoie un embed de jeu et retourne le message."""
    return await safe_send(channel, embed=embed, view=view)


# ================================================================================
# 🔹 Fin de partie standardisée
# ================================================================================
async def finish_game(message, embed, view=None):
    """Termine une partie : désactive les boutons et édite l'embed final."""
    if view:
        for child in view.children:
            child.disabled = True
        if hasattr(view, "finished"):
            view.finished = True
    return await safe_edit(message, embed=embed, view=view)


# ================================================================================
# 🔹 Modal standardisée pour les jeux
# ================================================================================
class ReplyModal(discord.ui.Modal):
    """Modal standard : un seul champ de saisie pour répondre à un jeu."""

    def __init__(
        self,
        title: str,
        label: str,
        placeholder: str,
        max_length: int,
        on_submit_callback,
    ):
        super().__init__(title=title)
        self.on_submit_callback = on_submit_callback

        self.answer = discord.ui.TextInput(
            label=label,
            placeholder=placeholder,
            required=True,
            max_length=max_length,
        )
        self.add_item(self.answer)

    async def on_submit(self, interaction: discord.Interaction):
        await self.on_submit_callback(interaction, self.answer.value)


# ================================================================================
# 🔹 View standardisée : bouton "✍️ Répondre"
# ================================================================================
class ReplyView(discord.ui.View):
    """View standard avec un bouton '✍️ Répondre' qui ouvre une modal."""

    def __init__(
        self,
        user_id: int,
        modal_title: str,
        modal_label: str,
        modal_placeholder: str = "...",
        modal_max_length: int = 50,
        on_submit=None,
        timeout: int = 180,
    ):
        super().__init__(timeout=timeout)
        self.user_id           = user_id
        self.modal_title       = modal_title
        self.modal_label       = modal_label
        self.modal_placeholder = modal_placeholder
        self.modal_max_length  = modal_max_length
        self.on_submit         = on_submit
        self.message           = None
        self.finished          = False

    @discord.ui.button(label="✍️ Répondre", style=discord.ButtonStyle.primary)
    async def reply(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await safe_respond(interaction, "❌ Ce n'est pas ton jeu.", ephemeral=True)
            return

        if self.finished:
            await safe_respond(interaction, "❌ La partie est terminée.", ephemeral=True)
            return

        if self.on_submit is None:
            await safe_respond(interaction, "❌ Ce jeu est mal configuré.", ephemeral=True)
            return

        modal = ReplyModal(
            title=self.modal_title,
            label=self.modal_label,
            placeholder=self.modal_placeholder,
            max_length=self.modal_max_length,
            on_submit_callback=self.on_submit,
        )
        try:
            await interaction.response.send_modal(modal)
        except discord.NotFound:
            pass

    async def mark_finished(self, embed=None):
        """Marque la partie comme terminée et désactive les boutons."""
        self.finished = True
        for child in self.children:
            child.disabled = True
        if self.message:
            try:
                if embed is not None:
                    await safe_edit(self.message, embed=embed, view=self)
                else:
                    await safe_edit(self.message, view=self)
            except Exception:
                pass


# ================================================================================
# 🔹 View avec BUZZER + Modal (1 seul joueur à la fois)
# ================================================================================
class BuzzerView(discord.ui.View):
    """
    View standard :
    - Un bouton '🔔 Buzzer' visible par tous
    - Le 1er qui clique prend la main et ouvre une modal
    - Un timeout de sécurité déverrouille si le joueur ferme la modal sans valider
    - Un flag `finished` empêche toute nouvelle interaction après la fin
    """

    def __init__(
        self,
        modal_title: str,
        modal_label: str,
        modal_placeholder: str = "...",
        modal_max_length: int = 50,
        on_submit=None,
        on_buzz=None,          # ✅ reçoit un discord.User
        on_buzz_timeout=None,  # ✅ appelé quand le timer de buzz expire
        buzz_timeout: int = 10,
        view_timeout: int = 300,
    ):
        super().__init__(timeout=view_timeout)
        self.modal_title       = modal_title
        self.modal_label       = modal_label
        self.modal_placeholder = modal_placeholder
        self.modal_max_length  = modal_max_length
        self.on_submit         = on_submit
        self.on_buzz           = on_buzz
        self.on_buzz_timeout   = on_buzz_timeout
        self.buzz_timeout      = buzz_timeout
        self.buzzer_id         = None
        self.buzz_task         = None
        self.message           = None
        self.finished          = False

    @discord.ui.button(label="🔔 Buzzer", style=discord.ButtonStyle.primary)
    async def buzz(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.finished:
            await safe_respond(interaction, "❌ La partie est terminée.", ephemeral=True)
            return

        if self.buzzer_id is not None:
            await safe_respond(
                interaction,
                f"❌ Trop tard ! C'est <@{self.buzzer_id}> qui a la main.",
                ephemeral=True,
            )
            return

        # 1. Marque le buzzer AVANT tout
        self.buzzer_id  = interaction.user.id
        button.disabled = True

        # 2. Ouvre la modal le plus vite possible
        modal = ReplyModal(
            title=self.modal_title,
            label=self.modal_label,
            placeholder=self.modal_placeholder,
            max_length=self.modal_max_length,
            on_submit_callback=self._wrap_submit(),
        )
        try:
            await interaction.response.send_modal(modal)
        except discord.NotFound:
            log.warning("[BuzzerView] Interaction expirée avant send_modal")
            self.buzzer_id  = None
            button.disabled = False
            return

        # 3. Désactive VISUELLEMENT le bouton pour tout le monde (AVANT on_buzz)
        if self.message:
            try:
                await safe_edit(self.message, view=self)
            except Exception as e:
                log.exception("[BuzzerView] safe_edit a échoué : %s", e)

        # 4. Callback externe (embed "Au tour de X")
        if self.on_buzz:
            try:
                await self.on_buzz(interaction.user)
            except Exception as e:
                log.exception("[BuzzerView] on_buzz a échoué : %s", e)

        # 5. Timer de sécurité
        self.buzz_task = asyncio.create_task(self._unlock_after_timeout())

    async def _unlock_after_timeout(self):
        """Déverrouille automatiquement après un délai."""
        try:
            await asyncio.sleep(self.buzz_timeout)
            if self.buzzer_id is not None:
                if self.on_buzz_timeout:
                    try:
                        await self.on_buzz_timeout()
                    except Exception as e:
                        log.exception("[BuzzerView] on_buzz_timeout a échoué : %s", e)
                await self.unlock()
        except asyncio.CancelledError:
            pass

    def _wrap_submit(self):
        """Wrapper : annule le timer + déverrouille après validation."""
        async def _callback(interaction, answer):
            if self.buzz_task and not self.buzz_task.done():
                self.buzz_task.cancel()

            try:
                if self.on_submit:
                    await self.on_submit(interaction, answer)
            finally:
                await self.unlock()

        return _callback

    async def unlock(self, force: bool = False):
        """Déverrouille le buzzer pour le tour suivant."""
        self.buzzer_id = None
        if self.buzz_task and not self.buzz_task.done():
            self.buzz_task.cancel()

        if self.finished and not force:
            return

        for child in self.children:
            child.disabled = False

        if self.message:
            try:
                await safe_edit(self.message, view=self)
            except Exception as e:
                log.exception("[BuzzerView] unlock safe_edit a échoué : %s", e)

    async def mark_finished(self, embed=None):
        """Marque la partie comme terminée et désactive les boutons."""
        self.finished = True
        for child in self.children:
            child.disabled = True
        if self.message:
            try:
                if embed is not None:
                    await safe_edit(self.message, embed=embed, view=self)
                else:
                    await safe_edit(self.message, view=self)
            except Exception:
                pass

    async def on_timeout(self):
        """Ferme les boutons quand la view expire."""
        self.finished = True
        for child in self.children:
            child.disabled = True
        if self.message:
            try:
                await safe_edit(self.message, view=self)
            except Exception:
                pass
