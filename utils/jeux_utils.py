# ================================================================================
# 📌 jeux_utils.py — Fonctions utilitaires communes aux jeux
# Objectif : Standardiser le comportement des jeux (modes, embeds, fin de partie)
# Catégorie : Utils
# Accès : Interne
# ================================================================================

# ================================================================================
# 📦 Imports nécessaires
# ================================================================================
import unicodedata
import discord

from utils.discord_utils import safe_send, safe_edit, safe_respond, safe_followup


# ================================================================================
# 🔹 Normalisation de texte
# ================================================================================
def normalize_text(text: str) -> str:
    """Retire les accents et met en minuscules."""
    return ''.join(
        c for c in unicodedata.normalize('NFD', text.lower())
        if unicodedata.category(c) != 'Mn'
    ).strip()


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
    return await safe_edit(message, embed=embed, view=view)
