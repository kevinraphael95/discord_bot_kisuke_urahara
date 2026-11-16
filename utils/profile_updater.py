# ================================================================================
# 📌 profile_updater.py
# Objectif : Mettre à jour l'avatar et/ou la bannière du bot (GIF supportés)
# ================================================================================

# ================================================================================
# 📦 Modules standards
# ================================================================================
import asyncio
import logging
from pathlib import Path

# ================================================================================
# 📦  Modules tiers
# ================================================================================
import discord

# ================================================================================
# 📝 Initialisation du logger
# ================================================================================
log = logging.getLogger(__name__)

# ================================================================================
# 🖼️ Fonction principale de mise à jour du profil
# ================================================================================
async def update_bot_profile(
    bot: discord.Client,
    avatar_path: str | None = None,
    banner_path: str | None = None,
) -> bool:
    """
    Met à jour l'avatar et/ou la bannière du bot.

    :param bot: Instance du bot (discord.Client / commands.Bot)
    :param avatar_path: Chemin vers le fichier image/GIF de l'avatar (optionnel)
    :param banner_path: Chemin vers le fichier image/GIF de la bannière (optionnel)
    :return: True si la mise à jour a réussi, False sinon
    """
    if not avatar_path and not banner_path:
        log.warning("⚠️ Aucun avatar ni bannière fourni, rien à faire.")
        return False

    kwargs = {}
    try:
        if avatar_path:
            kwargs["avatar"] = await asyncio.to_thread(Path(avatar_path).read_bytes)
        if banner_path:
            kwargs["banner"] = await asyncio.to_thread(Path(banner_path).read_bytes)
    except FileNotFoundError as e:
        log.error("❌ Fichier introuvable : %s", e)
        return False

    try:
        await bot.user.edit(**kwargs)
        log.info("✅ Profil du bot mis à jour : %s", ", ".join(kwargs))
        return True
    except discord.HTTPException as e:
        log.error("❌ Impossible de mettre à jour le profil : %s", e)
    except TypeError as e:
        log.error("❌ Paramètre non supporté (version de discord.py ?) : %s", e)
    return False
