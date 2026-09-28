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
_semaphores: dict = defaultdict(lambda: asyncio.Semaphore(1))
_last_call: dict = defaultdict(float)

_MIN_INTERVAL = 0.05

_DEFAULT_RETRY = 3


# ================================================================================
# 🔑 Détermination du bucket à partir de l'objet cible
# ================================================================================
def _bucket_for(target) -> str:
    """
    Retourne une clé de bucket cohérente avec ce que Discord utilise pour
    le rate-limit.
    """
    if isinstance(target, discord.Interaction):
        return f"interaction:{target.id}"
    if isinstance(target, discord.Message):
        return f"channel:{target.channel.id}"
    if isinstance(target, discord.abc.Messageable):
        return f"channel:{target.id}"
    if isinstance(target, discord.abc.GuildChannel):
        return f"channel:{target.id}"
    # 👇 AJOUTÉ : gère les Context (ctx) — ils ont un .channel au lieu d'un .id
    if hasattr(target, "channel") and hasattr(target.channel, "id"):
        return f"channel:{target.channel.id}"
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
    if target is None and args:
        target = args[0]
    bucket = _bucket_for(target)
    sem = _semaphores[bucket]

    async with sem:
        for attempt in range(1, retry + 2):
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
                raise

            except Exception:
                raise

        log.error(
            "[RateLimit] %s (bucket=%s) → échec après %d tentatives",
            action_func.__name__, bucket, retry + 1,
        )
        return None


# ================================================================================
# 📩 Fonctions publiques sécurisées
# ================================================================================
async def safe_send(channel: discord.abc.Messageable, content=None, **kwargs):
    return await _discord_action(channel.send, content=content, target=channel, **kwargs)


async def safe_create_webhook(channel: discord.abc.GuildChannel, **kwargs):
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
    if delay > 0:
        await asyncio.sleep(delay)
    return await _discord_action(message.delete, target=message)


async def safe_clear_reactions(message: discord.Message, delay: float = 0):
    return await _discord_action(message.clear_reactions, target=message)
