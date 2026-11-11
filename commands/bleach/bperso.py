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
import re
import time
from urllib.parse import quote

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Select

from utils.discord_anti429 import safe_send, safe_edit, safe_interact

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

def parse_infobox_html(page_html: str):
    """Renvoie ([(libellé, valeur), ...], classes_css_de_l_infobox, url_image)."""
    match = _ASIDE_RE.search(page_html)
    if not match:
        return [], "", None
    css_class, inner = match.group(1), match.group(2)

    fields = []
    for label, value in _DATA_RE.findall(inner):
        label_text = html_to_text(label, " ")
        value_text = html_to_text(value)
        if label_text and value_text:
            fields.append((label_text, value_text))

    image = None
    img = re.search(r"<img[^>]*pi-image-thumbnail[^>]*>", inner, re.S | re.I)
    if img:
        src = (re.search(r'data-src="([^"]+)"', img.group(0))
               or re.search(r'src="([^"]+)"', img.group(0)))
        if src:
            image = html.unescape(src.group(1))
    return fields, css_class, image

def first_paragraphs(page_html: str, count: int = 2) -> str:
    """Renvoie les premiers vrais paragraphes de la page (hors infobox)."""
    without_infobox = re.sub(r"<aside.*?</aside>", "", page_html, flags=re.S | re.I)
    paragraphs = []
    for p in re.findall(r"<p[^>]*>(.*?)</p>", without_infobox, flags=re.S | re.I):
        text = html_to_text(p, " ")
        if len(text) >= 60:                  # ignore les paragraphes vides / trop courts
            paragraphs.append(text)
        if len(paragraphs) >= count:
            break
    return "\n\n".join(paragraphs)

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

    # --- Requête 1 : la page rendue en HTML + ses catégories ---
    data = await _api_get(session, {
        "action": "parse", "page": title, "prop": "text|categories",
        "redirects": 1, "disableeditsection": 1, "disablelimitreport": 1,
    })
    if not data or "parse" not in data:
        return None

    parsed = data["parse"]
    real_title = parsed["title"]
    page_html = parsed.get("text", "")
    if isinstance(page_html, dict):               # ancien format de l'API
        page_html = page_html.get("*", "")
    categories = [
        (c.get("category", "") if isinstance(c, dict) else str(c))
        for c in parsed.get("categories", [])
    ]

    raw_fields, aside_class, infobox_image = parse_infobox_html(page_html)
    is_character = (
        any("character" in c.lower() for c in categories)
        or "character" in aside_class.lower()
    )
    if require_character and not is_character:
        return None
    if not raw_fields:
        log.info("[perso] Aucune infobox lisible pour « %s »", real_title)

    summary = first_paragraphs(page_html)

    # --- Requête 2 : image principale (+ résumé de secours) ---
    image = None
    extra = await _api_get(session, {
        "action": "query", "prop": "extracts|pageimages",
        "exintro": 1, "explaintext": 1, "exsentences": 5,
        "piprop": "original", "redirects": 1, "titles": real_title,
    })
    if extra:
        pages = extra.get("query", {}).get("pages", [])
        if pages:
            image = (pages[0].get("original") or {}).get("source")
            if not summary:
                summary = (pages[0].get("extract") or "").strip()
    image = image or infobox_image

    # --- Champs de l'infobox : on garde les MAX_FIELDS premiers ---
    fields = []
    for label, value in raw_fields:
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
        summary = summary[:700].rstrip() + "…"

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
class bPerso(commands.Cog):
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
    @app_commands.command(name="bperso", description="Affiche la fiche d'un personnage Bleach (depuis le wiki).")
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
    @commands.command(name="bperso", help="Affiche la fiche d'un personnage Bleach (depuis le wiki).")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_perso(self, ctx: commands.Context, *, name: str = None):
        await self._send_character(ctx.channel, name)

# ================================================================================
# 🔌 Setup du Cog
# ================================================================================
async def setup(bot: commands.Bot):
    cog = bPerso(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Bleach"
    await bot.add_cog(cog)
