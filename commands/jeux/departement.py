# ================================================================================
# 📌 departements.py — Commande interactive /departement et !departement
# Objectif : Jeu sur les départements français.
#
#   🟢 MODE FACILE : on te donne le NOM du département, tu trouves le NUMÉRO.
#   🔴 MODE HARD   : on te donne une info au hasard, tu en trouves une autre.
#
# Un MENU s'affiche d'abord pour choisir Facile ou Hard, puis la partie démarre.
# Modes : Solo (1 joueur, 2 minutes) et Multi (plusieurs joueurs, 2 minutes)
# Réponses : via bouton (solo = ✍️ Répondre, multi = 🔔 Buzzer)
# Catégorie : Jeux
# Accès : Tous
# Cooldown : 1 utilisation / 10 secondes / utilisateur
# Usage prefix : !departement [numero|nom|prefecture|mix] [m|multi]
# ================================================================================

# ================================================================================
# 📦 Imports nécessaires
# ================================================================================
import asyncio
import logging
import random
from typing import Literal, NamedTuple

import discord
from discord import app_commands
from discord.ext import commands

from utils.discord_utils import safe_edit, safe_send
from utils.jeux_utils import BuzzerView, ReplyView, normalize_text, parse_mode

log = logging.getLogger(__name__)

# ================================================================================
# 📂 Liste des départements français et leurs préfectures
# ================================================================================
DEPARTEMENTS_RAW = {
    "01 - Ain": "Bourg-en-Bresse",
    "02 - Aisne": "Laon",
    "03 - Allier": "Moulins",
    "04 - Alpes-de-Haute-Provence": "Digne-les-Bains",
    "05 - Hautes-Alpes": "Gap",
    "06 - Alpes-Maritimes": "Nice",
    "07 - Ardèche": "Privas",
    "08 - Ardennes": "Charleville-Mézières",
    "09 - Ariège": "Foix",
    "10 - Aube": "Troyes",
    "11 - Aude": "Carcassonne",
    "12 - Aveyron": "Rodez",
    "13 - Bouches-du-Rhône": "Marseille",
    "14 - Calvados": "Caen",
    "15 - Cantal": "Aurillac",
    "16 - Charente": "Angoulême",
    "17 - Charente-Maritime": "La Rochelle",
    "18 - Cher": "Bourges",
    "19 - Corrèze": "Tulle",
    "2A - Corse-du-Sud": "Ajaccio",
    "2B - Haute-Corse": "Bastia",
    "21 - Côte-d'Or": "Dijon",
    "22 - Côtes-d'Armor": "Saint-Brieuc",
    "23 - Creuse": "Guéret",
    "24 - Dordogne": "Périgueux",
    "25 - Doubs": "Besançon",
    "26 - Drôme": "Valence",
    "27 - Eure": "Évreux",
    "28 - Eure-et-Loir": "Chartres",
    "29 - Finistère": "Quimper",
    "30 - Gard": "Nîmes",
    "31 - Haute-Garonne": "Toulouse",
    "32 - Gers": "Auch",
    "33 - Gironde": "Bordeaux",
    "34 - Hérault": "Montpellier",
    "35 - Ille-et-Vilaine": "Rennes",
    "36 - Indre": "Châteauroux",
    "37 - Indre-et-Loire": "Tours",
    "38 - Isère": "Grenoble",
    "39 - Jura": "Lons-le-Saunier",
    "40 - Landes": "Mont-de-Marsan",
    "41 - Loir-et-Cher": "Blois",
    "42 - Loire": "Saint-Étienne",
    "43 - Haute-Loire": "Le Puy-en-Velay",
    "44 - Loire-Atlantique": "Nantes",
    "45 - Loiret": "Orléans",
    "46 - Lot": "Cahors",
    "47 - Lot-et-Garonne": "Agen",
    "48 - Lozère": "Mende",
    "49 - Maine-et-Loire": "Angers",
    "50 - Manche": "Saint-Lô",
    "51 - Marne": "Châlons-en-Champagne",
    "52 - Haute-Marne": "Chaumont",
    "53 - Mayenne": "Laval",
    "54 - Meurthe-et-Moselle": "Nancy",
    "55 - Meuse": "Bar-le-Duc",
    "56 - Morbihan": "Vannes",
    "57 - Moselle": "Metz",
    "58 - Nièvre": "Nevers",
    "59 - Nord": "Lille",
    "60 - Oise": "Beauvais",
    "61 - Orne": "Alençon",
    "62 - Pas-de-Calais": "Arras",
    "63 - Puy-de-Dôme": "Clermont-Ferrand",
    "64 - Pyrénées-Atlantiques": "Pau",
    "65 - Hautes-Pyrénées": "Tarbes",
    "66 - Pyrénées-Orientales": "Perpignan",
    "67 - Bas-Rhin": "Strasbourg",
    "68 - Haut-Rhin": "Colmar",
    "69 - Rhône": "Lyon",
    "70 - Haute-Saône": "Vesoul",
    "71 - Saône-et-Loire": "Mâcon",
    "72 - Sarthe": "Le Mans",
    "73 - Savoie": "Chambéry",
    "74 - Haute-Savoie": "Annecy",
    "75 - Paris": "Paris",
    "76 - Seine-Maritime": "Rouen",
    "77 - Seine-et-Marne": "Melun",
    "78 - Yvelines": "Versailles",
    "79 - Deux-Sèvres": "Niort",
    "80 - Somme": "Amiens",
    "81 - Tarn": "Albi",
    "82 - Tarn-et-Garonne": "Montauban",
    "83 - Var": "Toulon",
    "84 - Vaucluse": "Avignon",
    "85 - Vendée": "La Roche-sur-Yon",
    "86 - Vienne": "Poitiers",
    "87 - Haute-Vienne": "Limoges",
    "88 - Vosges": "Épinal",
    "89 - Yonne": "Auxerre",
    "90 - Territoire de Belfort": "Belfort",
    "91 - Essonne": "Évry-Courcouronnes",
    "92 - Hauts-de-Seine": "Nanterre",
    "93 - Seine-Saint-Denis": "Bobigny",
    "94 - Val-de-Marne": "Créteil",
    "95 - Val-d'Oise": "Cergy",
    "971 - Guadeloupe": "Basse-Terre",
    "972 - Martinique": "Fort-de-France",
    "973 - Guyane": "Cayenne",
    "974 - La Réunion": "Saint-Denis",
    "976 - Mayotte": "Mamoudzou",
}


class Dept(NamedTuple):
    code: str
    nom: str
    pref: str


DEPARTEMENTS: list[Dept] = []
for _key, _pref in DEPARTEMENTS_RAW.items():
    _code, _nom = _key.split(" - ", 1)
    DEPARTEMENTS.append(Dept(_code, _nom, _pref))

# Réponses alternatives acceptées (en plus de la forme complète)
ALIASES = {
    "Évry-Courcouronnes": ["Évry"],
    "Charleville-Mézières": ["Charleville"],
    "Châlons-en-Champagne": ["Châlons", "Châlons-sur-Marne"],
    "Le Puy-en-Velay": ["Le Puy", "Puy-en-Velay"],
    "Cergy": ["Cergy-Pontoise"],
    "Territoire de Belfort": ["Belfort"],
    "La Réunion": ["Réunion"],
    "Clermont-Ferrand": ["Clermont"],
    "Basse-Terre": ["Basseterre"],
}

# ================================================================================
# 🔧 Champs, textes et vérification des réponses
# ================================================================================
FIELDS = ("code", "nom", "pref")

ASK_TEXT = {
    ("code", "nom"):  "Quel département porte ce numéro ?",
    ("code", "pref"): "Quelle est la préfecture du département portant ce numéro ?",
    ("nom", "code"):  "Quel est le numéro de ce département ?",
    ("nom", "pref"):  "Quelle est la préfecture de ce département ?",
    ("pref", "code"): "Quel est le numéro du département dont c'est la préfecture ?",
    ("pref", "nom"):  "De quel département est-ce la préfecture ?",
}

ASKED_LABEL = {"code": "le numéro", "nom": "le département", "pref": "la préfecture"}
MODAL_TEXT = {
    "code": ("🖊️ Devine le numéro", "Entre le numéro", "Exemple : 69"),
    "nom":  ("🖊️ Devine le département", "Entre le département", "Exemple : Rhône"),
    "pref": ("🖊️ Devine la préfecture", "Entre la préfecture", "Exemple : Lyon"),
}

KIND_ASKED = {"numero": "code", "nom": "nom", "prefecture": "pref"}
KIND_ALIASES = {
    "numero": "numero", "numéro": "numero", "num": "numero", "code": "numero",
    "nom": "nom", "departement": "nom", "département": "nom",
    "prefecture": "prefecture", "préfecture": "prefecture", "pref": "prefecture",
    "chef-lieu": "prefecture", "cheflieu": "prefecture", "cl": "prefecture",
    "mix": "mix", "mixte": "mix", "random": "mix", "aleatoire": "mix", "aléatoire": "mix",
}

# 🟢 En mode facile on impose : donné = nom, demandé = numéro
FACILE_GIVEN, FACILE_ASKED = "nom", "code"


def canon_code(text: str) -> str:
    """'01' == '1', '2a' == '2A'."""
    s = text.strip().upper().replace(" ", "")
    return s.lstrip("0") if s.isdigit() else s


def canon_text(text: str) -> str:
    """Normalise accents/tirets/espaces et 'Saint' → 'st' ('St Étienne' = 'Saint-Étienne')."""
    n = normalize_text(text)
    return n.replace("sainte", "ste").replace("saint", "st")


def canon(text: str, field: str) -> str:
    return canon_code(text) if field == "code" else canon_text(text)


def accepted_answers(dept: Dept, field: str) -> set[str]:
    value = getattr(dept, field)
    if field == "code":
        return {canon_code(value)}

    forms = {value, *ALIASES.get(value, [])}
    for form in list(forms):  # on accepte aussi sans article initial ("Mans" pour "Le Mans")
        low = form.lower()
        for art in ("la ", "le ", "les ", "l'"):
            if low.startswith(art):
                forms.add(form[len(art):])
    return {canon_text(f) for f in forms}


def pick_round(kind: str, difficulte: str = "hard") -> tuple[Dept, str, str]:
    """Retourne (département, champ donné, champ demandé)."""
    dept = random.choice(DEPARTEMENTS)

    if difficulte == "facile":
        return dept, FACILE_GIVEN, FACILE_ASKED

    asked = KIND_ASKED.get(kind) or random.choice(FIELDS)
    given = random.choice([f for f in FIELDS if f != asked])
    return dept, given, asked


# ================================================================================
# 🎮 Classe de gestion de l'affichage
# ================================================================================
class DepartementsGame:
    def __init__(self, dept: Dept, given: str, asked: str, author_id: int,
                 multi: bool = False, duration: int = 120, difficulte: str = "hard"):
        self.dept = dept
        self.given = given
        self.asked = asked
        self.author_id = author_id
        self.multi = multi
        self.duration = duration
        self.difficulte = difficulte
        self.finished = False
        self.winner: str | None = None
        self.last_error: str | None = None
        self.attempts: list[dict] = []
        self.message = None
        self.start_time = asyncio.get_event_loop().time()

    @property
    def given_value(self) -> str:
        return getattr(self.dept, self.given)

    @property
    def answer(self) -> str:
        return getattr(self.dept, self.asked)

    def build_embed(self) -> discord.Embed:
        mode_text = "Multi 🌍" if self.multi else "Solo 🧍‍♂️"
        diff_text = "🟢 Facile" if self.difficulte == "facile" else "🔴 Hard"
        title = f"🇫🇷 Départements [{diff_text}] — Trouve {ASKED_LABEL[self.asked]} - Mode {mode_text}"

        action_text = "Clique sur **🔔 Buzzer** pour prendre la main." if self.multi else "Clique sur **✍️ Répondre** pour proposer ta réponse."
        question = ASK_TEXT[(self.given, self.asked)]

        embed = discord.Embed(
            title=title,
            description=f"{question}\n# ➡️ `{self.given_value}`\n{action_text}",
            color=discord.Color.green() if self.difficulte == "facile" else discord.Color.blurple()
        )

        if self.attempts:
            lines = []
            for entry in self.attempts:
                status = "✅" if entry.get('correct') else "❌"
                lines.append(f"{entry['author']}: **{entry['word']}** {status}")
            embed.add_field(name=f"Essais ({len(self.attempts)})", value="\n".join(lines), inline=False)

        if self.last_error and not self.finished:
            embed.add_field(name="⚠️ Remarque", value=self.last_error, inline=False)

        if self.finished:
            recap = f"📍 `{self.dept.code}` — **{self.dept.nom}** · Préfecture : **{self.dept.pref}**"
            if self.winner:
                embed.title = f"{title} — Gagné !"
                embed.color = discord.Color.green()
                embed.description = (
                    f"{question}\n# ➡️ `{self.given_value}`\n\n"
                    f"🏆 **{self.winner}** a trouvé !\n✅ Réponse : **{self.answer}**\n{recap}"
                )
            else:
                embed.title = "⏰ Temps écoulé !"
                embed.color = discord.Color.red()
                embed.description = (
                    f"{question}\n# ➡️ `{self.given_value}`\n\n"
                    f"❌ Personne n'a trouvé. C'était **{self.answer}**.\n{recap}"
                )
            embed.set_footer(text="Partie terminée")
        else:
            elapsed = int(asyncio.get_event_loop().time() - self.start_time)
            remaining = max(0, self.duration - elapsed)
            embed.set_footer(text=f"⏱️ Temps restant : {remaining} secondes")

        return embed


# ================================================================================
# 🎛️ Menu de choix de difficulté
# ================================================================================
class DifficulteView(discord.ui.View):
    """Affiche deux boutons : 🟢 Facile et 🔴 Hard. Renvoie le choix via callback."""

    def __init__(self, author_id: int, on_choice, timeout: float = 30.0):
        super().__init__(timeout=timeout)
        self.author_id = author_id
        self.on_choice = on_choice
        self.message: discord.Message | None = None
        self.choice: str | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "❌ Seul l'auteur de la commande peut choisir la difficulté.",
                ephemeral=True,
            )
            return False
        return True

    async def _choose(self, interaction: discord.Interaction, difficulte: str):
        self.choice = difficulte
        # Désactive les boutons
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()
        await self.on_choice(interaction, difficulte)

    @discord.ui.button(label="Facile", emoji="🟢", style=discord.ButtonStyle.success)
    async def btn_facile(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._choose(interaction, "facile")

    @discord.ui.button(label="Hard", emoji="🔴", style=discord.ButtonStyle.danger)
    async def btn_hard(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._choose(interaction, "hard")

    async def on_timeout(self):
        if self.message:
            try:
                for child in self.children:
                    if isinstance(child, discord.ui.Button):
                        child.disabled = True
                await self.message.edit(view=self)
            except Exception:
                pass


# ================================================================================
# 🧠 Cog principal
# ================================================================================
class Departements(commands.Cog):
    """Commande /departement et !departement — Numéro, département et préfecture"""
    SOLO_TIME  = 120
    MULTI_TIME = 120
    MENU_TIME  = 30

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ============================================================================
    # 🔹 Étape 1 : menu de choix de la difficulté
    # ============================================================================
    async def _ask_difficulte(self, channel, author_id: int, kind: str, multi: bool):
        """Affiche le menu Facile/Hard et lance la partie avec le choix effectué."""

        async def on_choice(interaction: discord.Interaction, difficulte: str):
            # On supprime le menu, puis on lance la partie
            if interaction.message:
                try:
                    await interaction.message.delete()
                except Exception:
                    pass
            await self._send_quiz(channel, author_id=author_id, kind=kind,
                                  multi=multi, difficulte=difficulte)

        view = DifficulteView(author_id=author_id, on_choice=on_choice, timeout=self.MENU_TIME)

        embed = discord.Embed(
            title="🇫🇷 Départements — Choisis ta difficulté",
            description=(
                "🟢 **Facile** — On te donne le **nom** du département, tu trouves le **numéro**.\n"
                "🔴 **Hard** — On te donne une info au hasard (numéro, nom ou préfecture), "
                "tu dois trouver une autre info.\n\n"
                f"*Le menu expire dans {self.MENU_TIME} secondes.*"
            ),
            color=discord.Color.gold(),
        )
        embed.set_footer(text=f"Mode : {'Multi 🌍' if multi else 'Solo 🧍‍♂️'}")

        view.message = await safe_send(channel, embed=embed, view=view)
        if view.message is None:
            return

        # Si le menu expire sans choix, on nettoie
        await view.wait()
        if view.choice is None and view.message:
            try:
                await view.message.delete()
            except Exception:
                pass

    # ============================================================================
    # 🔹 Étape 2 : la partie elle-même
    # ============================================================================
    async def _send_quiz(self, channel, author_id: int, kind: str = "mix",
                         multi: bool = False, difficulte: str = "hard"):
        dept, given, asked = pick_round(kind, difficulte)
        duration = self.MULTI_TIME if multi else self.SOLO_TIME
        game = DepartementsGame(dept, given, asked, author_id, multi, duration, difficulte)
        valid = accepted_answers(dept, asked)

        state = {"finished": False}
        embed = game.build_embed()

        # ── Callback de validation (partagé) ──
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

            # Vérification anti-doublon (avec normalisation)
            if any(canon(entry['word'], asked) == canon(user_answer, asked) for entry in game.attempts):
                game.last_error = f"La réponse `{user_answer}` a déjà été proposée !"
                if game.message:
                    await safe_edit(game.message, embed=game.build_embed())
                return

            is_correct = canon(user_answer, asked) in valid

            game.attempts.append({
                'word': user_answer,
                'author': interaction.user.display_name,
                'correct': is_correct
            })

            # ✅ Bonne réponse
            if is_correct:
                state["finished"] = True
                game.finished = True
                game.winner = interaction.user.mention

                final_embed = game.build_embed()
                await view.mark_finished(embed=final_embed)

            # ❌ Mauvaise réponse
            else:
                if game.message:
                    await safe_edit(game.message, embed=game.build_embed())

        modal_title, modal_label, modal_placeholder = MODAL_TEXT[asked]

        # ── Création de la view selon le mode ──
        if multi:
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

            view = BuzzerView(
                modal_title=modal_title,
                modal_label=modal_label,
                modal_placeholder=modal_placeholder,
                modal_max_length=50,
                on_submit=on_submit,
                on_buzz=on_buzz,
                buzz_timeout=30,
                view_timeout=300,
            )
        else:
            view = ReplyView(
                user_id=author_id,
                modal_title=modal_title,
                modal_label=modal_label,
                modal_placeholder=modal_placeholder,
                modal_max_length=50,
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
        await view.mark_finished(embed=final_embed)

    # ============================================================================
    # 🔹 Commande SLASH
    # ============================================================================
    @app_commands.command(name="departement", description="Numéro, département, préfecture : trouve l'info manquante")
    @app_commands.describe(
        trouve="(hard uniquement) Ce que tu dois trouver : numero, nom, prefecture ou mix",
        mode="solo ou multi (tout le monde peut jouer)",
    )
    @app_commands.checks.cooldown(1, 10.0, key=lambda i: i.user.id)
    async def slash_departements(
        self,
        interaction: discord.Interaction,
        trouve: Literal["mix", "numero", "nom", "prefecture"] = "mix",
        mode: Literal["solo", "multi"] = "solo",
    ):
        await interaction.response.defer()
        await self._ask_difficulte(
            interaction.channel,
            author_id=interaction.user.id,
            kind=trouve,
            multi=parse_mode(mode),
        )
        await interaction.delete_original_response()

    # ============================================================================
    # 🔹 Commande PREFIX
    # ============================================================================
    @commands.command(
        name="departement",
        aliases=["departements", "dep"],
        help="Trouve le numéro, le nom ou la préfecture d'un département. Options : numero|nom|prefecture|mix, m|multi.",
    )
    @commands.cooldown(1, 10.0, commands.BucketType.user)
    async def prefix_departements(self, ctx: commands.Context, *, arg: str = None):
        tokens = (arg or "").lower().split()
        multi = any(parse_mode(t) for t in tokens)
        kind = next((KIND_ALIASES[t] for t in tokens if t in KIND_ALIASES), "mix")
        await self._ask_difficulte(ctx.channel, author_id=ctx.author.id, kind=kind, multi=multi)


# ================================================================================
# 🔌 Setup du Cog
# ================================================================================
async def setup(bot: commands.Bot):
    cog = Departements(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Jeux"
    await bot.add_cog(cog)
