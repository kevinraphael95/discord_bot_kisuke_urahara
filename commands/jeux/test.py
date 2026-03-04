# ────────────────────────────────────────────────────────────────────────────────
# 📌 ygonator.py
# Objectif : Akinator Yu-Gi-Oh! — pose des questions Oui/Non/Peut-être/Je sais pas
#            et filtre progressivement via l'API YGOPRODeck pour deviner la carte
# Catégorie : Fun / Jeux
# Accès : Tous
# Cooldown : 10s par utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button
import aiohttp
from typing import Optional

from utils.discord_utils import safe_send, safe_edit, safe_respond, safe_delete

# ────────────────────────────────────────────────────────────────────────────────
# 🎨 Constantes
# ────────────────────────────────────────────────────────────────────────────────
YGOPRO_API = "https://db.ygoprodeck.com/api/v7/cardinfo.php"

FRAME_COLORS = {
    "normal": 0xC8A45B, "effect": 0xFF8B53, "ritual": 0x5B9BD5,
    "fusion": 0x7C4FA0, "synchro": 0xCCCCCC, "xyz": 0x444444,
    "link": 0x003087, "spell": 0x1D9E74, "trap": 0xBC5A84,
    "token": 0x9AA0A6,
}

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Arbre de questions
#
# Chaque entrée :
#   text      : question affichée
#   param     : clé enregistrée dans state
#   yes       : valeur si OUI
#   no        : valeur si NON  (None = pas de filtre en cas de Non)
#   only_if   : {clé: valeur} — question posée seulement si ces conditions sont dans state
#   skip_if   : {clé: valeur} — question sautée si une de ces conditions est dans state
# ────────────────────────────────────────────────────────────────────────────────
QUESTIONS = [
    # ── Catégorie principale ──
    {
        "text":  "Ta carte est un **Monstre** ?",
        "param": "category",
        "yes":   "monster",
        "no":    "spelltrap",
    },

    # ── Branche Magie / Piège ──
    {
        "text":    "C'est une **Magie** (pas un Piège) ?",
        "param":   "type",
        "yes":     "Spell Card",
        "no":      "Trap Card",
        "only_if": {"category": "spelltrap"},
    },
    {
        "text":    "La Magie est **Continue** (reste sur le terrain) ?",
        "param":   "race",
        "yes":     "Continuous",
        "only_if": {"type": "Spell Card"},
    },
    {
        "text":    "La Magie est un **Terrain** (Field) ?",
        "param":   "race",
        "yes":     "Field",
        "only_if": {"type": "Spell Card"},
        "skip_if": {"race": "Continuous"},
    },
    {
        "text":    "La Magie est de **Jeu-Rapide** (Quick-Play) ?",
        "param":   "race",
        "yes":     "Quick-Play",
        "only_if": {"type": "Spell Card"},
        "skip_if": {"race": "Continuous", "race_b": "Field"},
    },
    {
        "text":    "La Magie est d'**Équipement** (Equip) ?",
        "param":   "race",
        "yes":     "Equip",
        "only_if": {"type": "Spell Card"},
        "skip_if": {"race": "Continuous", "race_b": "Field", "race_c": "Quick-Play"},
    },
    {
        "text":    "Le Piège est **Continu** (reste sur le terrain) ?",
        "param":   "race",
        "yes":     "Continuous",
        "only_if": {"type": "Trap Card"},
    },
    {
        "text":    "Le Piège est un **Contre-Piège** (Counter) ?",
        "param":   "race",
        "yes":     "Counter",
        "only_if": {"type": "Trap Card"},
        "skip_if": {"race": "Continuous"},
    },

    # ── Branche Monstre : Extra Deck ──
    {
        "text":    "Ton monstre vient de l'**Extra Deck** ?",
        "param":   "deck",
        "yes":     "extra",
        "no":      "main",
        "only_if": {"category": "monster"},
    },
    {
        "text":    "C'est un monstre **Fusion** ?",
        "param":   "type",
        "yes":     "Fusion Monster",
        "only_if": {"deck": "extra"},
    },
    {
        "text":    "C'est un monstre **Synchro** ?",
        "param":   "type",
        "yes":     "Synchro Monster",
        "only_if": {"deck": "extra"},
        "skip_if": {"type": "Fusion Monster"},
    },
    {
        "text":    "C'est un monstre **XYZ** ?",
        "param":   "type",
        "yes":     "XYZ Monster",
        "only_if": {"deck": "extra"},
        "skip_if": {"type": "Fusion Monster", "type_b": "Synchro Monster"},
    },
    {
        "text":    "C'est un monstre **Lien** (Link) ?",
        "param":   "type",
        "yes":     "Link Monster",
        "only_if": {"deck": "extra"},
        "skip_if": {"type": "Fusion Monster", "type_b": "Synchro Monster", "type_c": "XYZ Monster"},
    },

    # ── Monstre Main Deck : type ──
    {
        "text":    "Ton monstre a un **effet** (texte d'effet actif) ?",
        "param":   "has_effect",
        "yes":     "true",
        "no":      "false",
        "only_if": {"deck": "main"},
    },
    {
        "text":    "Ton monstre est un **Tuner** (syntoniseur, cercle blanc sur l'image) ?",
        "param":   "is_tuner",
        "yes":     "yes",
        "only_if": {"deck": "main"},
    },

    # ── Attribut ──
    {
        "text":    "Ton monstre est d'attribut **DARK** ?",
        "param":   "attribute",
        "yes":     "dark",
        "only_if": {"category": "monster"},
    },
    {
        "text":    "Ton monstre est d'attribut **LIGHT** ?",
        "param":   "attribute",
        "yes":     "light",
        "only_if": {"category": "monster"},
        "skip_if": {"attribute": "dark"},
    },
    {
        "text":    "Ton monstre est d'attribut **EARTH** ?",
        "param":   "attribute",
        "yes":     "earth",
        "only_if": {"category": "monster"},
        "skip_if": {"attribute": "dark", "attribute_b": "light"},
    },
    {
        "text":    "Ton monstre est d'attribut **WATER** ?",
        "param":   "attribute",
        "yes":     "water",
        "only_if": {"category": "monster"},
        "skip_if": {"attribute": "dark", "attribute_b": "light", "attribute_c": "earth"},
    },
    {
        "text":    "Ton monstre est d'attribut **FIRE** ?",
        "param":   "attribute",
        "yes":     "fire",
        "only_if": {"category": "monster"},
        "skip_if": {"attribute": "dark", "attribute_b": "light", "attribute_c": "earth", "attribute_d": "water"},
    },

    # ── Race ──
    {
        "text":    "Ton monstre est un **Dragon** ?",
        "param":   "race",
        "yes":     "Dragon",
        "only_if": {"category": "monster"},
    },
    {
        "text":    "Ton monstre est un **Guerrier** (Warrior) ?",
        "param":   "race",
        "yes":     "Warrior",
        "only_if": {"category": "monster"},
        "skip_if": {"race": "Dragon"},
    },
    {
        "text":    "Ton monstre est un **Magicien** (Spellcaster) ?",
        "param":   "race",
        "yes":     "Spellcaster",
        "only_if": {"category": "monster"},
        "skip_if": {"race": "Dragon", "race_b": "Warrior"},
    },
    {
        "text":    "Ton monstre est une **Machine** ?",
        "param":   "race",
        "yes":     "Machine",
        "only_if": {"category": "monster"},
        "skip_if": {"race": "Dragon", "race_b": "Warrior", "race_c": "Spellcaster"},
    },
    {
        "text":    "Ton monstre est un **Démon** (Fiend) ?",
        "param":   "race",
        "yes":     "Fiend",
        "only_if": {"category": "monster"},
        "skip_if": {"race": "Dragon", "race_b": "Warrior", "race_c": "Spellcaster", "race_d": "Machine"},
    },
    {
        "text":    "Ton monstre est un **Zombie** ?",
        "param":   "race",
        "yes":     "Zombie",
        "only_if": {"category": "monster"},
        "skip_if": {"race": "Dragon", "race_b": "Warrior", "race_c": "Spellcaster", "race_d": "Machine", "race_e": "Fiend"},
    },

    # ── Niveau ──
    {
        "text":    "Ton monstre est de **niveau 4 ou moins** ?",
        "param":   "lvl_group",
        "yes":     "low",
        "no":      "high",
        "only_if": {"category": "monster"},
        "skip_if": {"type": "Link Monster"},
    },
    {
        "text":    "Ton monstre est de **niveau 1 ou 2** ?",
        "param":   "lvl_low",
        "yes":     "1-2",
        "no":      "3-4",
        "only_if": {"lvl_group": "low"},
    },
    {
        "text":    "Ton monstre est de **niveau/rang 8 ou plus** ?",
        "param":   "lvl_high",
        "yes":     "8+",
        "no":      "5-7",
        "only_if": {"lvl_group": "high"},
    },

    # ── ATK ──
    {
        "text":    "Ton monstre a **2000 ATK ou plus** ?",
        "param":   "atk_group",
        "yes":     "high",
        "no":      "low",
        "only_if": {"category": "monster"},
    },
    {
        "text":    "Ton monstre a **3000 ATK ou plus** ?",
        "param":   "atk_exact",
        "yes":     "3000+",
        "no":      "2000-2999",
        "only_if": {"atk_group": "high"},
    },
    {
        "text":    "Ton monstre a **moins de 1000 ATK** (ou 0) ?",
        "param":   "atk_exact",
        "yes":     "sub1000",
        "no":      "1000-1999",
        "only_if": {"atk_group": "low"},
    },
]


# ────────────────────────────────────────────────────────────────────────────────
# 🔧 Helpers
# ────────────────────────────────────────────────────────────────────────────────

def _state_has(state: dict, key: str, val) -> bool:
    """Vérifie si state[clé_sans_suffix] == val (ignore les suffixes _b _c etc.)."""
    base = key.rstrip("abcdefghijklmnopqrstuvwxyz_")
    return state.get(base) == val


def is_applicable(q: dict, state: dict) -> bool:
    """La question doit-elle être posée ?"""
    # Déjà répondu à ce param
    if q["param"] in state:
        return False

    # only_if : toutes les conditions doivent être vraies
    for k, v in q.get("only_if", {}).items():
        if state.get(k) != v:
            return False

    # skip_if : dès qu'une condition est vraie → skip
    for k, v in q.get("skip_if", {}).items():
        base = k.rstrip("abcdefghijklmnopqrstuvwxyz_")
        if state.get(base) == v:
            return False

    return True


def build_api_url(state: dict) -> str:
    """Traduit le state en URL YGOPRODeck."""
    p = {}

    # Type de carte
    t = state.get("type")
    if t in ("Spell Card", "Trap Card", "Fusion Monster",
             "Synchro Monster", "XYZ Monster", "Link Monster"):
        p["type"] = t
    elif state.get("category") == "monster":
        if state.get("has_effect") == "false":
            p["type"] = "Normal Monster"
        elif state.get("is_tuner") == "yes":
            p["type"] = "Tuner Monster"

    # Attribut
    if state.get("attribute") in ("dark","light","earth","water","fire","wind","divine"):
        p["attribute"] = state["attribute"]

    # Race
    if state.get("race") in ("Dragon","Warrior","Spellcaster","Machine","Fiend",
                              "Zombie","Aqua","Beast","Insect","Rock","Pyro",
                              "Plant","Thunder","Winged Beast","Psychic","Reptile",
                              "Cyberse","Wyrm","Sea Serpent","Divine-Beast",
                              "Continuous","Field","Quick-Play","Equip",
                              "Normal","Ritual","Counter"):
        p["race"] = state["race"]

    # Niveau
    ll = state.get("lvl_low")
    lh = state.get("lvl_high")
    lg = state.get("lvl_group")
    if   ll == "1-2":  p["level"] = "lte2"
    elif ll == "3-4":  p["level"] = "gte3&level=lte4"
    elif lh == "5-7":  p["level"] = "gte5&level=lte7"
    elif lh == "8+":   p["level"] = "gte8"
    elif lg == "low":  p["level"] = "lte4"
    elif lg == "high": p["level"] = "gte5"

    # ATK
    ae = state.get("atk_exact")
    ag = state.get("atk_group")
    if   ae == "3000+":    p["atk"] = "gte3000"
    elif ae == "2000-2999":p["atk"] = "gte2000&atk=lte2999"
    elif ae == "sub1000":  p["atk"] = "lt1000"
    elif ae == "1000-1999":p["atk"] = "gte1000&atk=lte1999"
    elif ag == "high":     p["atk"] = "gte2000"
    elif ag == "low":      p["atk"] = "lt2000"

    # Has effect
    if state.get("has_effect") == "true" and "type" not in p:
        p["has_effect"] = "true"

    qs = "&".join(f"{k}={v}" for k, v in p.items())
    return f"{YGOPRO_API}?{qs}" if qs else YGOPRO_API


def card_embed(card: dict, title_prefix: str = "") -> discord.Embed:
    color = FRAME_COLORS.get(card.get("frameType", "effect"), 0xFF8B53)
    embed = discord.Embed(
        title=f"{title_prefix}{card['name']}",
        url=card.get("ygoprodeck_url", ""),
        color=color,
    )
    imgs = card.get("card_images", [])
    if imgs:
        embed.set_thumbnail(url=imgs[0]["image_url_small"])

    atk  = card.get("atk")
    def_ = card.get("def")
    lvl  = card.get("level")
    attr = card.get("attribute", "")
    race = card.get("race", "")
    ctype= card.get("type", "")

    info = f"**{ctype}**"
    if race: info += f" · {race}"
    if attr: info += f" · {attr}"
    embed.add_field(name="Type", value=info, inline=True)
    if lvl  is not None: embed.add_field(name="⭐ Niv.", value=str(lvl), inline=True)
    if atk  is not None:
        s = f"ATK **{atk}**"
        if def_ is not None: s += f" / DEF **{def_}**"
        embed.add_field(name="Stats", value=s, inline=True)

    desc = card.get("desc", "")
    if len(desc) > 300: desc = desc[:297] + "…"
    if desc: embed.add_field(name="Effet", value=desc, inline=False)

    prices = (card.get("card_prices") or [{}])[0]
    cm  = prices.get("cardmarket_price")
    tcp = prices.get("tcgplayer_price")
    if cm or tcp:
        p = ""
        if cm:  p += f"Cardmarket **{cm}€**  "
        if tcp: p += f"TCGPlayer **${tcp}**"
        embed.add_field(name="💰 Prix", value=p.strip(), inline=True)

    embed.set_footer(text=f"ID {card.get('id','?')} · YGOPRODeck")
    return embed


# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ Vue principale
# ────────────────────────────────────────────────────────────────────────────────

class YgonatorView(View):
    def __init__(self, bot: commands.Bot, user: discord.User):
        super().__init__(timeout=180)
        self.bot  = bot
        self.user = user
        self.message: Optional[discord.Message] = None
        self.state:   dict = {}
        self.nb_asked: int = 0
        self.candidates: int = -1
        self._build_buttons()

    # ── Questions encore applicables ──
    @property
    def pending(self) -> list:
        return [q for q in QUESTIONS if is_applicable(q, self.state)]

    # ── Construit les 4 boutons Oui/Non/Peut-être/Je sais pas ──
    def _build_buttons(self):
        self.clear_items()
        answers = [
            ("✅  Oui",          "yes",   discord.ButtonStyle.success),
            ("❌  Non",          "no",    discord.ButtonStyle.danger),
            ("🤔  Peut-être",    "maybe", discord.ButtonStyle.secondary),
            ("🤷  Je sais pas",  "dunno", discord.ButtonStyle.secondary),
        ]
        for label, val, style in answers:
            btn = Button(label=label, style=style, row=0)
            btn.callback = self._make_cb(val)
            self.add_item(btn)

        guess = Button(label="🔮 Deviner !", style=discord.ButtonStyle.primary, row=1)
        guess.callback = self._guess_cb
        self.add_item(guess)

    def _make_cb(self, answer: str):
        async def cb(interaction: discord.Interaction):
            if interaction.user.id != self.user.id:
                return await interaction.response.send_message(
                    "❌ Ce n'est pas ta partie !", ephemeral=True
                )
            await interaction.response.defer()
            await self._handle_answer(answer)
        return cb

    async def _guess_cb(self, interaction: discord.Interaction):
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message(
                "❌ Ce n'est pas ta partie !", ephemeral=True
            )
        await interaction.response.defer()
        await self._do_guess()

    # ── Traitement d'une réponse ──
    async def _handle_answer(self, answer: str):
        pending = self.pending
        if not pending:
            await self._do_guess()
            return

        q = pending[0]
        self.nb_asked += 1

        if answer == "yes" and q.get("yes") is not None:
            self.state[q["param"]] = q["yes"]
        elif answer == "no" and q.get("no") is not None:
            self.state[q["param"]] = q["no"]
        else:
            # Peut-être / Je sais pas / Non sans valeur → marque comme vu sans filtrer
            self.state[q["param"]] = "__skip__"

        # Mise à jour du compteur de candidats
        url   = build_api_url(self.state)
        count = await self._count(url)
        self.candidates = count

        # 1 seule carte → deviner direct
        if count == 1:
            return await self._do_guess()

        # 0 carte → annuler le dernier filtre pour ne pas bloquer
        if count == 0:
            self.state[q["param"]] = "__skip__"
            url   = build_api_url(self.state)
            count = await self._count(url)
            self.candidates = count

        # Plus de questions → deviner
        if not self.pending:
            return await self._do_guess()

        self._build_buttons()
        await safe_edit(self.message, embed=self._embed(), view=self)

    async def _count(self, url: str) -> int:
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(url, timeout=aiohttp.ClientTimeout(total=8)) as r:
                    if r.status != 200:
                        return -1
                    d = await r.json()
                    return len(d.get("data", []))
        except Exception:
            return -1

    async def _do_guess(self):
        self.clear_items()
        url = build_api_url(self.state)

        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                    if r.status != 200:
                        raise ValueError(f"HTTP {r.status}")
                    data = (await r.json()).get("data", [])
        except Exception as e:
            embed = discord.Embed(
                title="❌ Erreur API",
                description=f"YGOPRODeck inaccessible.\n`{e}`",
                color=0xFF0000,
            )
            self._add_replay()
            return await safe_edit(self.message, embed=embed, view=self)

        total = len(data)

        if total == 0:
            embed = discord.Embed(
                title="😵 Je donne ma langue au chat !",
                description=(
                    "Aucune carte ne correspond exactement à tes réponses.\n"
                    "Tu as peut-être répondu à côté quelque part, ou c'est une carte très rare !"
                ),
                color=0xFF4500,
            )
        elif total == 1:
            embed = card_embed(data[0], "🎉 Ta carte est : ")
            embed.description = f"*Trouvé en **{self.nb_asked}** question(s) !*"
            embed.color = 0x00CC66
        else:
            embed = discord.Embed(
                title=f"🔮 Il reste **{total}** cartes possibles !",
                description=f"Après **{self.nb_asked}** questions, j'hésite encore. Voici mes meilleures hypothèses :",
                color=0xFFAA00,
            )
            for c in data[:5]:
                bits = [f"`{c.get('type','')}`"]
                if c.get("level") is not None: bits.append(f"Niv.{c['level']}")
                if c.get("atk")   is not None: bits.append(f"ATK {c['atk']}")
                embed.add_field(name=c["name"], value=" · ".join(bits), inline=False)
            if total > 5:
                embed.set_footer(text=f"… et {total-5} autres. Relance pour affiner !")

        self._add_replay()
        await safe_edit(self.messa