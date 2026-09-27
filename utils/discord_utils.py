# ================================================================================
# 📌 discord_utils.py — Fonctions utilitaires sécurisées pour Discord
# Objectif : Éviter à tout prix le rate-limit 429
# Version : ✅ Sémaphore par bucket + throttle AVANT l'appel + backoff retry_after
# ================================================================================

# ================================================================================
# 📦 Imports nécessaires
# ================================================================================
import asyncio
import logging
from collections import defaultdict

import discord
from discord.errors import HTTPException

# ================================================================================
# 🧠 Logger
# ================================================================================
log = logging.getLogger(__name__)

# ================================================================================
# 🚦 État global : un sémaphore + un timestamp par "bucket" Discord
# ================================================================================
# Discord limite par bucket : un channel, un webhook, une interaction, etc.
# Deux appels simultanés sur le même bucket = risque de 429.
# Le sémaphore garantit qu'UN SEUL appel part à la fois par bucket.
_semaphores: dict = defaultdict(lambda: asyncio.Semaphore(1))
_last_call: dict = defaultdict(float)

# Espacement minimum entre deux appels successifs sur le même bucket.
# Discord autorise ~5 requêtes / 5s par channel : 50ms est très conservateur
# et n'a aucun impact perceptible sur l'UX, tout en lissant les rafales.
_MIN_INTERVAL = 0.05

# Nombre de tentatives max en cas de 429
_DEFAULT_RETRY = 3


# ================================================================================
# 🔑 Détermination du bucket à partir de l'objet cible
# ================================================================================
def _bucket_for(target) -> str:
    """
    Retourne une clé de bucket cohérente avec ce que Discord utilise pour
    le rate-limit. Important : un Message et un Channel ne partagent PAS le
    même bucket côté Discord — c'est le channel qui compte pour les sends/edits.
    """
    if isinstance(target, discord.Interaction):
        return f"interaction:{target.id}"
    if isinstance(target, discord.Message):
        return f"channel:{target.channel.id}"
    if isinstance(target, discord.abc.Messageable):
        return f"channel:{target.id}"
    if isinstance(target, discord.abc.GuildChannel):
        return f"channel:{target.id}"
    return "global"


# ================================================================================
# 🛡️ Cœur : action Discord sécurisée (throttle + sémaphore + backoff 429)
# ================================================================================
async def _discord_action(
    action_func,
    *args,
    target=None,
    retry: int = _DEFAULT_RETRY,
    delay: float = None,  # conservé pour compat API, ignoré
    **kwargs,
):
    """
    Exécute une action Discord en respectant le rate-limit de bout en bout.

    - target : objet Discord (channel, message, interaction) qui sert à
      identifier le bucket. Si None, on prend args[0] par défaut.
    - retry  : nombre de tentatives supplémentaires en cas de 429.
    - delay  : conservé pour compatibilité avec l'ancienne signature,
               mais ignoré (le throttle est géré globalement via _MIN_INTERVAL).

    Ordre des opérations :
      1. On prend le sémaphore du bucket (un seul appel à la fois).
      2. On attend le temps nécessaire pour respecter _MIN_INTERVAL (AVANT l'appel).
      3. On tente l'appel.
      4. Si 429 → on attend retry_after exact renvoyé par Discord, puis on retente.
      5. Si autre erreur → on remonte (l'appelant décide).
    """
    if target is None and args:
        target = args[0]
    bucket = _bucket_for(target)
    sem = _semaphores[bucket]

    async with sem:
        for attempt in range(1, retry + 2):
            # --- Throttle AVANT l'appel (le point crucial) ---
            now = asyncio.get_event_loop().time()
            wait = _MIN_INTERVAL - (now - _last_call[bucket])
            if wait > 0:
                await asyncio.sleep(wait)

            _last_call[bucket] = asyncio.get_event_loop().time()

            try:
                return await action_func(*args, **kwargs)

            except HTTPException as e:
                if e.status == 429:
                    wait_time = getattr(e, "retry_after", None) or (attempt * 2.0)
                    log.warning(
                        "[RateLimit] %s (bucket=%s) → 429, pause %.2fs (tentative %d/%d)",
                        action_func.__name__, bucket, wait_time, attempt, retry + 1,
                    )
                    await asyncio.sleep(wait_time)
                    continue
                # Autre erreur HTTP : on remonte (bot.py gère)
                raise

            except Exception:
                # Toute autre erreur : on remonte (bot.py gère)
                raise

        log.error(
            "[RateLimit] %s (bucket=%s) → échec après %d tentatives",
            action_func.__name__, bucket, retry + 1,
        )
        return None


# ================================================================================
# 📩 Fonctions publiques sécurisées (API identique à l'ancienne version)
# ================================================================================
async def safe_send(channel: discord.abc.Messageable, content=None, **kwargs):
    return await _discord_action(channel.send, content=content, target=channel, **kwargs)


async def safe_create_webhook(channel: discord.abc.GuildChannel, **kwargs):
    """Crée un webhook en toute sécurité (retry/backoff 429 identique aux autres actions)."""
    return await _discord_action(channel.create_webhook, target=channel, **kwargs)


async def safe_edit(message: discord.Message, content=None, **kwargs):
    return await _discord_action(message.edit, content=content, target=message, **kwargs)


async def safe_respond(interaction: discord.Interaction, content=None, **kwargs):
    return await _discord_action(
        interaction.response.send_message,
        content=content,
        target=interaction,
        **kwargs,
    )


async def safe_followup(interaction: discord.Interaction, content=None, **kwargs):
    return await _discord_action(
        interaction.followup.send,
        content=content,
        target=interaction,
        **kwargs,
    )


async def safe_interact(interaction: discord.Interaction, content=None, edit=False, **kwargs):
    """
    Envoie ou édite une réponse d'interaction en toute sécurité.
    - Si edit=True → édite le message de l'interaction.
    - Sinon → envoie une nouvelle réponse (ephemeral possible).
    """
    try:
        if edit:
            if not interaction.response.is_done():
                return await _discord_action(
                    interaction.response.edit_message,
                    content=content, target=interaction, **kwargs,
                )
            return await _discord_action(
                interaction.edit_original_response,
                content=content, target=interaction, **kwargs,
            )

        if not interaction.response.is_done():
            return await _discord_action(
                interaction.response.send_message,
                content=content, target=interaction, **kwargs,
            )
        return await _discord_action(
            interaction.followup.send,
            content=content, target=interaction, **kwargs,
        )
    except Exception:
        log.exception("[safe_interact] échec")
        return None


async def safe_reply(ctx_or_message, content=None, **kwargs):
    return await _discord_action(
        ctx_or_message.reply, content=content, target=ctx_or_message, **kwargs
    )


async def safe_add_reaction(message: discord.Message, emoji: str, delay: float = 0):
    return await _discord_action(message.add_reaction, emoji, target=message)


async def safe_delete(message: discord.Message, delay: float = 0):
    """
    Supprime un message. Si delay > 0, attend AVANT la suppression.
    """
    if delay > 0:
        await asyncio.sleep(delay)
    return await _discord_action(message.delete, target=message)


async def safe_clear_reactions(message: discord.Message, delay: float = 0):
    return await _discord_action(message.clear_reactions, target=message)
