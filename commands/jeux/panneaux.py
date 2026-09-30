# ================================================================================
# 📌 panneaux.py — Commande interactive /panneaux et !panneaux
# Objectif : Deviner la signification d'un panneau du code de la route
# Variantes : QCM (4 boutons A/B/C/D) ou Texte (tape la signification)
# Modes : Solo (1 joueur) et Multi (tout le monde peut jouer)
# Catégorie : Jeux
# Accès : Tous
# Cooldown : 1 utilisation / 10 secondes / utilisateur
# Usage prefix : !panneaux [qcm|texte] [m|multi]
# ================================================================================

# ================================================================================
# 📦 Imports nécessaires
# ================================================================================
import asyncio
import logging
import random
import re
from difflib import SequenceMatcher
from typing import Literal, NamedTuple
from urllib.parse import quote

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

from utils.discord_utils import safe_edit, safe_respond, safe_send
from utils.jeux_utils import BuzzerView, ReplyView, normalize_text, parse_mode

log = logging.getLogger(__name__)

# ================================================================================
# 📂 Base de panneaux (code = fichier Wikimedia Commons "France road sign {code}.svg")
# 4e valeur optionnelle : nom de fichier Commons quand il diffère du code
# ================================================================================
class Sign(NamedTuple):
    code: str
    cat: str
    meaning: str
    file: str | None = None


_RAW_SIGNS = [
    # ---------- A — Danger ----------
    ("A1a", "danger", "Virage à droite"),
    ("A1b", "danger", "Virage à gauche"),
    ("A1c", "danger", "Succession de virages dont le premier est à droite"),
    ("A1d", "danger", "Succession de virages dont le premier est à gauche"),
    ("A2a", "danger", "Cassis ou dos-d'âne"),
    ("A2b", "danger", "Ralentisseur de type dos-d'âne"),
    ("A3", "danger", "Chaussée rétrécie"),
    ("A3a", "danger", "Chaussée rétrécie par la droite"),
    ("A3b", "danger", "Chaussée rétrécie par la gauche"),
    ("A4", "danger", "Chaussée particulièrement glissante"),
    ("A6", "danger", "Pont mobile"),
    ("A7", "danger", "Passage à niveau muni de barrières ou demi-barrières automatiques"),
    ("A8", "danger", "Passage à niveau sans barrières ni demi-barrières"),
    ("A9a", "danger", "Traversée de voie de transport en commun (danger)", "France Road Sign A9a.png"),
    ("A9b", "danger", "Traversée de voies de tramway (danger)", "France road sign A9.svg"),
    ("A13a", "danger", "Endroit fréquenté par les enfants"),
    ("A13b", "danger", "Passage pour piétons (danger)"),
    ("A14", "danger", "Autres dangers"),
    ("A15a1", "danger", "Passage d'animaux domestiques"),
    ("A15a2", "danger", "Passage d'animaux domestiques"),
    ("A15b", "danger", "Passage d'animaux sauvages"),
    ("A15c", "danger", "Passage de cavaliers"),
    ("A16", "danger", "Descente dangereuse"),
    ("A17", "danger", "Annonce de feux tricolores"),
    ("A18", "danger", "Circulation dans les deux sens"),
    ("A19", "danger", "Risque de chute de pierres"),
    ("A20", "danger", "Débouché sur un quai ou une berge"),
    ("A21", "danger", "Débouché de cyclistes venant de droite ou de gauche"),
    ("A23", "danger", "Traversée d'une aire de danger aérien"),
    ("A24", "danger", "Vent latéral"),

    # ---------- AB — Intersections et priorité ----------
    ("AB1", "priorite", "Priorité à droite"),
    ("AB2", "priorite", "Priorité ponctuelle à la prochaine intersection"),
    ("AB3a", "priorite", "Cédez le passage"),
    ("AB3b", "priorite", "Signal avancé de cédez-le-passage"),
    ("AB4", "priorite", "Stop"),
    ("AB5", "priorite", "Signal avancé de stop"),
    ("AB6", "priorite", "Route à caractère prioritaire"),
    ("AB7", "priorite", "Fin de route à caractère prioritaire"),
    ("AB25", "priorite", "Carrefour à sens giratoire"),

    # ---------- B — Interdiction ----------
    ("B0", "interdiction", "Circulation interdite à tout véhicule dans les deux sens"),
    ("B1", "interdiction", "Sens interdit à tout véhicule"),
    ("B1j", "interdiction", "Interdiction d'accès à contresens de bretelle de sortie"),
    ("B2a", "interdiction", "Interdiction de tourner à gauche à la prochaine intersection"),
    ("B2b", "interdiction", "Interdiction de tourner à droite à la prochaine intersection"),
    ("B2c", "interdiction", "Interdiction de faire demi-tour"),
    ("B3", "interdiction", "Interdiction de dépasser tous les véhicules à moteur (sauf deux-roues)"),
    ("B3a", "interdiction", "L'interdiction de dépasser concerne seulement les transports de marchandises de plus de 3,5 tonnes"),
    ("B4", "interdiction", "Arrêt obligatoire au poste de douane"),
    ("B5a", "interdiction", "Arrêt obligatoire au poste de gendarmerie"),
    ("B5b", "interdiction", "Arrêt obligatoire au poste de police"),
    ("B5c", "interdiction", "Arrêt obligatoire au poste de péage"),
    ("B6a1", "interdiction", "Stationnement interdit"),
    ("B6a2", "interdiction", "Stationnement interdit du 1er au 15 du mois"),
    ("B6a3", "interdiction", "Stationnement interdit du 16 à la fin du mois"),
    ("B6d", "interdiction", "Arrêt et stationnement interdits"),
    ("B7a", "interdiction", "Accès interdit aux véhicules à moteur, sauf cyclomoteurs"),
    ("B7b", "interdiction", "Accès interdit à tous les véhicules à moteur"),
    ("B8", "interdiction", "Accès interdit aux véhicules affectés au transport de marchandises"),
    ("B9a", "interdiction", "Accès interdit aux piétons"),
    ("B9b", "interdiction", "Accès interdit aux cycles"),
    ("B9c", "interdiction", "Accès interdit aux véhicules à traction animale"),
    ("B9d", "interdiction", "Accès interdit aux véhicules agricoles à moteur"),
    ("B9e", "interdiction", "Accès interdit aux voitures à bras"),
    ("B9f", "interdiction", "Accès interdit aux véhicules de transport en commun"),
    ("B9g", "interdiction", "Accès interdit aux cyclomoteurs"),
    ("B9h", "interdiction", "Accès interdit aux motocyclettes et motocyclettes légères"),
    ("B9i", "interdiction", "Accès interdit aux véhicules tractant une caravane ou remorque de plus de 250 kg"),
    ("B10a", "interdiction", "Accès interdit aux véhicules dont la longueur dépasse le nombre indiqué"),
    ("B11", "interdiction", "Accès interdit aux véhicules dont la largeur dépasse le nombre indiqué"),
    ("B12", "interdiction", "Accès interdit aux véhicules dont la hauteur dépasse le nombre indiqué"),
    ("B13", "interdiction", "Accès interdit aux véhicules dont le poids total dépasse le nombre indiqué"),
    ("B13a", "interdiction", "Accès interdit aux véhicules dont le poids par essieu dépasse le nombre indiqué"),
    ("B14", "interdiction", "Limitation de vitesse"),
    ("B15", "interdiction", "Cédez le passage à la circulation venant en sens inverse"),
    ("B16", "interdiction", "Signaux sonores interdits"),
    ("B17", "interdiction", "Interdiction de circuler sans maintenir un intervalle minimal entre véhicules"),
    ("B18a", "interdiction", "Accès interdit aux véhicules transportant des marchandises explosives ou inflammables"),
    ("B18b", "interdiction", "Accès interdit aux véhicules transportant des marchandises polluantes pour l'eau"),
    ("B18c", "interdiction", "Accès interdit aux véhicules transportant des matières dangereuses"),
    ("B19", "interdiction", "Autre interdiction précisée par une inscription sur le panneau"),

    # ---------- B — Obligation ----------
    ("B21-1", "obligation", "Obligation de tourner à droite avant le panneau"),
    ("B21-2", "obligation", "Obligation de tourner à gauche avant le panneau"),
    ("B21a1", "obligation", "Contournement obligatoire par la droite"),
    ("B21a2", "obligation", "Contournement obligatoire par la gauche"),
    ("B21b", "obligation", "Direction obligatoire à la prochaine intersection : tout droit"),
    ("B21c1", "obligation", "Direction obligatoire à la prochaine intersection : à droite"),
    ("B21c2", "obligation", "Direction obligatoire à la prochaine intersection : à gauche"),
    ("B21d1", "obligation", "Directions obligatoires : tout droit ou à droite"),
    ("B21d2", "obligation", "Directions obligatoires : tout droit ou à gauche"),
    ("B21e", "obligation", "Directions obligatoires : à droite ou à gauche"),
    ("B22a", "obligation", "Piste ou bande obligatoire pour les cycles"),
    ("B22b", "obligation", "Chemin obligatoire réservé aux piétons"),
    ("B22c", "obligation", "Chemin obligatoire réservé aux cavaliers"),
    ("B25", "obligation", "Vitesse minimale obligatoire", "France road sign B25 (30).svg"),
    ("B26", "obligation", "Chaînes à neige obligatoires sur au moins deux roues motrices"),
    ("B27a", "obligation", "Voie réservée aux véhicules de transport en commun"),
    ("B27b", "obligation", "Voie réservée aux tramways"),
    ("B29", "obligation", "Autre obligation précisée par une inscription sur le panneau"),

    # ---------- B — Fin d'interdiction / d'obligation ----------
    ("B31", "fin", "Fin de toutes les interdictions précédemment signalées"),
    ("B33", "fin", "Fin de limitation de vitesse", "France road sign B33 (50).svg"),
    ("B34", "fin", "Fin d'interdiction de dépasser"),
    ("B34a", "fin", "Fin d'interdiction de dépasser pour les véhicules de transport de marchandises de plus de 3,5 tonnes"),
    ("B35", "fin", "Fin d'interdiction de l'usage de l'avertisseur sonore"),
    ("B39", "fin", "Fin d'une interdiction précisée par une inscription sur le panneau"),
    ("B40", "fin", "Fin de piste ou bande obligatoire pour cycles"),
    ("B41", "fin", "Fin de chemin obligatoire pour piétons"),
    ("B42", "fin", "Fin de chemin obligatoire pour cavaliers"),
    ("B43", "fin", "Fin de vitesse minimale obligatoire", "France road sign B43 (30).svg"),
    ("B44", "fin", "Fin d'obligation de l'usage des chaînes à neige"),
    ("B45", "fin", "Fin de voie réservée aux transports en commun", "France road sign B45a.svg"),
    ("B49", "fin", "Fin d'une obligation précisée par une inscription sur le panneau"),

    # ---------- B — Prescription zonale ----------
    ("B6b1", "zone", "Entrée d'une zone à stationnement interdit"),
    ("B6b2", "zone", "Entrée d'une zone à stationnement unilatéral à alternance semi-mensuelle"),
    ("B6b3", "zone", "Entrée d'une zone à stationnement de durée limitée avec disque"),
    ("B6b4", "zone", "Entrée d'une zone à stationnement payant"),
    ("B6b5", "zone", "Entrée d'une zone à stationnement alterné et limité, avec disque"),
    ("B30", "zone", "Entrée d'une zone à vitesse limitée à 30 km/h", "France road sign B30 (30).svg"),
    ("B50a", "zone", "Sortie de zone à stationnement interdit"),
    ("B50b", "zone", "Sortie de zone à stationnement unilatéral à alternance semi-mensuelle"),
    ("B50c", "zone", "Sortie d'une zone à stationnement de durée limitée avec disque"),
    ("B50d", "zone", "Sortie de zone à stationnement payant"),
    ("B50e", "zone", "Sortie d'une zone à stationnement alterné et limité, avec disque"),
    ("B51", "zone", "Sortie d'une zone à vitesse limitée à 30 km/h", "France road sign B51 (30).svg"),
    ("B52", "zone", "Entrée d'une zone de rencontre"),
    ("B53", "zone", "Sortie d'une zone de rencontre"),
    ("B54", "zone", "Entrée d'une aire piétonne"),
    ("B55", "zone", "Sortie d'une aire piétonne"),
    ("B56", "zone", "Entrée de zone de circulation restreinte"),
    ("B57", "zone", "Sortie de zone de circulation restreinte"),
    ("B58", "zone", "Entrée de zone d'obligation d'équipements en période hivernale"),
    ("B59", "zone", "Sortie de zone d'obligation d'équipements en période hivernale"),

    # ---------- C — Indication ----------
    ("C1a", "indication", "Lieu aménagé pour le stationnement"),
    ("C1b", "indication", "Lieu aménagé pour le stationnement gratuit à durée limitée avec contrôle par disque"),
    ("C1c", "indication", "Lieu aménagé pour le stationnement payant"),
    ("C3", "indication", "Risque d'incendie"),
    ("C4a", "indication", "Vitesse conseillée", "France road sign C4a (50).svg"),
    ("C4b", "indication", "Fin de vitesse conseillée"),
    ("C5", "indication", "Station de taxis"),
    ("C6", "indication", "Arrêt d'autobus"),
    ("C8", "indication", "Emplacement d'arrêt d'urgence"),
    ("C9", "indication", "Station d'autopartage"),
    ("C12", "indication", "Circulation à sens unique"),
    ("C13a", "indication", "Impasse"),
    ("C13b", "indication", "Présignalisation d'une impasse"),
    ("C13c", "indication", "Impasse avec issue pour piétons"),
    ("C13d", "indication", "Impasse avec issue pour piétons et cyclistes"),
    ("C18", "indication", "Priorité par rapport à la circulation venant en sens inverse"),
    ("C20a", "indication", "Passage pour piétons (indication)"),
    ("C20b", "indication", "Traversée de voie de transport en commun (indication)"),
    ("C20c", "indication", "Traversée de voies de tramway (indication)"),
    ("C23", "indication", "Stationnement réglementé pour caravanes et autocaravanes"),
    ("C25a", "indication", "Limites de vitesse en France, aux frontières"),
    ("C25b", "indication", "Rappel des limites de vitesse sur autoroute"),
    ("C26a", "indication", "Voie de détresse à droite"),
    ("C26b", "indication", "Voie de détresse à gauche"),
    ("C27", "indication", "Surélévation de chaussée"),
    ("C28", "indication", "Réduction du nombre de voies sur route à chaussées séparées"),
    ("C29a", "indication", "Présignalisation d'un créneau de dépassement"),
    ("C30", "indication", "Fin d'un créneau de dépassement à trois voies"),
    ("C107", "indication", "Début d'une route à accès réglementé"),
    ("C108", "indication", "Fin de route à accès réglementé"),
    ("C111", "indication", "Entrée d'un tunnel"),
    ("C112", "indication", "Sortie de tunnel"),
    ("C113", "indication", "Piste ou bande cyclable conseillée et réservée aux cycles"),
    ("C114", "indication", "Fin de piste ou bande cyclable conseillée"),
    ("C115", "indication", "Voie verte, réservée aux piétons et véhicules non motorisés"),
    ("C116", "indication", "Fin de voie verte"),
    ("C207", "indication", "Début d'une section d'autoroute"),
    ("C208", "indication", "Fin d'une section d'autoroute"),

    # ---------- CE — Service ----------
    ("CE1", "service", "Poste de secours"),
    ("CE2a", "service", "Poste d'appel d'urgence"),
    ("CE2b", "service", "Cabine téléphonique publique"),
    ("CE3a", "service", "Informations touristiques"),
    ("CE4a", "service", "Terrain de camping pour tentes"),
    ("CE4b", "service", "Terrain de camping pour caravanes et autocaravanes"),
    ("CE4c", "service", "Terrain de camping pour tentes, caravanes et autocaravanes"),
    ("CE5a", "service", "Auberge de jeunesse"),
    ("CE5b", "service", "Chambre d'hôtes ou gîte"),
    ("CE6a", "service", "Point de départ d'un itinéraire pédestre"),
    ("CE6b", "service", "Point de départ d'un circuit de ski de fond"),
    ("CE7", "service", "Emplacement pour pique-nique"),
    ("CE8", "service", "Gare auto/train"),
    ("CE9", "service", "Parc de stationnement sous vidéoprotection"),
    ("CE10", "service", "Embarcadère"),
    ("CE12", "service", "Toilettes ouvertes au public"),
    ("CE14", "service", "Installations accessibles aux personnes à mobilité réduite"),
    ("CE15a", "service", "Poste de distribution de carburant ouvert 24h/24, 7j/7"),
    ("CE15g", "service", "Poste de carburant 24h/24 assurant la recharge des véhicules électriques"),
    ("CE15i", "service", "Poste de recharge de véhicules électriques ouvert 24h/24, 7j/7"),
    ("CE16", "service", "Restaurant"),
    ("CE17", "service", "Hôtel ou motel"),
    ("CE18", "service", "Débit de boissons ou collations"),
    ("CE19", "service", "Mise à l'eau d'embarcations légères"),
    ("CE20a", "service", "Gare de téléphérique"),
    ("CE20b", "service", "Point de départ d'un télésiège ou d'une télécabine"),
    ("CE21", "service", "Point de vue"),
    ("CE23", "service", "Jeux d'enfants"),
    ("CE24", "service", "Station de vidange pour caravanes et autocaravanes"),
    ("CE25", "service", "Distributeur de billets de banque"),
    ("CE26", "service", "Station de gonflage gratuite"),
    ("CE27", "service", "Point de détente"),
    ("CE28", "service", "Poste de dépannage"),
    ("CE29", "service", "Moyen de lutte contre l'incendie"),
    ("CE30a", "service", "Issue de secours vers la droite"),
    ("CE30b", "service", "Issue de secours vers la gauche"),
    ("CE52", "service", "Lieu aménagé pour la pratique du covoiturage"),

    # ---------- AK / KC — Signalisation temporaire ----------
    ("AK2", "temporaire", "Cassis ou dos-d'âne (temporaire)"),
    ("AK3", "temporaire", "Chaussée rétrécie (temporaire)"),
    ("AK4", "temporaire", "Chaussée glissante (temporaire)"),
    ("AK5", "temporaire", "Travaux"),
    ("AK14", "temporaire", "Autres dangers (temporaire)"),
    ("AK17", "temporaire", "Annonce de feux tricolores (temporaire)"),
    ("AK22", "temporaire", "Projection de gravillons"),
    ("AK30", "temporaire", "Bouchon"),
    ("AK31", "temporaire", "Accident"),
    ("AK32", "temporaire", "Nappes de brouillard ou de fumées épaisses"),
    ("KC1", "temporaire", "Route barrée", "KC1 route barrée.svg"),
]

SIGNS: list[Sign] = [Sign(*row) for row in _RAW_SIGNS]

CAT_LABELS = {
    "danger": "Danger",
    "priorite": "Intersections et priorité",
    "interdiction": "Interdiction",
    "obligation": "Obligation",
    "fin": "Fin d'interdiction ou d'obligation",
    "zone": "Prescription zonale",
    "indication": "Indication",
    "service": "Service",
    "temporaire": "Signalisation temporaire",
}

LETTERS = "ABCD"
FUZZY_THRESHOLD = 0.85
HTTP_HEADERS = {"User-Agent": "KisukeUraharaBot/1.0 (Discord bot; jeu panneaux)"}

# ================================================================================
# 🔧 Helpers texte
# ================================================================================
def clean_meaning(text: str) -> str:
    """Retire les précisions entre parenthèses : 'Passage pour piétons (danger)' → 'Passage pour piétons'."""
    return re.sub(r"\s*\([^)]*\)", "", text).strip()


# Toutes les significations connues (normalisées), pour la vérification floue
_NORMALIZED_MEANINGS = sorted({normalize_text(clean_meaning(s.meaning)) for s in SIGNS})


def is_correct_text(guess: str, sign: Sign) -> bool:
    """
    Réponse valide si elle correspond (aux fautes de frappe près) à la bonne signification.
    On compare avec TOUTES les significations : si la saisie ressemble plus à un
    autre panneau (ex. 'gauche' au lieu de 'droite'), c'est faux.
    """
    target = normalize_text(clean_meaning(sign.meaning))
    g = normalize_text(clean_meaning(guess))
    if not g:
        return False
    if g == target:
        return True

    best = max(_NORMALIZED_MEANINGS, key=lambda m: SequenceMatcher(None, g, m).ratio())
    return best == target and SequenceMatcher(None, g, target).ratio() >= FUZZY_THRESHOLD


def pick_distractors(sign: Sign, count: int = 3) -> list[str]:
    """Mauvaises réponses : d'abord la même catégorie, puis le reste. Jamais deux fois le même texte."""
    target = clean_meaning(sign.meaning)
    same_cat = [s for s in SIGNS if s.cat == sign.cat]
    other_cat = [s for s in SIGNS if s.cat != sign.cat]
    random.shuffle(same_cat)
    random.shuffle(other_cat)

    seen = {target}
    result: list[str] = []
    for s in same_cat + other_cat:
        text = clean_meaning(s.meaning)
        if text in seen:
            continue
        seen.add(text)
        result.append(text)
        if len(result) == count:
            break
    return result


# ================================================================================
# 🌐 Images (Wikimedia Commons)
# ================================================================================
def sign_image_url(sign: Sign) -> str:
    filename = sign.file or f"France road sign {sign.code}.svg"
    return (
        "https://commons.wikimedia.org/wiki/Special:FilePath/"
        + quote(filename.replace(" ", "_"))
        + "?width=400"
    )


_IMAGE_OK: dict[str, bool] = {}


async def _head_ok(session: aiohttp.ClientSession, url: str) -> bool:
    timeout = aiohttp.ClientTimeout(total=6)
    async with session.head(url, allow_redirects=True, timeout=timeout, headers=HTTP_HEADERS) as resp:
        return resp.status == 200 and resp.content_type.startswith("image")


async def image_available(bot: commands.Bot, url: str) -> bool:
    """Vérifie que l'image existe sur Commons (les codes récents n'ont pas toujours d'illustration)."""
    if url in _IMAGE_OK:
        return _IMAGE_OK[url]
    try:
        session = getattr(bot, "aiohttp_session", None)
        if session is None:
            async with aiohttp.ClientSession() as temp_session:
                ok = await _head_ok(temp_session, url)
        else:
            ok = await _head_ok(session, url)
    except Exception as e:
        # Problème réseau : on ne bloque pas le jeu, et on ne met rien en cache
        log.warning("[panneaux] Vérification image impossible : %s", e)
        return True
    _IMAGE_OK[url] = ok
    return ok


# ================================================================================
# 🔹 View QCM (boutons A / B / C / D)
# ================================================================================
class QcmButton(discord.ui.Button):
    def __init__(self, choice: int):
        super().__init__(label=LETTERS[choice], style=discord.ButtonStyle.secondary)
        self.choice = choice

    async def callback(self, interaction: discord.Interaction):
        await self.view.handle(interaction, self.choice)


class QcmView(discord.ui.View):
    """4 boutons de réponse. Solo : seul l'auteur joue. Multi : 1 essai par joueur."""

    def __init__(self, author_id: int, multi: bool, on_answer, nb_options: int = 4, timeout: int = 300):
        super().__init__(timeout=timeout)
        self.author_id = author_id
        self.multi     = multi
        self.on_answer = on_answer
        self.answered: set[int] = set()
        self.message   = None
        self.finished  = False
        for i in range(nb_options):
            self.add_item(QcmButton(i))

    async def handle(self, interaction: discord.Interaction, choice: int):
        if self.finished:
            await safe_respond(interaction, "❌ La partie est terminée.", ephemeral=True)
            return
        if not self.multi and interaction.user.id != self.author_id:
            await safe_respond(interaction, "❌ Ce n'est pas ton jeu.", ephemeral=True)
            return
        if interaction.user.id in self.answered:
            await safe_respond(interaction, "❌ Tu as déjà répondu.", ephemeral=True)
            return

        self.answered.add(interaction.user.id)
        await self.on_answer(interaction, choice)

    def mark_wrong(self, choice: int):
        """Grise un mauvais choix (visible par tout le monde)."""
        for child in self.children:
            if isinstance(child, QcmButton) and child.choice == choice:
                child.style = discord.ButtonStyle.danger
                child.disabled = True

    async def mark_finished(self, embed=None, correct_index: int | None = None):
        self.finished = True
        for child in self.children:
            child.disabled = True
            if isinstance(child, QcmButton) and child.choice == correct_index:
                child.style = discord.ButtonStyle.success
        if self.message:
            try:
                if embed is not None:
                    await safe_edit(self.message, embed=embed, view=self)
                else:
                    await safe_edit(self.message, view=self)
            except Exception:
                pass

    async def on_timeout(self):
        self.finished = True
        for child in self.children:
            child.disabled = True
        if self.message:
            try:
                await safe_edit(self.message, view=self)
            except Exception:
                pass


# ================================================================================
# 🎮 Classe de gestion de la partie
# ================================================================================
class PanneauxGame:
    def __init__(
        self,
        sign: Sign,
        image_url: str,
        kind: str,
        author_id: int,
        multi: bool,
        duration: int,
        options: list[str] | None = None,
        correct_index: int | None = None,
    ):
        self.sign          = sign
        self.image_url     = image_url
        self.kind          = kind            # "qcm" | "texte"
        self.author_id     = author_id
        self.multi         = multi
        self.duration      = duration
        self.options       = options or []
        self.correct_index = correct_index
        # QCM : 1 essai par joueur ; Texte solo : 3 essais ; Texte multi : illimité
        self.max_attempts  = 3 if (kind == "texte" and not multi) else None
        self.attempts: list[dict] = []
        self.finished      = False
        self.winner: str | None = None
        self.last_error: str | None = None
        self.message       = None
        self.start_time    = asyncio.get_event_loop().time()

    @property
    def answer_text(self) -> str:
        return clean_meaning(self.sign.meaning)

    def build_embed(self) -> discord.Embed:
        kind_text = "QCM 🔠" if self.kind == "qcm" else "Texte ✍️"
        mode_text = "Multi 🌍" if self.multi else "Solo 🧍‍♂️"
        title = f"🚦 Panneaux - {kind_text} {mode_text}"

        if self.kind == "qcm":
            action = "Clique sur la bonne réponse (**A**, **B**, **C** ou **D**)."
            if self.multi:
                action += "\nUn seul essai par joueur !"
        elif self.multi:
            action = "Clique sur **🔔 Buzzer** pour prendre la main."
        else:
            action = "Clique sur **✍️ Répondre** pour proposer ta réponse."

        embed = discord.Embed(
            title=title,
            description=f"Que signifie ce panneau ?\n{action}",
            color=discord.Color.blurple(),
        )
        embed.set_image(url=self.image_url)

        if self.kind == "qcm":
            lines = [f"**{LETTERS[i]}.** {text}" for i, text in enumerate(self.options)]
            embed.add_field(name="Propositions", value="\n".join(lines), inline=False)
        else:
            embed.add_field(name="💡 Indice", value=f"Catégorie : **{CAT_LABELS.get(self.sign.cat, self.sign.cat)}**", inline=False)

        if self.attempts:
            lines = []
            for entry in self.attempts:
                status = "✅" if entry.get("correct") else "❌"
                lines.append(f"{entry['author']}: **{entry['word']}** {status}")
            if self.max_attempts:
                field_name = f"Essais ({len(self.attempts)}/{self.max_attempts})"
            else:
                field_name = f"Essais ({len(self.attempts)})"
            embed.add_field(name=field_name, value="\n".join(lines), inline=False)

        if self.last_error and not self.finished:
            embed.add_field(name="⚠️ Remarque", value=self.last_error, inline=False)

        if self.finished:
            reveal = f"✅ Réponse : **{self.answer_text}**\n🔖 Code : `{self.sign.code}`"
            if self.winner:
                embed.title = f"{title} — Gagné !"
                embed.color = discord.Color.green()
                embed.description = f"🏆 **{self.winner}** a trouvé !\n{reveal}"
            else:
                embed.title = "🚦 Panneaux - Perdu"
                embed.color = discord.Color.red()
                embed.description = f"❌ Personne n'a trouvé.\n{reveal}"
            embed.set_footer(text="Partie terminée")
        else:
            elapsed = int(asyncio.get_event_loop().time() - self.start_time)
            remaining = max(0, self.duration - elapsed)
            embed.set_footer(text=f"⏱️ Temps restant : {remaining} secondes")

        return embed


# ================================================================================
# 🧠 Cog principal
# ================================================================================
class Panneaux(commands.Cog):
    """Commande /panneaux et !panneaux — Deviner la signification d'un panneau"""

    DURATIONS = {"qcm": 90, "texte": 180}

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ============================================================================
    # 🔹 Tirage d'un panneau dont l'image existe
    # ============================================================================
    async def _pick_sign(self) -> tuple[Sign, str] | None:
        for _ in range(6):
            sign = random.choice(SIGNS)
            url = sign_image_url(sign)
            if await image_available(self.bot, url):
                return sign, url
        return None

    # ============================================================================
    # 🔹 Fonction interne commune
    # ============================================================================
    async def _start_game(self, channel: discord.abc.Messageable, author_id: int, kind: str = "qcm", multi: bool = False):
        picked = await self._pick_sign()
        if picked is None:
            await safe_send(channel, "❌ Impossible de charger les images de panneaux pour le moment, réessaie plus tard.")
            return
        sign, image_url = picked

        duration = self.DURATIONS[kind]
        options = None
        correct_index = None
        if kind == "qcm":
            options = [clean_meaning(sign.meaning)] + pick_distractors(sign, 3)
            random.shuffle(options)
            correct_index = options.index(clean_meaning(sign.meaning))

        game = PanneauxGame(sign, image_url, kind, author_id, multi, duration, options, correct_index)
        state = {"finished": False}
        embed = game.build_embed()

        async def finish(winner: str | None):
            state["finished"] = True
            game.finished = True
            game.winner = winner
            await view.mark_finished(embed=game.build_embed(), **({"correct_index": game.correct_index} if kind == "qcm" else {}))

        # ── Callback QCM ──
        async def on_answer(interaction: discord.Interaction, choice: int):
            if not interaction.response.is_done():
                await interaction.response.defer()
            if state["finished"]:
                return

            is_correct = (choice == game.correct_index)
            game.attempts.append({
                "word": LETTERS[choice],
                "author": interaction.user.display_name,
                "correct": is_correct,
            })

            if is_correct:
                await finish(interaction.user.mention)
            elif not game.multi:
                view.mark_wrong(choice)
                await finish(None)
            else:
                view.mark_wrong(choice)
                if game.message:
                    await safe_edit(game.message, embed=game.build_embed(), view=view)

        # ── Callback Texte ──
        async def on_submit(interaction: discord.Interaction, answer: str):
            if not interaction.response.is_done():
                await interaction.response.defer()
            if state["finished"]:
                return
            if not game.multi and interaction.user.id != game.author_id:
                return

            user_answer = answer.strip()
            game.last_error = None
            if not user_answer:
                return

            # Anti-doublon (avec normalisation)
            if any(normalize_text(e["word"]) == normalize_text(user_answer) for e in game.attempts):
                game.last_error = f"La réponse `{user_answer}` a déjà été proposée !"
                if game.message:
                    await safe_edit(game.message, embed=game.build_embed())
                return

            is_correct = is_correct_text(user_answer, sign)
            game.attempts.append({
                "word": user_answer,
                "author": interaction.user.display_name,
                "correct": is_correct,
            })

            if is_correct:
                await finish(interaction.user.mention)
            elif game.max_attempts and len(game.attempts) >= game.max_attempts:
                await finish(None)
            elif game.message:
                await safe_edit(game.message, embed=game.build_embed())

        # ── Callback buzz (texte multi) ──
        async def on_buzz(user: discord.User | discord.Member):
            if view.message:
                for child in view.children:
                    if isinstance(child, discord.ui.Button):
                        child.disabled = True
                current_embed = game.build_embed()
                elapsed = int(asyncio.get_event_loop().time() - game.start_time)
                remaining = max(0, game.duration - elapsed)
                current_embed.set_footer(text=f"🎯 Main prise par {user.display_name} | ⏱️ Temps restant : {remaining}s")
                await safe_edit(view.message, embed=current_embed, view=view)

        # ── Création de la view selon la variante ──
        if kind == "qcm":
            view = QcmView(author_id=author_id, multi=multi, on_answer=on_answer, nb_options=len(options), timeout=300)
        elif multi:
            view = BuzzerView(
                modal_title="🖊️ Signification du panneau",
                modal_label="Que signifie ce panneau ?",
                modal_placeholder="Exemple : Virage à droite",
                modal_max_length=120,
                on_submit=on_submit,
                on_buzz=on_buzz,
                buzz_timeout=45,
                view_timeout=300,
            )
        else:
            view = ReplyView(
                user_id=author_id,
                modal_title="🖊️ Signification du panneau",
                modal_label="Que signifie ce panneau ?",
                modal_placeholder="Exemple : Virage à droite",
                modal_max_length=120,
                on_submit=on_submit,
                timeout=300,
            )

        view.message = await safe_send(channel, embed=embed, view=view)
        if view.message is None:
            return
        game.message = view.message

        # ── Attente ──
        try:
            await asyncio.sleep(duration)
        except asyncio.CancelledError:
            return

        if state["finished"]:
            return

        # ── Fin du temps ──
        game.finished = True
        final_embed = game.build_embed()
        final_embed.title = "⏰ Temps écoulé !"
        if kind == "qcm":
            await view.mark_finished(embed=final_embed, correct_index=game.correct_index)
        else:
            await view.mark_finished(embed=final_embed)

    # ============================================================================
    # 🔹 Commande SLASH
    # ============================================================================
    @app_commands.command(name="panneaux", description="Devine la signification d'un panneau du code de la route")
    @app_commands.describe(
        variante="qcm (4 choix) ou texte (tape la signification)",
        mode="solo ou multi (tout le monde peut jouer)",
    )
    @app_commands.checks.cooldown(1, 10.0, key=lambda i: i.user.id)
    async def slash_panneaux(
        self,
        interaction: discord.Interaction,
        variante: Literal["qcm", "texte"] = "qcm",
        mode: Literal["solo", "multi"] = "solo",
    ):
        await interaction.response.defer()
        await self._start_game(interaction.channel, author_id=interaction.user.id, kind=variante, multi=parse_mode(mode))
        await interaction.delete_original_response()

    # ============================================================================
    # 🔹 Commande PREFIX
    # ============================================================================
    @commands.command(
        name="panneaux",
        help="Devine un panneau du code de la route. Options : qcm ou texte, et m/multi pour jouer en multi.",
    )
    @commands.cooldown(1, 10.0, commands.BucketType.user)
    async def prefix_panneaux(self, ctx: commands.Context, *, arg: str = None):
        tokens = (arg or "").lower().split()
        multi = any(parse_mode(t) for t in tokens)
        kind = "texte" if any(t in ("texte", "text", "t") for t in tokens) else "qcm"
        await self._start_game(ctx.channel, author_id=ctx.author.id, kind=kind, multi=multi)


# ================================================================================
# 🔌 Setup du Cog
# ================================================================================
async def setup(bot: commands.Bot):
    cog = Panneaux(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Jeux"
    await bot.add_cog(cog)
