# ================================================================================
# 📌 perso.py
# Objectif : Affiche la fiche d'un personnage Bleach récupérée en ligne sur le
#            Bleach Wiki (Fandom). Sans nom : personnage aléatoire.
#            Si le nom est ambigu : menu pour choisir parmi les résultats.
# Catégorie : Bleach
# Accès : Tous
# Cooldown : 5s par utilisateur
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
from discord.ui import View, Select

from utils.discord_utils import safe_send, safe_edit, safe_interact

log = logging.getLogger(__name__)

# ================================================================================
# 📂 Configuration du wiki
# ================================================================================
WIKI_BASE = "https://bleach.fandom.com"      # autre wiki = change seulement cette ligne
API_URL = f"{WIKI_BASE}/api.php"
HEADERS = {"User-Agent": "KisukeUraharaBot/1.0 (bot Discord Bleach)"}

CACHE_TTL = 3600       # une fiche reste 1 heure en mémoire (évite de spammer le wiki)
MAX_FIELDS = 12        # nombre max de champs de l'infobox affichés
MAX_NAME_LEN = 100     # longueur max du nom tapé par l'utilisateur
MAX_CHOICES = 5        # nombre max de résultats proposés dans le menu

# Cache : { "ichigo kurosaki": (heure_de_mise_en_cache, fiche) }
_cache: dict = {}

# ================================================================================
# 🌐 Appel de l'API du wiki
# ================================================================================
async def _api_get(session: aiohttp.ClientSession, params: dict):
    """Appelle l'API MediaWiki et renvoie le JSON, ou None en cas de problème."""
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
            return await response.json(content_type=None)
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as e:
        log.warning("[perso] Requête au wiki impossible : %s", e)
        return None

# ================================================================================
# 🧩 Lecture de l'infobox dans le wikitext
# ================================================================================
# Le wikitext d'une page ressemble à :
#     {{Character Infobox
#     |race = [[Human]]
#     |birthday = July 15
#     }}
# On isole ce bloc {{ ... }} puis on le découpe champ par champ.
_INFOBOX_RE = re.compile(r"\{\{\s*([^|{}\n]*infobox[^|{}\n]*)", re.IGNORECASE)

def _extract_template(text: str, start: int):
    """Renvoie le contenu du modèle {{...}} qui commence à `start` (accolades équilibrées)."""
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
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)                        # commentaires
    text = re.sub(r"<ref[^>]*?/>|<ref[^>]*>.*?</ref>", "", text, flags=re.DOTALL)  # références
    text = re.sub(r"<br\s*/?>", ", ", text, flags=re.IGNORECASE)                   # <br> -> virgule
    text = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", text)                  # [[lien|texte]] -> texte
    for _ in range(5):                                                             # {{modèles}}
        text = re.sub(r"\{\{[^{}]*\}\}", "", text)
    text = text.replace("'''", "").replace("''", "")                               # gras / italique
    text = re.sub(r"<[^>]+>", "", text)                                            # balises HTML
    text = re.sub(r"\s*\n\s*", ", ", text)                                         # retours à la ligne
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip(" ,")

def _is_displayable(key: str) -> bool:
    """Exclut les champs techniques (images, légendes, couleurs)."""
    k = key.lower().replace(" ", "_")
    if "image" in k or k.startswith("caption") or k in {"theme", "color", "colour", "bgcolor"}:
        return False
    return True

# ================================================================================
# 📥 Récupération des fiches
# ================================================================================
async def fetch_character(session, title: str, require_character: bool = False):
    """Construit la fiche de la page `title` (dict), ou None si elle n'existe pas.
    Avec require_character=True, renvoie aussi None si ce n'est pas un personnage."""
    key = title.lower()
    cached = _cache.get(key)
    if cached and time.time() - cached[0] < CACHE_TTL:
        char = cached[1]
        return char if (char["is_character"] or not require_character) else None

    # --- Requête 1 : le wikitext (redirects=1 suit les redirections) ---
    data = await _api_get(session, {
        "action": "parse", "page": title, "prop": "wikitext", "redirects": 1,
    })
    if not data or "parse" not in data:
        return None

    real_title = data["parse"]["title"]
    wikitext = data["parse"]["wikitext"]
    if isinstance(wikitext, dict):               # ancien format de l'API
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

async def search_characters(session, name: str):
    """Renvoie la liste des fiches qui correspondent à `name` (personnages en priorité)."""
    data = await _api_get(session, {
        "action": "query", "list": "search",
        "srsearch": name, "srnamespace": 0, "srlimit": MAX_CHOICES,
    })
    if not data:
        return []
    titles = [r["title"] for r in data.get("query", {}).get("search", [])]
    if not titles:
        return []

    # Toutes les pages sont récupérées EN MÊME TEMPS (asyncio.gather).
    results = await asyncio.gather(*(fetch_character(session, t) for t in titles))
    chars = [c for c in results if c]
    characters = [c for c in chars if c["is_character"]]
    return characters or chars

async def fetch_random_character(session):
    """Renvoie un personnage au hasard (pages aléatoires filtrées sur les personnages)."""
    for _ in range(3):
        data = await _api_get(session, {
            "action": "query", "list": "random", "rnnamespace": 0, "rnlimit": 8,
        })
        if not data:
            return None
        titles = [r["title"] for r in data.get("query", {}).get("random", [])]
        results = await asyncio.gather(
            *(fetch_character(session, t, require_character=True) for t in titles)
        )
        for char in results:
            if char:
                return char
    return None

# ================================================================================
# 🖼️ Construction de l'embed et du bouton lien
# ================================================================================
def build_embed(char: dict) -> discord.Embed:
    summary = char["summary"]
    if len(summary) > 700:
        summary = summary[:700] + "…"

    embed = discord.Embed(
        title=char["title"][:256],
        url=char["url"],
        description=summary or None,
        color=discord.Color.orange(),
    )
    for field_name, field_value in char["fields"]:
        embed.add_field(name=field_name[:256], value=field_value[:1024], inline=True)
    if char["image"]:
        embed.set_image(url=char["image"])
    embed.set_footer(text="Source : Bleach Wiki (Fandom), texte sous licence CC BY-SA")
    return embed

def build_link_view(char: dict) -> View:
    view = View()
    view.add_item(discord.ui.Button(
        label="📖 Page du wiki",
        url=char["url"],
        style=discord.ButtonStyle.link,
    ))
    return view

# ================================================================================
# 🎛️ UI — Menu de choix (quand plusieurs résultats correspondent)
# ================================================================================
class ChoiceView(View):
    def __init__(self, bot, chars):
        super().__init__(timeout=120)
        self.bot = bot
        self.chars = chars
        self.prompt = "🔎 Plusieurs résultats trouvés, choisis un personnage :"
        self.message = None
        self.add_item(ChoiceSelect(self))

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message:
            await safe_edit(self.message, content=self.prompt, view=self)

class ChoiceSelect(Select):
    def __init__(self, parent_view: ChoiceView):
        self.parent_view = parent_view
        options = [
            discord.SelectOption(
                label=char["title"][:100],
                value=str(index),
                description=(char["summary"][:100] or None),
            )
            for index, char in enumerate(parent_view.chars)
        ]
        super().__init__(placeholder="Sélectionne un personnage", options=options)

    async def callback(self, interaction: discord.Interaction):
        char = self.parent_view.chars[int(self.values[0])]
        self.parent_view.stop()      # le menu est utilisé : plus de timeout à gérer
        # safe_interact répond à l'interaction (évite « Cette interaction a échoué »).
        await safe_interact(
            interaction,
            content=None,
            embed=build_embed(char),
            view=build_link_view(char),
            edit=True,
        )

# ================================================================================
# 🧠 Cog principal avec cooldowns centralisés
# ================================================================================
class Perso(commands.Cog):
    """
    Commande /perso et !perso — Affiche la fiche d'un personnage Bleach depuis le wiki.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ============================================================================
    # 🔹 Fonction interne commune
    # ============================================================================
    async def _send_character(self, channel: discord.abc.Messageable, name: str = None):
        session = self.bot.aiohttp_session
        if session is None:
            await safe_send(channel, "⏳ Le bot n'est pas encore prêt, réessaie dans un instant.")
            return

        if name:
            name = name.strip()[:MAX_NAME_LEN]

        # "typing" : affiche « le bot écrit... » pendant la recherche.
        async with channel.typing():
            if name:
                chars = await search_characters(session, name)
            else:
                random_char = await fetch_random_character(session)
                chars = [random_char] if random_char else []

        if not chars:
            # allowed_mentions=none : empêche d'abuser du nom tapé pour faire un @everyone.
            await safe_send(
                channel,
                f"❌ Personnage `{name or 'aléatoire'}` introuvable sur le wiki.",
                allowed_mentions=discord.AllowedMentions.none(),
            )
            return

        # Un seul résultat, ou un titre qui correspond exactement : on l'affiche direct.
        exact = [c for c in chars if name and c["title"].lower() == name.lower()]
        if len(chars) == 1 or exact:
            char = exact[0] if exact else chars[0]
            await safe_send(channel, embed=build_embed(char), view=build_link_view(char))
            return

        # Plusieurs résultats possibles : menu de choix.
        view = ChoiceView(self.bot, chars)
        view.message = await safe_send(channel, view.prompt, view=view)

    # ============================================================================
    # 🔹 Commande SLASH
    # ============================================================================
    @app_commands.command(name="perso", description="Affiche la fiche d'un personnage Bleach (depuis le wiki).")
    @app_commands.describe(name="Nom du personnage (laisser vide pour aléatoire)")
    @app_commands.checks.cooldown(rate=1, per=5.0, key=lambda i: i.user.id)
    async def slash_perso(self, interaction: discord.Interaction, name: str = None):
        # defer : Discord exige une réponse en 3 secondes, la recherche peut durer plus.
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
