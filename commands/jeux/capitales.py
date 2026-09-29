# ================================================================================
# 📌 capitales.py — Commande interactive /capitales et !capitales
# Objectif : Deviner la capitale d'un pays
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

from utils.discord_utils import safe_send, safe_edit
from utils.jeux_utils import normalize_text, parse_mode, ReplyView, BuzzerView

log = logging.getLogger(__name__)

# ================================================================================
# 📂 Liste des pays et leurs capitales
# ================================================================================
CAPITALS = {
    "Afghanistan": "Kaboul",
    "Afrique du Sud": "Pretoria",
    "Albanie": "Tirana",
    "Algérie": "Alger",
    "Allemagne": "Berlin",
    "Andorre": "Andorre-la-Vieille",
    "Angola": "Luanda",
    "Antigua-et-Barbuda": "Saint-Jean",
    "Arabie saoudite": "Riyad",
    "Argentine": "Buenos Aires",
    "Arménie": "Erevan",
    "Australie": "Canberra",
    "Autriche": "Vienne",
    "Azerbaïdjan": "Bakou",
    "Bahamas": "Nassau",
    "Bahreïn": "Manama",
    "Bangladesh": "Dacca",
    "Barbade": "Bridgetown",
    "Belgique": "Bruxelles",
    "Belize": "Belmopan",
    "Bénin": "Porto-Novo",
    "Bhoutan": "Thimphou",
    "Biélorussie": "Minsk",
    "Birmanie": "Naypyidaw",
    "Bolivie": "Sucre",
    "Bosnie-Herzégovine": "Sarajevo",
    "Botswana": "Gaborone",
    "Brésil": "Brasília",
    "Brunei": "Bandar Seri Begawan",
    "Bulgarie": "Sofia",
    "Burkina Faso": "Ouagadougou",
    "Burundi": "Gitega",
    "Cambodge": "Phnom Penh",
    "Cameroun": "Yaoundé",
    "Canada": "Ottawa",
    "Cap-Vert": "Praia",
    "Chili": "Santiago",
    "Chine": "Pékin",
    "Chypre": "Nicosie",
    "Colombie": "Bogotá",
    "Comores": "Moroni",
    "Congo": "Brazzaville",
    "Corée du Nord": "Pyongyang",
    "Corée du Sud": "Séoul",
    "Costa Rica": "San José",
    "Croatie": "Zagreb",
    "Cuba": "La Havane",
    "Danemark": "Copenhague",
    "Djibouti": "Djibouti",
    "Dominique": "Roseau",
    "Égypte": "Le Caire",
    "Émirats arabes unis": "Abou Dabi",
    "Équateur": "Quito",
    "Érythrée": "Asmara",
    "Espagne": "Madrid",
    "Estonie": "Tallinn",
    "Eswatini": "Mbabane",
    "États-Unis": "Washington, D.C.",
    "Éthiopie": "Addis-Abeba",
    "Fidji": "Suva",
    "Finlande": "Helsinki",
    "France": "Paris",
    "Gabon": "Libreville",
    "Gambie": "Banjul",
    "Géorgie": "Tbilissi",
    "Ghana": "Accra",
    "Grèce": "Athènes",
    "Grenade": "Saint-Georges",
    "Guatemala": "Guatemala",
    "Guinée": "Conakry",
    "Guinée-Bissau": "Bissau",
    "Guinée équatoriale": "Malabo",
    "Guyana": "Georgetown",
    "Haïti": "Port-au-Prince",
    "Honduras": "Tegucigalpa",
    "Hongrie": "Budapest",
    "Îles Marshall": "Majuro",
    "Îles Salomon": "Honiara",
    "Inde": "New Delhi",
    "Indonésie": "Jakarta",
    "Iran": "Téhéran",
    "Irak": "Bagdad",
    "Irlande": "Dublin",
    "Islande": "Reykjavik",
    "Israël": "Jérusalem",
    "Italie": "Rome",
    "Jamaïque": "Kingston",
    "Japon": "Tokyo",
    "Jordanie": "Amman",
    "Kazakhstan": "Noursoultan",
    "Kenya": "Nairobi",
    "Kirghizistan": "Bichkek",
    "Kiribati": "Tarawa",
    "Koweït": "Koweït",
    "Laos": "Vientiane",
    "Lesotho": "Maseru",
    "Lettonie": "Riga",
    "Liban": "Beyrouth",
    "Liberia": "Monrovia",
    "Libye": "Tripoli",
    "Liechtenstein": "Vaduz",
    "Lituanie": "Vilnius",
    "Luxembourg": "Luxembourg",
    "Madagascar": "Antananarivo",
    "Malaisie": "Kuala Lumpur",
    "Malawi": "Lilongwe",
    "Maldives": "Malé",
    "Mali": "Bamako",
    "Malte": "La Valette",
    "Maroc": "Rabat",
    "Maurice": "Port-Louis",
    "Mauritanie": "Nouakchott",
    "Mexique": "Mexico",
    "Micronésie": "Palikir",
    "Moldavie": "Chișinău",
    "Monaco": "Monaco",
    "Mongolie": "Oulan-Bator",
    "Monténégro": "Podgorica",
    "Mozambique": "Maputo",
    "Namibie": "Windhoek",
    "Nauru": "Yaren",
    "Népal": "Katmandou",
    "Nicaragua": "Managua",
    "Niger": "Niamey",
    "Nigéria": "Abuja",
    "Norvège": "Oslo",
    "Nouvelle-Zélande": "Wellington",
    "Oman": "Mascate",
    "Ouganda": "Kampala",
    "Ouzbékistan": "Tachkent",
    "Pakistan": "Islamabad",
    "Palaos": "Ngerulmud",
    "Panama": "Panama",
    "Papouasie-Nouvelle-Guinée": "Port-Moresby",
    "Paraguay": "Asuncion",
    "Pays-Bas": "Amsterdam",
    "Pérou": "Lima",
    "Philippines": "Manille",
    "Pologne": "Varsovie",
    "Portugal": "Lisbonne",
    "Qatar": "Doha",
    "République centrafricaine": "Bangui",
    "République dominicaine": "Saint-Domingue",
    "République tchèque": "Prague",
    "Roumanie": "Bucarest",
    "Royaume-Uni": "Londres",
    "Russie": "Moscou",
    "Rwanda": "Kigali",
    "Saint-Christophe-et-Niévès": "Basseterre",
    "Saint-Marin": "Saint-Marin",
    "Saint-Vincent-et-les-Grenadines": "Kingstown",
    "Salvador": "San Salvador",
    "Samoa": "Apia",
    "Sao Tomé-et-Principe": "São Tomé",
    "Sénégal": "Dakar",
    "Serbie": "Belgrade",
    "Seychelles": "Victoria",
    "Sierra Leone": "Freetown",
    "Singapour": "Singapour",
    "Slovaquie": "Bratislava",
    "Slovénie": "Ljubljana",
    "Somalie": "Mogadiscio",
    "Soudan": "Khartoum",
    "Soudan du Sud": "Djouba",
    "Sri Lanka": "Sri Jayawardenepura Kotte",
    "Suède": "Stockholm",
    "Suisse": "Berne",
    "Syrie": "Damas",
    "Tadjikistan": "Douchanbé",
    "Tanzanie": "Dodoma",
    "Thaïlande": "Bangkok",
    "Timor oriental": "Dili",
    "Togo": "Lomé",
    "Tonga": "Nukuʻalofa",
    "Trinité-et-Tobago": "Port-d'Espagne",
    "Tunisie": "Tunis",
    "Turkménistan": "Achgabat",
    "Turquie": "Ankara",
    "Tuvalu": "Funafuti",
    "Ukraine": "Kiev",
    "Uruguay": "Montevideo",
    "Vanuatu": "Port-Vila",
    "Vatican": "Cité du Vatican",
    "Venezuela": "Caracas",
    "Viêt Nam": "Hanoï",
    "Yémen": "Sanaa",
    "Zambie": "Lusaka",
    "Zimbabwe": "Harare"
}

# ================================================================================
# 🎮 Classe de gestion de l'affichage
# ================================================================================
class CapitalesGame:
    def __init__(self, country: str, capital: str, author_id: int, multi: bool = False, duration: int = 120):
        self.country = country
        self.capital = capital
        self.author_id = author_id
        self.multi = multi
        self.duration = duration
        self.finished = False
        self.winner: str | None = None
        self.attempts: list[dict] = []
        self.message = None
        self.start_time = asyncio.get_event_loop().time()

    def build_embed(self) -> discord.Embed:
        mode_text = "Multi 🌍" if self.multi else "Solo 🧍‍♂️"
        title = f"🌍 Devine la Capitale - Mode {mode_text}"

        action_text = "Clique sur **🔔 Buzzer** pour prendre la main." if self.multi else "Clique sur **✍️ Répondre** pour proposer ta réponse."
        description = f"Quelle est la capitale de **{self.country}** ?\n{action_text}"

        embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Color.blurple()
        )

        if self.attempts:
            lines = []
            for entry in self.attempts:
                status = "✅" if entry.get('correct') else "❌"
                lines.append(f"{entry['author']}: **{entry['word']}** {status}")
            tries_text = "\n".join(lines)
            embed.add_field(name=f"Essais ({len(self.attempts)})", value=tries_text, inline=False)

        if self.finished:
            if self.winner:
                embed.title = f"{title} — Gagné !"
                embed.color = discord.Color.green()
                embed.description = f"Quelle est la capitale de **{self.country}** ?\n\n🏆 **{self.winner}** a trouvé !\n✅ Réponse : **{self.capital}**"
            else:
                embed.title = "⏰ Temps écoulé !"
                embed.color = discord.Color.red()
                embed.description = f"Quelle est la capitale de **{self.country}** ?\n\n❌ Personne n'a trouvé. C'était **{self.capital}**."
            embed.set_footer(text="Partie terminée")
        else:
            elapsed = int(asyncio.get_event_loop().time() - self.start_time)
            remaining = max(0, self.duration - elapsed)
            embed.set_footer(text=f"⏱️ Temps restant : {remaining} secondes")

        return embed

# ================================================================================
# 🧠 Cog principal
# ================================================================================
class Capitales(commands.Cog):
    """Commande /capitales et !capitales — Deviner la capitale d'un pays"""
    SOLO_TIME  = 120
    MULTI_TIME = 120

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ============================================================================
    # 🔹 Fonction interne commune
    # ============================================================================
    async def _send_quiz(self, channel, author_id: int, multi: bool = False):
        country = random.choice(list(CAPITALS.keys()))
        capital = CAPITALS[country]
        duration = self.MULTI_TIME if multi else self.SOLO_TIME
        game = CapitalesGame(country, capital, author_id, multi, duration)

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
            is_correct = (normalize_text(user_answer) == normalize_text(capital))

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
                modal_title="🖊️ Devine la capitale",
                modal_label="Entre la capitale",
                modal_placeholder="Exemple : Paris",
                modal_max_length=50,
                on_submit=on_submit,
                on_buzz=on_buzz,
                buzz_timeout=30,
                view_timeout=300,
            )
        else:
            view = ReplyView(
                user_id=author_id,
                modal_title="🖊️ Devine la capitale",
                modal_label="Entre la capitale",
                modal_placeholder="Exemple : Paris",
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
    @app_commands.command(name="capitales", description="Devine la capitale d'un pays")
    @app_commands.describe(mode="Tapez 'm' ou 'multi' pour le mode multijoueur")
    @app_commands.checks.cooldown(1, 10.0, key=lambda i: i.user.id)
    async def slash_capitales(self, interaction: discord.Interaction, mode: str = None):
        await interaction.response.defer()
        multi = parse_mode(mode)
        await self._send_quiz(interaction.channel, author_id=interaction.user.id, multi=multi)
        await interaction.delete_original_response()

    # ============================================================================
    # 🔹 Commande PREFIX
    # ============================================================================
    @commands.command(name="capitales", help="Devine la capitale d'un pays")
    @commands.cooldown(1, 10.0, commands.BucketType.user)
    async def prefix_capitales(self, ctx: commands.Context, *, arg: str = None):
        multi = parse_mode(arg)
        await self._send_quiz(ctx.channel, author_id=ctx.author.id, multi=multi)


# ================================================================================
# 🔌 Setup du Cog
# ================================================================================
async def setup(bot: commands.Bot):
    cog = Capitales(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Jeux"
    await bot.add_cog(cog)
