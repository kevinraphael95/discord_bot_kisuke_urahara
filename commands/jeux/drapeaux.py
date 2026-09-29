# ================================================================================
# 📌 drapeaux.py — Commande interactive /drapeaux et !drapeaux
# Objectif : Deviner le pays à partir d'un drapeau aléatoire (tous les pays)
# Modes : Solo (1 joueur, 2 minutes) et Multi (plusieurs joueurs, 2 minutes)
# Réponses : via bouton (solo = ✍️ Répondre, multi = 🔔 Buzzer)
# Catégorie : Jeux
# Accès : Tous
# Cooldown : 1 utilisation / 10 secondes / utilisateur
# ================================================================================

# ================================================================================
# 📦 Imports nécessaires
# ================================================================================
import asyncio
import logging
import random

import discord
from discord import app_commands
from discord.ext import commands

from utils.discord_utils import safe_edit, safe_send
from utils.jeux_utils import BuzzerView, ReplyView, normalize_text, parse_mode

log = logging.getLogger(__name__)

# ================================================================================
# 📂 Liste complète des pays et codes ISO
# ================================================================================
COUNTRIES = {
    "Afghanistan": "af", "Afrique du Sud": "za", "Albanie": "al", "Algérie": "dz",
    "Allemagne": "de", "Andorre": "ad", "Angola": "ao", "Antigua-et-Barbuda": "ag",
    "Arabie saoudite": "sa", "Argentine": "ar", "Arménie": "am", "Australie": "au",
    "Autriche": "at", "Azerbaïdjan": "az", "Bahamas": "bs", "Bahreïn": "bh",
    "Bangladesh": "bd", "Barbade": "bb", "Belgique": "be", "Belize": "bz",
    "Bénin": "bj", "Bhoutan": "bt", "Biélorussie": "by", "Birmanie": "mm",
    "Bolivie": "bo", "Bosnie-Herzégovine": "ba", "Botswana": "bw", "Brésil": "br",
    "Brunei": "bn", "Bulgarie": "bg", "Burkina Faso": "bf", "Burundi": "bi",
    "Cambodge": "kh", "Cameroun": "cm", "Canada": "ca", "Cap-Vert": "cv",
    "Chili": "cl", "Chine": "cn", "Chypre": "cy", "Colombie": "co",
    "Comores": "km", "Congo": "cg", "Corée du Nord": "kp", "Corée du Sud": "kr",
    "Costa Rica": "cr", "Croatie": "hr", "Cuba": "cu", "Danemark": "dk",
    "Djibouti": "dj", "Dominique": "dm", "Égypte": "eg", "Émirats arabes unis": "ae",
    "Équateur": "ec", "Érythrée": "er", "Espagne": "es", "Estonie": "ee",
    "Eswatini": "sz", "États-Unis": "us", "Éthiopie": "et", "Fidji": "fj",
    "Finlande": "fi", "France": "fr", "Gabon": "ga", "Gambie": "gm",
    "Géorgie": "ge", "Ghana": "gh", "Grèce": "gr", "Grenade": "gd",
    "Guatemala": "gt", "Guinée": "gn", "Guinée-Bissau": "gw", "Guinée équatoriale": "gq",
    "Guyana": "gy", "Haïti": "ht", "Honduras": "hn", "Hongrie": "hu",
    "Îles Marshall": "mh", "Îles Salomon": "sb", "Inde": "in", "Indonésie": "id",
    "Iran": "ir", "Irak": "iq", "Irlande": "ie", "Islande": "is",
    "Israël": "il", "Italie": "it", "Jamaïque": "jm", "Japon": "jp",
    "Jordanie": "jo", "Kazakhstan": "kz", "Kenya": "ke", "Kirghizistan": "kg",
    "Kiribati": "ki", "Koweït": "kw", "Laos": "la", "Lesotho": "ls",
    "Lettonie": "lv", "Liban": "lb", "Liberia": "lr", "Libye": "ly",
    "Liechtenstein": "li", "Lituanie": "lt", "Luxembourg": "lu", "Madagascar": "mg",
    "Malaisie": "my", "Malawi": "mw", "Maldives": "mv", "Mali": "ml",
    "Malte": "mt", "Maroc": "ma", "Maurice": "mu", "Mauritanie": "mr",
    "Mexique": "mx", "Micronésie": "fm", "Moldavie": "md", "Monaco": "mc",
    "Mongolie": "mn", "Monténégro": "me", "Mozambique": "mz", "Namibie": "na",
    "Nauru": "nr", "Népal": "np", "Nicaragua": "ni", "Niger": "ne",
    "Nigéria": "ng", "Norvège": "no", "Nouvelle-Zélande": "nz", "Oman": "om",
    "Ouganda": "ug", "Ouzbékistan": "uz", "Pakistan": "pk", "Palaos": "pw",
    "Panama": "pa", "Papouasie-Nouvelle-Guinée": "pg", "Paraguay": "py", "Pays-Bas": "nl",
    "Pérou": "pe", "Philippines": "ph", "Pologne": "pl", "Portugal": "pt",
    "Qatar": "qa", "République centrafricaine": "cf", "République dominicaine": "do",
    "République tchèque": "cz", "Roumanie": "ro", "Royaume-Uni": "gb", "Russie": "ru",
    "Rwanda": "rw", "Saint-Christophe-et-Niévès": "kn", "Sainte-Lucie": "lc",
    "Saint-Marin": "sm", "Saint-Vincent-et-les-Grenadines": "vc", "Salvador": "sv",
    "Samoa": "ws", "Sao Tomé-et-Principe": "st", "Sénégal": "sn", "Serbie": "rs",
    "Seychelles": "sc", "Sierra Leone": "sl", "Singapour": "sg", "Slovaquie": "sk",
    "Slovénie": "si", "Somalie": "so", "Soudan": "sd", "Soudan du Sud": "ss",
    "Sri Lanka": "lk", "Suède": "se", "Suisse": "ch", "Syrie": "sy",
    "Taïwan": "tw", "Tadjikistan": "tj", "Tanzanie": "tz", "Thaïlande": "th",
    "Timor oriental": "tl", "Togo": "tg", "Tonga": "to", "Trinité-et-Tobago": "tt",
    "Tunisie": "tn", "Turkménistan": "tm", "Turquie": "tr", "Tuvalu": "tv",
    "Ukraine": "ua", "Uruguay": "uy", "Vanuatu": "vu", "Vatican": "va",
    "Venezuela": "ve", "Viêt Nam": "vn", "Yémen": "ye", "Zambie": "zm",
    "Zimbabwe": "zw"
}

def get_flag_url(iso_code: str) -> str:
    return f"https://flagcdn.com/w320/{iso_code}.png"

# ================================================================================
# 🎮 Classe de gestion du jeu
# ================================================================================
class DrapeauxGame:
    def __init__(self, country: str, iso_code: str, author_id: int, multi: bool = False, duration: int = 120):
        self.country = country
        self.flag_url = get_flag_url(iso_code)
        self.author_id = author_id
        self.multi = multi
        self.duration = duration
        self.finished = False
        self.winner: str | None = None
        self.last_error: str | None = None
        self.attempts: list[dict] = []
        self.message = None
        self.start_time = asyncio.get_event_loop().time()

    def build_embed(self) -> discord.Embed:
        mode_text = "Multijoueur 🌍" if self.multi else "Solo 🧍‍♂️"
        title = f"🚩 Devine le Drapeau - Mode {mode_text}"

        action_text = "Clique sur **🔔 Buzzer** pour prendre la main." if self.multi else "Clique sur **✍️ Répondre** pour proposer ta réponse."
        description = f"Quel est ce pays ?\n{action_text}"

        embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Color.blurple()
        )
        embed.set_image(url=self.flag_url)

        if self.attempts:
            lines = []
            for entry in self.attempts:
                status = "✅" if entry.get('correct') else "❌"
                lines.append(f"{entry['author']}: **{entry['word']}** {status}")
            tries_text = "\n".join(lines)
            embed.add_field(name=f"Essais ({len(self.attempts)})", value=tries_text, inline=False)

        if self.last_error and not self.finished:
            embed.add_field(name="⚠️ Remarque", value=self.last_error, inline=False)

        if self.finished:
            if self.winner:
                embed.title = f"{title} — Gagné !"
                embed.color = discord.Color.green()
                embed.description = f"Quel est ce pays ?\n\n🏆 **{self.winner}** a trouvé !\n✅ Réponse : **{self.country}**"
            else:
                embed.title = "⏰ Temps écoulé !"
                embed.color = discord.Color.red()
                embed.description = f"Quel est ce pays ?\n\n❌ Personne n'a trouvé. C'était **{self.country}**."
            embed.set_footer(text="Partie terminée")
        else:
            elapsed = int(asyncio.get_event_loop().time() - self.start_time)
            remaining = max(0, self.duration - elapsed)
            embed.set_footer(text=f"⏱️ Temps restant : {remaining} secondes")

        return embed

# ================================================================================
# 🧠 Cog principal
# ================================================================================
class Drapeaux(commands.Cog):
    """Commande /drapeaux et !drapeaux — Deviner le pays à partir d'un drapeau"""

    SOLO_TIME  = 120
    MULTI_TIME = 120

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ============================================================================
    # 🔹 Fonction interne commune
    # ============================================================================
    async def _send_quiz(self, channel, author_id: int, multi: bool = False):
        country, iso_code = random.choice(list(COUNTRIES.items()))
        duration = self.MULTI_TIME if multi else self.SOLO_TIME
        game = DrapeauxGame(country, iso_code, author_id, multi, duration)

        state = {"finished": False}
        embed = game.build_embed()

        # ── Callback de validation ──
        async def on_submit(interaction: discord.Interaction, answer: str):
            if not interaction.response.is_done():
                await interaction.response.defer()

            if state["finished"]:
                return

            if not game.multi and interaction.user.id != game.author_id:
                return

            user_answer = answer.strip()
            if not user_answer:
                return

            game.last_error = None

            # Vérification anti-doublon (avec normalisation)
            if any(normalize_text(entry['word']) == normalize_text(user_answer) for entry in game.attempts):
                game.last_error = f"Le pays `{user_answer}` a déjà été proposé !"
                if game.message:
                    await safe_edit(game.message, embed=game.build_embed())
                return

            is_correct = (normalize_text(user_answer) == normalize_text(country))

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

        # ── Callback quand quelqu'un buzze (multi seulement) ──
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

        # ── Vue selon le mode ──
        if multi:
            view = BuzzerView(
                modal_title="🖊️ Devine le pays",
                modal_label="Entre le nom du pays",
                modal_placeholder="Exemple : France",
                modal_max_length=50,
                on_submit=on_submit,
                on_buzz=on_buzz,
                buzz_timeout=30,
                view_timeout=300,
            )
        else:
            view = ReplyView(
                user_id=author_id,
                modal_title="🖊️ Devine le pays",
                modal_label="Entre le nom du pays",
                modal_placeholder="Exemple : France",
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
    @app_commands.command(name="drapeaux", description="Devine le pays à partir d'un drapeau")
    @app_commands.describe(mode="Tapez 'm' ou 'multi' pour le mode multijoueur")
    @app_commands.checks.cooldown(1, 10.0, key=lambda i: i.user.id)
    async def slash_drapeaux(self, interaction: discord.Interaction, mode: str = None):
        await interaction.response.defer()
        multi = parse_mode(mode)
        await self._send_quiz(interaction.channel, author_id=interaction.user.id, multi=multi)
        await interaction.delete_original_response()

    # ============================================================================
    # 🔹 Commande PREFIX
    # ============================================================================
    @commands.command(name="drapeaux", help="Devine le pays à partir d'un drapeau")
    @commands.cooldown(1, 10.0, commands.BucketType.user)
    async def prefix_drapeaux(self, ctx: commands.Context, *, arg: str = None):
        multi = parse_mode(arg)
        await self._send_quiz(ctx.channel, author_id=ctx.author.id, multi=multi)


# ================================================================================
# 🔌 Setup du Cog
# ================================================================================
async def setup(bot: commands.Bot):
    cog = Drapeaux(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Jeux"
    await bot.add_cog(cog)
