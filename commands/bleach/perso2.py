# ================================================================================
# 📌 perso.py — Commande interactive /perso et !perso
# Objectif : Affiche la fiche d'un personnage Bleach, récupérée EN LIGNE
#            depuis le Bleach Wiki (Fandom) grâce à son API MediaWiki.
# Catégorie : Bleach
# Accès : Tous
# Cooldown : 5s par utilisateur
# ================================================================================
#
# COMMENT ÇA MARCHE (vue d'ensemble) :
#   1. L'utilisateur tape !perso Ichigo   (ou /perso, ou sans nom = aléatoire)
#   2. On cherche le nom sur le wiki        -> API "list=search"
#   3. On télécharge le wikitext de la page -> API "action=parse"
#   4. On lit l'infobox (le tableau à droite de la page du wiki) dans ce texte
#   5. On récupère le résumé + l'image      -> API "action=query"
#   6. On fabrique un embed Discord et on l'envoie
#
# Toutes les requêtes passent par bot.aiohttp_session (créée dans bot.py),
# donc elles ne bloquent pas le bot.
#
# LIMITE IMPORTANTE : le wiki est en ANGLAIS et les noms des champs de l'infobox
# viennent du wiki (on ne les invente pas). Pour un autre wiki (ex : version
# française), change seulement WIKI_BASE.
# ================================================================================

# ================================================================================
# 📦 Imports nécessaires
# ================================================================================
import asyncio
import logging
import re
import time
from urllib.parse import quote

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

from utils.discord_utils import safe_send

log = logging.getLogger(__name__)

# ================================================================================
# ⚙️ Configuration
# ================================================================================
WIKI_BASE = "https://bleach.fandom.com"
API_URL = f"{WIKI_BASE}/api.php"

# Certains sites refusent les requêtes sans "User-Agent" : on s'identifie.
HEADERS = {"User-Agent": "KisukeUraharaBot/1.0 (bot Discord Bleach)"}

CACHE_TTL = 3600       # on garde une fiche 1 heure en mémoire (évite de spammer le wiki)
MAX_FIELDS = 12        # nombre max de champs de l'infobox affichés dans l'embed
MAX_NAME_LEN = 100     # longueur max du nom tapé par l'utilisateur

# Cache : { "ichigo kurosaki": (heure_de_mise_en_cache, fiche) }
_cache: dict = {}


# ================================================================================
# 🌐 Appel de l'API du wiki
# ================================================================================
async def _api_get(session: aiohttp.ClientSession, params: dict):
    """Appelle l'API MediaWiki et renvoie le JSON, ou None en cas de problème."""
    # formatversion=2 : format JSON plus simple (listes au lieu de dictionnaires numérotés)
    params = {**params, "format": "json", "formatversion": "2"}
    try:
        async with session.get(
            API_URL,
            params=params,
            headers=HEADERS,
            timeout=aiohttp.ClientTimeout(total=10),
        ) as response:
            if response.status != 200:
                log.warning("[perso] Le wiki a répondu %s", response.status)
                return None
            # content_type=None : n'échoue pas si le serveur annonce un autre type
            return await response.json(content_type=None)
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as e:
        log.warning("[perso] Requête au wiki impossible : %s", e)
        return None


# ================================================================================
# 🧩 Lecture de l'infobox dans le wikitext
# ================================================================================
# Le wikitext d'une page ressemble à :
#     {{Character Infobox
#     |image = Ichigo.png
#     |race  = [[Human]], [[Shinigami]]
#     |birthday = July 15
#     }}
#     '''Ichigo Kurosaki''' is the main protagonist...
#
# On isole ce bloc {{ ... }} puis on le découpe champ par champ.

_INFOBOX_RE = re.compile(r"\{\{\s*([^|{}\n]*infobox[^|{}\n]*)", re.IGNORECASE)


def _extract_template(text: str, start: int):
    """Renvoie le contenu du modèle {{...}} commençant à l'index `start`.
    Compte les accolades pour gérer les modèles imbriqués."""
    depth = 0
    i = start
    while i < len(text) - 1:
        pair = text[i:i + 2]
        if pair == "{{":
            depth += 1
            i += 2
        elif pair == "}}":
            depth -= 1
            i += 2
            if depth == 0:
                return text[start + 2:i - 2]
        else:
            i += 1
    return None


def _split_params(body: str):
    """Découpe sur les "|" qui ne sont pas à l'intérieur de {{...}} ou [[...]]."""
    parts, buf, depth, i = [], [], 0, 0
    while i < len(body):
        two = body[i:i + 2]
        if two in ("{{", "[["):
            depth += 1
            buf.append(two)
            i += 2
        elif two in ("}}", "]]"):
            depth = max(depth - 1, 0)
            buf.append(two)
            i += 2
        elif body[i] == "|" and depth == 0:
            parts.append("".join(buf))
            buf = []
            i += 1
        else:
            buf.append(body[i])
            i += 1
    parts.append("".join(buf))
    return parts


def parse_infobox(wikitext: str):
    """Renvoie (nom_du_modèle, {champ: valeur_brute}) ou (None, {})."""
    match = _INFOBOX_RE.search(wikitext)
    if not match:
        return None, {}

    body = _extract_template(wikitext, match.start())
    if body is None:
        return None, {}

    parts = _split_params(body)
    template_name = parts[0].strip()

    fields = {}
    for part in parts[1:]:
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        key = key.strip()
        if key and key not in fields:
            fields[key] = value.strip()
    return template_name, fields


def clean_wikitext(text: str) -> str:
    """Transforme du wikitext en texte lisible."""
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)                    # commentaires
    text = re.sub(r"<ref[^>]*?/>|<ref[^>]*>.*?</ref>", "", text, flags=re.DOTALL)  # références [1]
    text = re.sub(r"<br\s*/?>", ", ", text, flags=re.IGNORECASE)               # <br> -> virgule
    text = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", text)              # [[lien|texte]] -> texte
    for _ in range(5):                                                         # {{modèles}} imbriqués
        text = re.sub(r"\{\{[^{}]*\}\}", "", text)
    text = text.replace("'''", "").replace("''", "")                           # gras / italique
    text = re.sub(r"<[^>]+>", "", text)                                        # balises HTML restantes
    text = re.sub(r"\s*\n\s*", ", ", text)                                     # retours à la ligne
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip(" ,")


def _is_displayable(key: str) -> bool:
    """Exclut les champs techniques (images, légendes, couleurs)."""
    k = key.lower().replace(" ", "_")
    if "image" in k or k.startswith("caption") or k in {"theme", "color", "colour", "bgcolor"}:
        return False
    return True


# ================================================================================
# 📥 Récupération d'une fiche
# ================================================================================
async def fetch_character(session, title: str, require_character: bool = False):
    """Télécharge et construit la fiche de la page `title`.
    Renvoie un dictionnaire, ou None si la page n'existe pas.
    Si require_character=True, renvoie aussi None si ce n'est pas un personnage."""

    key = title.lower()
    cached = _cache.get(key)
    if cached and time.time() - cached[0] < CACHE_TTL:
        char = cached[1]
        return char if (char["is_character"] or not require_character) else None

    # --- Requête 1 : le wikitext de la page (redirects=1 suit les redirections) ---
    data = await _api_get(session, {
        "action": "parse", "page": title, "prop": "wikitext", "redirects": 1,
    })
    if not data or "parse" not in data:
        return None

    real_title = data["parse"]["title"]
    wikitext = data["parse"]["wikitext"]
    if isinstance(wikitext, dict):          # sécurité si l'API renvoie l'ancien format
        wikitext = wikitext.get("*", "")

    template_name, raw_fields = parse_infobox(wikitext)
    is_character = bool(
        (template_name and "character" in template_name.lower())
        or re.search(r"\[\[\s*Category:\s*Characters", wikitext, re.IGNORECASE)
    )
    if require_character and not is_character:
        return None

    # --- Requête 2 : résumé + image principale ---
    summary, image = "", None
    extra = await _api_get(session, {
        "action": "query", "prop": "extracts|pageimages",
        "exintro": 1, "explaintext": 1, "exsentences": 5,
        "piprop": "original", "redirects": 1, "titles": real_title,
    })
    if extra:
        pages = extra.get("query", {}).get("pages", [])
        if pages:
            summary = (pages[0].get("extract") or "").strip()
            image = (pages[0].get("original") or {}).get("source")

    # --- Image de secours : champ "image" de l'infobox ---
    if not image:
        for k, v in raw_fields.items():
            if k.lower() == "image":
                m = re.search(r"([^\n|=\[\]]+\.(?:png|jpe?g|gif|webp))", v, re.IGNORECASE)
                if m:
                    info = await _api_get(session, {
                        "action": "query", "prop": "imageinfo", "iiprop": "url",
                        "titles": "File:" + m.group(1).strip(),
                    })
                    if info:
                        pages = info.get("query", {}).get("pages", [])
                        if pages and pages[0].get("imageinfo"):
                            image = pages[0]["imageinfo"][0].get("url")
                break

    # --- Nettoyage des champs de l'infobox ---
    fields = []
    for k, v in raw_fields.items():
        if not _is_displayable(k):
            continue
        value = clean_wikitext(v)
        if not value:
            continue
        if len(value) > 300:
            value = value[:297] + "…"
        fields.append((k.replace("_", " ").strip().capitalize(), value))
        if len(fields) >= MAX_FIELDS:
            break

    char = {
        "title": real_title,
        "url": f"{WIKI_BASE}/wiki/{quote(real_title.replace(' ', '_'))}",
        "summary": summary,
        "fields": fields,
        "image": image,
        "is_character": is_character,
    }
    _cache[key] = (time.time(), char)
    return char


async def find_character(session, name: str):
    """Cherche un personnage par son nom (tolère les fautes de casse)."""
    data = await _api_get(session, {
        "action": "query", "list": "search",
        "srsearch": name, "srnamespace": 0, "srlimit": 5,
    })
    if not data:
        return None
    results = data.get("query", {}).get("search", [])
    if not results:
        return None

    # Titres candidats : correspondance exacte d'abord, puis l'ordre du wiki.
    titles = [r["title"] for r in results]
    titles.sort(key=lambda t: t.lower() != name.lower())

    first_found = None
    for title in titles[:3]:
        char = await fetch_character(session, title)
        if char and char["is_character"]:
            return char                      # un vrai personnage : parfait
        if char and first_found is None:
            first_found = char               # sinon on garde la 1re page trouvée
    return first_found


async def fetch_random_character(session):
    """Renvoie un personnage au hasard (pages aléatoires filtrées sur les personnages)."""
    for _ in range(3):
        data = await _api_get(session, {
            "action": "query", "list": "random", "rnnamespace": 0, "rnlimit": 8,
        })
        if not data:
            return None
        titles = [r["title"] for r in data.get("query", {}).get("random", [])]
        # Les 8 pages sont testées EN MÊME TEMPS (asyncio.gather).
        results = await asyncio.gather(
            *(fetch_character(session, t, require_character=True) for t in titles)
        )
        for char in results:
            if char:
                return char
    return None


# ================================================================================
# 🧠 Cog principal
# ================================================================================
class Perso(commands.Cog):
    """Commandes /perso et !perso — Affiche la fiche d'un personnage depuis le wiki."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ============================================================================
    # 🔹 Fonction interne commune (slash + préfixe)
    # ============================================================================
    async def _send_character(self, channel: discord.abc.Messageable, name: str = None):
        session = self.bot.aiohttp_session
        if session is None:
            await safe_send(channel, "⏳ Le bot n'est pas encore prêt, réessaie dans un instant.")
            return

        if name:
            name = name.strip()[:MAX_NAME_LEN]

        # "typing" : affiche « Kisuke est en train d'écrire... » pendant la recherche.
        async with channel.typing():
            if name:
                char = await find_character(session, name)
            else:
                char = await fetch_random_character(session)

        if not char:
            # allowed_mentions=none : empêche d'utiliser le bot pour faire un @everyone
            # via le nom tapé par l'utilisateur.
            await safe_send(
                channel,
                f"👎 Personnage `{name or 'aléatoire'}` introuvable sur le wiki.",
                allowed_mentions=discord.AllowedMentions.none(),
            )
            return

        embed = discord.Embed(
            title=char["title"][:256],
            url=char["url"],
            description=(char["summary"][:700] + "…") if len(char["summary"]) > 700 else (char["summary"] or None),
            color=discord.Color.orange(),
        )
        for field_name, field_value in char["fields"]:
            embed.add_field(name=field_name[:256], value=field_value[:1024], inline=True)
        if char["image"]:
            embed.set_image(url=char["image"])
        embed.set_footer(text="Source : Bleach Wiki (Fandom), texte sous licence CC BY-SA")

        view = discord.ui.View()
        view.add_item(discord.ui.Button(
            label="📖 Page du wiki",
            url=char["url"],
            style=discord.ButtonStyle.link,
        ))

        await safe_send(channel, embed=embed, view=view)

    # ============================================================================
    # 🔹 Commande SLASH
    # ============================================================================
    @app_commands.command(name="perso", description="Affiche la fiche d'un personnage Bleach (depuis le wiki).")
    @app_commands.describe(name="Nom du personnage (laisser vide pour aléatoire)")
    @app_commands.checks.cooldown(rate=1, per=5.0, key=lambda i: i.user.id)
    async def slash_perso(self, interaction: discord.Interaction, name: str = None):
        # defer : Discord exige une réponse en 3 secondes. Avec une requête réseau
        # on peut dépasser, donc on dit "je réfléchis" tout de suite.
        await interaction.response.defer()
        await self._send_character(interaction.channel, name)
        await interaction.delete_original_response()

    # ============================================================================
    # 🔹 Commande PREFIX
    # ============================================================================
    @commands.command(name="perso", help="Affiche la fiche d'un personnage Bleach (depuis le wiki).")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_perso(self, ctx: commands.Context, *, name: str = None):
        await self._send_character(ctx.channel, name)


# ================================================================================
# 🔌 Setup du Cog
# ================================================================================
async def setup(bot: commands.Bot):
    cog = Perso(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Bleach"
    await bot.add_cog(cog)
