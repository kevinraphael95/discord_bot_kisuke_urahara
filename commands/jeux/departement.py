# ================================================================================
# 📌 departements.py — Commande interactive /departements et !departements
# Objectif : Deviner la préfecture d'un département français
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
# 📂 Liste des départements français et leurs préfectures
# ================================================================================
DEPARTEMENTS = {
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

# ================================================================================
# 🎮 Classe de gestion de l'affichage
# ================================================================================
class DepartementsGame:
    def __init__(self, departement: str, prefecture: str, author_id: int, multi: bool = False, duration: int = 120):
        self.departement = departement
        self.prefecture = prefecture
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
        mode_text = "Multi 🌍" if self.multi else "Solo 🧍‍♂️"
        title = f"🇫🇷 Devine la Préfecture - Mode {mode_text}"

        action_text = "Clique sur **🔔 Buzzer** pour prendre la main." if self.multi else "Clique sur **✍️ Répondre** pour proposer ta réponse."
        description = f"# ➡️ `{self.departement}`\n{action_text}"

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

        if self.last_error and not self.finished:
            embed.add_field(name="⚠️ Remarque", value=self.last_error, inline=False)

        if self.finished:
            if self.winner:
                embed.title = f"{title} — Gagné !"
                embed.color = discord.Color.green()
                embed.description = f"# ➡️ `{self.departement}`\n\n🏆 **{self.winner}** a trouvé !\n✅ Réponse : **{self.prefecture}**"
            else:
                embed.title = "⏰ Temps écoulé !"
                embed.color = discord.Color.red()
                embed.description = f"# ➡️ `{self.departement}`\n\n❌ Personne n'a trouvé. C'était **{self.prefecture}**."
            embed.set_footer(text="Partie terminée")
        else:
            elapsed = int(asyncio.get_event_loop().time() - self.start_time)
            remaining = max(0, self.duration - elapsed)
            embed.set_footer(text=f"⏱️ Temps restant : {remaining} secondes")

        return embed

# ================================================================================
# 🧠 Cog principal
# ================================================================================
class Departements(commands.Cog):
    """Commande /departements et !departements — Deviner la préfecture d'un département français"""
    SOLO_TIME  = 120
    MULTI_TIME = 120

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ============================================================================
    # 🔹 Fonction interne commune
    # ============================================================================
    async def _send_quiz(self, channel, author_id: int, multi: bool = False):
        departement = random.choice(list(DEPARTEMENTS.keys()))
        prefecture = DEPARTEMENTS[departement]
        duration = self.MULTI_TIME if multi else self.SOLO_TIME
        game = DepartementsGame(departement, prefecture, author_id, multi, duration)

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

            # Vérification anti-doublon (avec normalisation)
            if any(normalize_text(entry['word']) == normalize_text(user_answer) for entry in game.attempts):
                game.last_error = f"La réponse `{user_answer}` a déjà été proposée !"
                if game.message:
                    await safe_edit(game.message, embed=game.build_embed())
                return

            is_correct = (normalize_text(user_answer) == normalize_text(prefecture))

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
                modal_title="🖊️ Devine la préfecture",
                modal_label="Entre la préfecture",
                modal_placeholder="Exemple : Lyon",
                modal_max_length=50,
                on_submit=on_submit,
                on_buzz=on_buzz,
                buzz_timeout=30,
                view_timeout=300,
            )
        else:
            view = ReplyView(
                user_id=author_id,
                modal_title="🖊️ Devine la préfecture",
                modal_label="Entre la préfecture",
                modal_placeholder="Exemple : Lyon",
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
    @app_commands.command(name="departement", description="Devine la préfecture d'un département français")
    @app_commands.describe(mode="Tapez 'm' ou 'multi' pour le mode multijoueur")
    @app_commands.checks.cooldown(1, 10.0, key=lambda i: i.user.id)
    async def slash_departements(self, interaction: discord.Interaction, mode: str = None):
        await interaction.response.defer()
        multi = parse_mode(mode)
        await self._send_quiz(interaction.channel, author_id=interaction.user.id, multi=multi)
        await interaction.delete_original_response()

    # ============================================================================
    # 🔹 Commande PREFIX
    # ============================================================================
    @commands.command(name="departement", help="Devine la préfecture d'un département français")
    @commands.cooldown(1, 10.0, commands.BucketType.user)
    async def prefix_departements(self, ctx: commands.Context, *, arg: str = None):
        multi = parse_mode(arg)
        await self._send_quiz(ctx.channel, author_id=ctx.author.id, multi=multi)


# ================================================================================
# 🔌 Setup du Cog
# ================================================================================
async def setup(bot: commands.Bot):
    cog = Departements(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Jeux"
    await bot.add_cog(cog)
