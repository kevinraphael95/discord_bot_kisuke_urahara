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
import html
import logging
import random
import re
import time
from urllib.parse import quote

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Select

from utils.discord_anti429 import safe_send, safe_edit

log = logging.getLogger(__name__)

# ================================================================================
# 📂 Configuration du wiki
# ================================================================================
WIKI_BASE = "https://bleach.fandom.com/fr"   # wiki FR. Version anglaise : "https://bleach.fandom.com"
API_URL = f"{WIKI_BASE}/api.php"

# Mots qui, dans une catégorie ou le style de l'infobox, indiquent un personnage
# (« Characters » sur le wiki anglais, « Personnages » sur le wiki français).
CHARACTER_KEYWORDS = ("character", "personnage")
HEADERS = {"User-Agent": "KisukeUraharaBot/1.0 (bot Discord Bleach)"}

CACHE_TTL = 3600       # une fiche reste 1 heure en mémoire (évite de spammer le wiki)
MAX_CACHE = 200        # nombre max de fiches gardées en mémoire
MAX_FIELDS = 12        # nombre max de champs de l'infobox affichés
MAX_NAME_LEN = 100     # longueur max du nom tapé par l'utilisateur
MAX_CHOICES = 5        # nombre max de résultats proposés dans le menu
SUMMARY_LIMIT = 500    # longueur max du résumé dans l'embed

# Champs de l'infobox qu'on n'affiche pas (en minuscules, apostrophe droite).
SKIP_LABELS = {"taille", "poids", "groupe sanguin", "base d'opérations", "manga", "anime"}

# True = prend la DERNIÈRE image de l'infobox (version la plus récente du perso),
# False = image principale de la page (généralement la première).
LATEST_IMAGE = False

# Cache : { "ichigo kurosaki": (heure_de_mise_en_cache, fiche) }
_cache: dict = {}

# ================================================================================
# 🗃️ Cache (borné)
# ================================================================================
def _cache_get(key: str):
    entry = _cache.get(key.lower())
    if entry and time.time() - entry[0] < CACHE_TTL:
        return entry[1]
    return None

def _cache_put(keys, char: dict):
    """Stocke la fiche sous plusieurs clés (titre tapé + vrai titre)."""
    now = time.time()
    if len(_cache) >= MAX_CACHE:
        for k in [k for k, (t, _) in _cache.items() if now - t >= CACHE_TTL]:
            del _cache[k]
        while len(_cache) >= MAX_CACHE:
            del _cache[min(_cache, key=lambda k: _cache[k][0])]
    for k in keys:
        _cache[k.lower()] = (now, char)

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
# 🧩 Lecture du HTML de la page (infobox + résumé)
# ================================================================================
# On lit la page RENDUE (HTML) et non le wikitext : sur Fandom, l'infobox est
# toujours rendue avec la même structure, quel que soit le modèle utilisé :
#     <aside class="portable-infobox ...">
#       <div class="pi-item pi-data">
#         <h3 class="pi-data-label">Race</h3>
#         <div class="pi-data-value">Shinigami</div>
#       </div>
#     </aside>
_ASIDE_RE = re.compile(
    r"<aside[^>]*class=\"([^\"]*portable-infobox[^\"]*)\"[^>]*>(.*?)</aside>",
    re.S | re.I,
)
_DATA_RE = re.compile(
    r"<h3[^>]*class=\"[^\"]*pi-data-label[^\"]*\"[^>]*>(.*?)</h3>\s*"
    r"<div[^>]*class=\"[^\"]*pi-data-value[^\"]*\"[^>]*>(.*?)</div>",
    re.S | re.I,
)
_PAREN_RE = re.compile(r"\s*\([^()]*\)")

def html_to_text(fragment: str, sep: str = ", ") -> str:
    """Transforme un morceau de HTML en texte lisible."""
    fragment = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", fragment, flags=re.S | re.I)
    fragment = re.sub(r"<sup[^>]*>.*?</sup>", "", fragment, flags=re.S | re.I)     # notes [1]
    fragment = re.sub(r"<br\s*/?>|</li>|</div>", sep, fragment, flags=re.I)        # séparateurs
    fragment = re.sub(r"<[^>]+>", "", fragment)                                    # autres balises
    fragment = html.unescape(fragment)                                             # &amp; -> &
    fragment = re.sub(r"\s+", " ", fragment)
    fragment = re.sub(r"\s+,", ",", fragment)
    fragment = re.sub(r"(,\s*){2,}", ", ", fragment)
    return fragment.strip(" ,")

def remove_parentheses(text: str) -> str:
    """Supprime tout ce qui est entre parenthèses (gère l'imbrication)."""
    previous = None
    while previous != text:
        previous = text
        text = _PAREN_RE.sub("", text)
    return re.sub(r"\s{2,}", " ", text).strip()

def shorten(text: str, limit: int = SUMMARY_LIMIT) -> str:
    """Coupe à la fin d'une phrase si possible, sinon avec « … »."""
    if len(text) <= limit:
        return text
    cut = text[:limit]
    end = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "), cut.rfind("."))
    if end > 150:
        return cut[:end + 1]
    return cut.rstrip() + "…"

def parse_infobox_html(page_html: str):
    """Renvoie ([(libellé, valeur), ...], classes_css_de_l_infobox, [urls_images])."""
    match = _ASIDE_RE.search(page_html)
    if not match:
        return [], "", []
    css_class, inner = match.group(1), match.group(2)

    fields = []
    for label, value in _DATA_RE.findall(inner):
        label_text = html_to_text(label, " ")
        value_text = html_to_text(value)
        if label_text and value_text:
            fields.append((label_text, value_text))

    images = []
    for img in re.findall(r"<img[^>]*pi-image-thumbnail[^>]*>", inner, re.S | re.I):
        src = (re.search(r'data-src="([^"]+)"', img) or re.search(r'src="([^"]+)"', img))
        if src:
            url = html.unescape(src.group(1))
            # On retire la miniature (scale-to-width-down/268) pour avoir l'image complète.
            images.append(re.sub(r"/scale-to-width-down/\d+", "", url))
    return fields, css_class, images

def first_paragraphs(page_html: str, count: int = 1) -> str:
    """Renvoie le(s) premier(s) vrai(s) paragraphe(s) de la page (hors infobox),
    sans les passages entre parenthèses."""
    without_infobox = re.sub(r"<aside.*?</aside>", "", page_html, flags=re.S | re.I)
    paragraphs = []
    for p in re.findall(r"<p(?:\s[^>]*)?>(.*?)</p>", without_infobox, flags=re.S | re.I):
        text = remove_parentheses(html_to_text(p, " "))
        if len(text) >= 60:                  # ignore les paragraphes vides / trop courts
            paragraphs.append(text)
        if len(paragraphs) >= count:
            break
    return "\n\n".join(paragraphs)

def _is_character_categories(categories) -> bool:
    return any(k in c.lower() for c in categories for k in CHARACTER_KEYWORDS)

# ================================================================================
# 📥 Récupération des fiches
# ================================================================================
async def fetch_character(session, title: str, require_character: bool = False):
    """Construit la fiche de la page `title` (dict), ou None si elle n'existe pas.
    Avec require_character=True, renvoie aussi None si ce n'est pas un personnage."""
    cached = _cache_get(title)
    if cached:
        return cached if (cached["is_character"] or not require_character) else None

    # Les deux requêtes partent EN MÊME TEMPS :
    #  - parse : section 0 seulement (infobox + intro), pas tout l'article
    #  - query : image, résumé de secours et catégories
    parse_data, extra = await asyncio.gather(
        _api_get(session, {
            "action": "parse", "page": title, "prop": "text", "section": 0,
            "redirects": 1, "disableeditsection": 1, "disablelimitreport": 1,
        }),
        _api_get(session, {
            "action": "query", "prop": "extracts|pageimages|categories",
            "exintro": 1, "explaintext": 1, "exsentences": 5,
            "piprop": "original", "cllimit": "max",
            "redirects": 1, "titles": title,
        }),
    )
    if not parse_data or "parse" not in parse_data:
        return None

    parsed = parse_data["parse"]
    real_title = parsed["title"]
    page_html = parsed.get("text", "")
    if isinstance(page_html, dict):               # ancien format de l'API
        page_html = page_html.get("*", "")

    page = {}
    if extra:
        pages = extra.get("query", {}).get("pages", [])
        if pages:
            page = pages[0]
    categories = [c.get("title", "") for c in page.get("categories", [])]

    raw_fields, aside_class, infobox_images = parse_infobox_html(page_html)
    is_character = (
        _is_character_categories(categories)
        or any(k in aside_class.lower() for k in CHARACTER_KEYWORDS)
    )
    if require_character and not is_character:
        return None
    if not raw_fields:
        log.info("[perso] Aucune infobox lisible pour « %s »", real_title)

    # --- Résumé : 1er paragraphe de la page, sinon extrait de l'API ---
    summary = first_paragraphs(page_html)
    if not summary:
        summary = remove_parentheses((page.get("extract") or "").strip())

    # --- Image ---
    if LATEST_IMAGE and infobox_images:
        image = infobox_images[-1]
    else:
        image = (page.get("original") or {}).get("source") or (
            infobox_images[0] if infobox_images else None
        )

    # --- Champs de l'infobox : on saute ceux de SKIP_LABELS, puis MAX_FIELDS max ---
    fields = []
    for label, value in raw_fields:
        if label.replace("’", "'").strip().lower() in SKIP_LABELS:
            continue
        if len(value) > 300:
            value = value[:297] + "…"
        fields.append((label, value))
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
    _cache_put({title, real_title}, char)
    return char

async def character_titles(session, titles):
    """Parmi `titles`, renvoie ceux qui sont des personnages (UNE seule requête)."""
    if not titles:
        return set()
    data = await _api_get(session, {
        "action": "query", "prop": "categories",
        "cllimit": "max", "titles": "|".join(titles),
    })
    if not data:
        return set()
    found = set()
    for page in data.get("query", {}).get("pages", []):
        cats = [c.get("title", "") for c in page.get("categories", [])]
        if _is_character_categories(cats):
            found.add(page.get("title"))
    return found

async def search_candidates(session, name: str):
    """Liste de résultats [{"title", "snippet"}] pour `name`, personnages en priorité.
    Aucune fiche complète n'est téléchargée ici : seulement les titres."""
    data = await _api_get(session, {
        "action": "query", "list": "search",
        "srsearch": name, "srnamespace": 0, "srlimit": MAX_CHOICES,
    })
    if not data:
        return []
    results = data.get("query", {}).get("search", [])
    if not results:
        return []

    char_titles = await character_titles(session, [r["title"] for r in results])
    candidates = [
        {
            "title": r["title"],
            "snippet": remove_parentheses(html_to_text(r.get("snippet", ""), " ")),
        }
        for r in results
    ]
    characters = [c for c in candidates if c["title"] in char_titles]
    return characters or candidates

async def fetch_random_character(session):
    """Renvoie un personnage au hasard (pages aléatoires filtrées sur les personnages)."""
    for _ in range(3):
        data = await _api_get(session, {
            "action": "query", "list": "random", "rnnamespace": 0,
            "rnlimit": 10, "rnfilterredir": "nonredirects",
        })
        if not data:
            return None
        titles = [r["title"] for r in data.get("query", {}).get("random", [])]
        chars = list(await character_titles(session, titles))
        if chars:
            return await fetch_character(session, random.choice(chars))
    return None

# ================================================================================
# 🖼️ Construction de l'embed et du bouton lien
# ================================================================================
def build_embed(char: dict) -> discord.Embed:
    embed = discord.Embed(
        title=char["title"][:256],
        url=char["url"],
        description=shorten(char["summary"]) or None,
        color=discord.Color.orange(),
    )
    for field_name, field_value in char["fields"]:
        # Valeurs courtes côte à côte, valeurs longues sur toute la largeur.
        embed.add_field(
            name=field_name[:256],
            value=field_value[:1024],
            inline=len(field_value) <= 40,
        )
    if char["image"]:
        embed.set_image(url=char["image"])
    embed.set_footer(text="Source : Bleach Wiki FR (Fandom), texte sous licence CC BY-SA")
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
    def __init__(self, session, candidates, author_id: int):
        super().__init__(timeout=120)
        self.session = session
        self.candidates = candidates[:MAX_CHOICES]
        self.author_id = author_id
        self.prompt = "🔎 Plusieurs résultats trouvés, choisis un personnage :"
        self.message = None
        self.add_item(ChoiceSelect(self))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Seul celui qui a lancé la commande peut utiliser le menu.
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "Ce menu n'est pas pour toi : lance ta propre commande `/perso`.",
                ephemeral=True,
            )
            return False
        return True

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
                label=c["title"][:100],
                value=str(index),
                description=(c["snippet"][:100] or None),
            )
            for index, c in enumerate(parent_view.candidates)
        ]
        super().__init__(placeholder="Sélectionne un personnage", options=options)

    async def callback(self, interaction: discord.Interaction):
        # La fiche complète n'est chargée qu'AU CLIC : on prévient Discord d'abord.
        await interaction.response.defer()
        title = self.parent_view.candidates[int(self.values[0])]["title"]
        char = await fetch_character(self.parent_view.session, title)
        self.parent_view.stop()      # le menu est utilisé : plus de timeout à gérer

        if not char:
            await safe_edit(
                interaction.message,
                content="❌ Impossible de charger cette fiche, réessaie plus tard.",
                embed=None,
                view=None,
            )
            return
        await safe_edit(
            interaction.message,
            content=None,
            embed=build_embed(char),
            view=build_link_view(char),
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
    async def _send_character(self, channel: discord.abc.Messageable, author_id: int, name: str = None):
        session = getattr(self.bot, "aiohttp_session", None)
        if session is None:
            await safe_send(channel, "⏳ Le bot n'est pas encore prêt, réessaie dans un instant.")
            return

        if name:
            name = name.strip()[:MAX_NAME_LEN] or None

        char = None
        candidates = []

        # "typing" : affiche « le bot écrit... » pendant la recherche.
        async with channel.typing():
            if name:
                # 1) Essai direct : le wiki gère les redirections (« Ichigo » -> « Ichigo Kurosaki »).
                char = await fetch_character(session, name, require_character=True)
                if not char:
                    # 2) Sinon, recherche (titres seulement, léger).
                    candidates = await search_candidates(session, name)
                    exact = [c for c in candidates if c["title"].lower() == name.lower()]
                    if exact or len(candidates) == 1:
                        char = await fetch_character(session, (exact or candidates)[0]["title"])
                        candidates = []
            else:
                char = await fetch_random_character(session)

        if char:
            await safe_send(channel, embed=build_embed(char), view=build_link_view(char))
            return

        if not candidates:
            # allowed_mentions=none : empêche d'abuser du nom tapé pour faire un @everyone.
            await safe_send(
                channel,
                f"❌ Personnage `{name or 'aléatoire'}` introuvable sur le wiki.",
                allowed_mentions=discord.AllowedMentions.none(),
            )
            return

        # Plusieurs résultats possibles : menu de choix.
        view = ChoiceView(session, candidates, author_id)
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
        await self._send_character(interaction.channel, interaction.user.id, name)
        await interaction.delete_original_response()

    # ============================================================================
    # 🔹 Commande PREFIX
    # ============================================================================
    @commands.command(name="perso", help="Affiche la fiche d'un personnage Bleach (depuis le wiki).")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_perso(self, ctx: commands.Context, *, name: str = None):
        await self._send_character(ctx.channel, ctx.author.id, name)

    # ============================================================================
    # 🔹 Gestion des cooldowns (sinon l'utilisateur ne voit rien)
    # ============================================================================
    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                f"⏳ Doucement ! Réessaie dans {error.retry_after:.1f}s.", ephemeral=True
            )
            return
        raise error

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.CommandOnCooldown):
            await safe_send(ctx.channel, f"⏳ Doucement ! Réessaie dans {error.retry_after:.1f}s.")
            return
        raise error

# ================================================================================
# 🔌 Setup du Cog
# ================================================================================
async def setup(bot: commands.Bot):
    cog = Perso(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Bleach"
    await bot.add_cog(cog)
