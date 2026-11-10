# ================================================================================
# 📌 jeux_utils.py — Fonctions utilitaires communes aux jeux
# Objectif : Standardiser le comportement des jeux (modes, embeds, réponses, fin)
# ================================================================================

# ================================================================================
# 📦 Imports nécessaires
# ================================================================================
import asyncio
import logging
import unicodedata
from typing import Awaitable, Callable

import discord

from utils.discord_anti429 import safe_send, safe_edit, safe_respond, safe_followup  # noqa: F401

log = logging.getLogger(__name__)

# Type d'un callback de validation : (interaction, réponse_saisie) -> None
SubmitCallback = Callable[[discord.Interaction, str], Awaitable[None]]


# ================================================================================
# 🔹 Normalisation de texte (accents + ligatures + tirets + espaces)
# ================================================================================
_LIGATURES  = {"œ": "oe", "æ": "ae"}
_SEPARATORS = ("-", " ", "'", "’", "_")


def normalize_text(text: str) -> str:
    """
    Retire les accents, ligatures, tirets, espaces et apostrophes, puis met en minuscules.
    Ex : "Arc-en-Ciel" → "arcenciel" ; "Cœur" → "coeur" ; "Élève" → "eleve"
    """
    text = text.lower()
    for src, dst in _LIGATURES.items():
        text = text.replace(src, dst)

    text = ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    )
    for ch in _SEPARATORS:
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
        on_submit_callback: SubmitCallback,
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

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        """Log l'erreur et prévient le joueur au lieu de l'échec silencieux de Discord."""
        log.exception("[ReplyModal] Erreur dans on_submit : %s", error)
        msg = "❌ Une erreur est survenue, réessaie."
        try:
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
        except discord.HTTPException:
            pass


# ================================================================================
# 🔹 Base commune des views de jeu (message, fin de partie, timeout)
# ================================================================================
class GameView(discord.ui.View):
    """Base : gère `message`, `finished`, `mark_finished` et `on_timeout`."""

    def __init__(self, timeout: float | None = 180):
        super().__init__(timeout=timeout)
        self.message: discord.Message | None = None
        self.finished = False

    async def _refresh(self, embed: discord.Embed | None = None):
        """Édite le message avec l'état actuel de la view (et l'embed si fourni)."""
        if not self.message:
            return
        try:
            if embed is not None:
                await safe_edit(self.message, embed=embed, view=self)
            else:
                await safe_edit(self.message, view=self)
        except Exception as e:
            log.warning("[%s] Édition du message impossible : %s", type(self).__name__, e)

    async def mark_finished(self, embed: discord.Embed | None = None):
        """Marque la partie comme terminée et désactive les boutons."""
        self.finished = True
        for child in self.children:
            child.disabled = True
        await self._refresh(embed)

    async def on_timeout(self):
        """Ferme les boutons quand la view expire."""
        if not self.finished:
            await self.mark_finished()


# ================================================================================
# 🔹 View standardisée : bouton "✍️ Répondre"
# ================================================================================
class ReplyView(GameView):
    """View standard avec un bouton '✍️ Répondre' qui ouvre une modal."""

    def __init__(
        self,
        user_id: int,
        modal_title: str,
        modal_label: str,
        modal_placeholder: str = "...",
        modal_max_length: int = 50,
        on_submit: SubmitCallback | None = None,
        timeout: int = 180,
    ):
        super().__init__(timeout=timeout)
        self.user_id           = user_id
        self.modal_title       = modal_title
        self.modal_label       = modal_label
        self.modal_placeholder = modal_placeholder
        self.modal_max_length  = modal_max_length
        self.on_submit         = on_submit

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


# ================================================================================
# 🔹 View avec BUZZER + Modal (1 seul joueur à la fois)
# ================================================================================
class BuzzerView(GameView):
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
        on_submit: SubmitCallback | None = None,
        on_buzz=None,          # reçoit un discord.User
        on_buzz_timeout=None,  # appelé quand le timer de buzz expire
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
        self.buzzer_id: int | None = None
        self.buzz_task: asyncio.Task | None = None

    # ── Gestion du timer ──
    def _cancel_buzz_task(self):
        """Annule le timer, sauf si on est justement en train d'être exécuté par lui
        (sinon la tâche s'annule elle-même et l'édition du message est interrompue)."""
        task = self.buzz_task
        if task and not task.done() and task is not asyncio.current_task():
            task.cancel()

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

        # 1. Marque le buzzer
        self.buzzer_id = interaction.user.id

        # 2. Désactive le VRAI bouton dans self.children (pas la copie locale)
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True

        # 3. Ouvre la modal
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
            self.buzzer_id = None
            for child in self.children:
                if isinstance(child, discord.ui.Button):
                    child.disabled = False
            return

        # 4. Callback externe (met à jour l'embed "Au tour de X")
        if self.on_buzz:
            try:
                await self.on_buzz(interaction.user)
            except Exception as e:
                log.exception("[BuzzerView] on_buzz a échoué : %s", e)

        # 5. Envoie la view AVEC le bouton grisé
        await self._refresh()

        # 6. Timer de sécurité (seulement si la partie n'a pas fini entre-temps)
        if not self.finished:
            self.buzz_task = asyncio.create_task(self._unlock_after_timeout())

    async def _unlock_after_timeout(self):
        """Déverrouille automatiquement après un délai."""
        try:
            await asyncio.sleep(self.buzz_timeout)
            if self.buzzer_id is not None and not self.finished:
                if self.on_buzz_timeout:
                    try:
                        await self.on_buzz_timeout()
                    except Exception as e:
                        log.exception("[BuzzerView] on_buzz_timeout a échoué : %s", e)
                await self.unlock()
        except asyncio.CancelledError:
            pass

    def _wrap_submit(self) -> SubmitCallback:
        """Wrapper : annule le timer + déverrouille après validation."""
        async def _callback(interaction: discord.Interaction, answer: str):
            # Si le timer a déjà rendu la main à quelqu'un d'autre,
            # on ne doit pas lui voler son tour en déverrouillant.
            is_holder = self.buzzer_id in (None, interaction.user.id)
            if is_holder:
                self._cancel_buzz_task()

            try:
                if self.on_submit:
                    await self.on_submit(interaction, answer)
            finally:
                if is_holder:
                    await self.unlock()

        return _callback

    async def unlock(self, force: bool = False):
        """Déverrouille le buzzer pour le tour suivant."""
        self.buzzer_id = None
        self._cancel_buzz_task()

        if self.finished and not force:
            return

        for child in self.children:
            child.disabled = False

        await self._refresh()

    async def mark_finished(self, embed: discord.Embed | None = None):
        """Fin de partie : coupe aussi le timer de buzz en cours."""
        self.buzzer_id = None
        self._cancel_buzz_task()
        await super().mark_finished(embed)
