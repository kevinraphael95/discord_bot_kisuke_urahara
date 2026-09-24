# ================================================================================
# 📌 discord_utils.py — Fonctions utilitaires sécurisées pour Discord
# Objectif : Fournir des fonctions send/edit/respond optimisées avec gestion du rate-limit
# ================================================================================

# ================================================================================
# 📦 Imports nécessaires
# ================================================================================
import asyncio
import discord
from discord.errors import HTTPException

# ================================================================================
# 🛡️ Gestion centralisée des appels Discord avec backoff 429
# ================================================================================
async def _discord_action(action_func, *args, retry=3, delay=0.3, **kwargs):
    """
    Exécute une action Discord sécurisée avec gestion du rate-limit et des exceptions.
    - action_func : fonction Discord à appeler (send, edit, reply, etc.)
    - retry : nombre de tentatives en cas de 429
    - delay : délai entre chaque tentative (anti-429)
    """
    for attempt in range(1, retry + 2):
        try:
            result = await action_func(*args, **kwargs)
            if delay > 0:
                await asyncio.sleep(delay)
            return result
        except HTTPException as e:
            if e.status == 429:
                # Utilise le délai exact renvoyé par Discord (retry_after) plutôt qu'un délai deviné :
                # trop court, on retente en boucle contre le rate-limit ; trop long, on ralentit le bot pour rien.
                wait_time = e.retry_after if getattr(e, "retry_after", None) else 10 * attempt
                print(f"[RateLimit] {action_func.__name__} → 429 Too Many Requests. Pause {wait_time}s...")
                await asyncio.sleep(wait_time)
            else:
                raise e
        except Exception as e:
            print(f"[Erreur] {action_func.__name__} → {e}")
            return None
    print(f"[Erreur] {action_func.__name__} → Échec après {retry+1} tentatives")
    return None

# ================================================================================
# 📩 Fonctions publiques sécurisées
# ================================================================================
async def safe_send(channel: discord.abc.Messageable, content=None, **kwargs):
    return await _discord_action(channel.send, content=content, **kwargs)

async def safe_create_webhook(channel: discord.abc.GuildChannel, **kwargs):
    """Crée un webhook en toute sécurité (retry/backoff 429 identique aux autres actions)."""
    return await _discord_action(channel.create_webhook, **kwargs)

async def safe_edit(message: discord.Message, content=None, **kwargs):
    return await _discord_action(message.edit, content=content, **kwargs)

async def safe_respond(interaction: discord.Interaction, content=None, **kwargs):
    return await _discord_action(interaction.response.send_message, content=content, **kwargs)

async def safe_followup(interaction: discord.Interaction, content=None, **kwargs):
    return await _discord_action(interaction.followup.send, content=content, **kwargs)

async def safe_interact(interaction: discord.Interaction, content=None, edit=False, **kwargs):
    """
    Envoie ou édite une réponse d'interaction en toute sécurité.
    - Si edit=True → édite le message de l'interaction.
    - Sinon → envoie une nouvelle réponse (ephemeral possible).
    """
    try:
        if edit:
            if not interaction.response.is_done():
                # Édition directe avant réponse
                return await _discord_action(interaction.response.edit_message, content=content, **kwargs)
            else:
                # Édition après réponse initiale
                return await _discord_action(interaction.edit_original_response, content=content, **kwargs)
        else:
            if not interaction.response.is_done():
                return await _discord_action(interaction.response.send_message, content=content, **kwargs)
            else:
                return await _discord_action(interaction.followup.send, content=content, **kwargs)
    except Exception as e:
        print(f"[Erreur] safe_interact → {e}")
        return None

async def safe_reply(ctx_or_message, content=None, **kwargs):
    return await _discord_action(ctx_or_message.reply, content=content, **kwargs)

async def safe_add_reaction(message: discord.Message, emoji: str, delay: float = 0.3):
    return await _discord_action(message.add_reaction, emoji, delay=delay)

async def safe_delete(message: discord.Message, delay: float = 0):
    result = await _discord_action(message.delete)
    if delay > 0:
        await asyncio.sleep(delay)
    return result

async def safe_clear_reactions(message: discord.Message, delay: float = 0.3):
    result = await _discord_action(message.clear_reactions)
    if delay > 0:
        await asyncio.sleep(delay)
    return result
