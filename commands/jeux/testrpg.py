# ────────────────────────────────────────────────────────────────────────────────
# 📌 testrpg.py — Commande simple /testrpg et !testrpg
# Objectif : JDR solo “Réveil” avec boutons pour découvrir l’histoire chapitre par chapitre
# Catégorie : Autre
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands
import random
from utils.discord_utils import safe_send, safe_respond  # Utilitaires sécurisés

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 JSON intégré avec texte narratif
# ────────────────────────────────────────────────────────────────────────────────
jdr_json = {
    "intro": "🌌 **RÉVEIL – Un JDR Solo d’introspection et de mystère**\n\n"
             "Tu t’éveilles dans un corps qui n’est pas le tien, dans un lieu inconnu. "
             "Chaque clic sur un bouton révélera un fragment de ton aventure. "
             "Imagine et décris mentalement tes émotions et observations.\n",
    "chambre": {
        "1": "Chambre simple et soigneusement rangée, presque trop parfaite.",
        "2": "Chambre modeste, en léger désordre, comme oubliée.",
        "3": "Chambre élégante, d’une beauté tranquille qui semble te regarder.",
        "4": "Chambre luxueuse mais chaotique, où le luxe et le désordre se mêlent.",
        "5": "Chambre étrange, parsemée d’objets insolites, défiant la logique.",
        "6": "Pièce à moitié détruite ou abandonnée, témoin d’un passé oublié."
    },
    "corps": {
        "1": "Sexe différent, plus jeune, fragile et curieux.",
        "2": "Sexe différent, même âge, avec une histoire invisible dans les yeux.",
        "3": "Sexe différent, plus âgé, empreint de secrets.",
        "4": "Même sexe, plus jeune, avec une vulnérabilité étrange.",
        "5": "Même sexe, même âge mais traits différents, écho d’une autre vie.",
        "6": "Même sexe, plus âgé, chaque ride raconte une histoire."
    },
    "lieu": {
        "1": "Appartement moderne, sobre, où chaque objet semble posé avec soin.",
        "2": "Vieille maison familiale, imprégnée de souvenirs et de fantômes du passé.",
        "3": "Chambre d’hôtel anonyme, murs racontant mille vies.",
        "4": "Hôpital silencieux, aux couloirs vides et odeurs antiseptiques.",
        "5": "Laboratoire étrange, rempli d’instruments inconnus et lumière froide.",
        "6": "Ruines désertées, où le vent murmure des histoires oubliées."
    },
    "objet": {
        "1": "Carte d’identité ou passeport, certitude d’une vie étrangère.",
        "2": "Badge d’entreprise, clé d’un monde inconnu.",
        "3": "Photo d’un groupe, avec ton visage mais des regards inconnus.",
        "4": "Lettre adressée à toi, avec des mots mystérieux.",
        "5": "Téléphone chargé de messages récents.",
        "6": "Rien – seul ton reflet répète l’énigme de ton existence."
    },
    "souvenir": {
        "1": "Fragment d’une vie passée, photo floue dans un rêve.",
        "2": "Événement dramatique, perte ou trahison, résonnant encore.",
        "3": "Vision d’un autre corps ou d’une autre vie que tu as pu connaître.",
        "4": "Lieu inconnu mais chargé de sens, phare dans le brouillard.",
        "5": "Sensation étrange, presque magique, qui semble te guider.",
        "6": "Rien de précis, juste un vide qui appelle à l’introspection."
    },
    "rencontre": {
        "1": "Une personne inconnue frappe à la porte, curieuse ou hostile.",
        "2": "Une voix résonne dans ta tête, douce ou menaçante.",
        "3": "Un danger surgit : chute, accident ou prédateur.",
        "4": "Une aide inattendue se manifeste, guide ou allié.",
        "5": "Une vision, un symbole ou hallucination t’invite à comprendre.",
        "6": "Silence complet, solitude totale, introspection profonde."
    },
    "choix": {
        "1": "Complication : obstacle ou énigme bloque ton chemin.",
        "2": "Avancée prudente : indice découvert mais mystère demeure.",
        "3": "Réussite : révélation partielle ou rencontre cruciale.",
        "4": "Complication : obstacle ou énigme bloque ton chemin.",
        "5": "Avancée prudente : indice découvert mais mystère demeure.",
        "6": "Réussite : révélation partielle ou rencontre cruciale."
    },
    "revelation": {
        "1": "Le corps appartient à quelqu’un que tu connais.",
        "2": "Tu es dans un souvenir ou une simulation.",
        "3": "Ton esprit est fragmenté entre plusieurs identités.",
        "4": "Tu es au centre d’une expérience mystérieuse.",
        "5": "Tu découvres un indice majeur sur ton passé ou ce lieu.",
        "6": "Révélation complète : identité et contexte éclairés."
    },
    "conclusion": {
        "1": "Tu retrouves ton corps originel, mais ton esprit est changé.",
        "2": "Tu acceptes ce corps et cette vie, un nouveau départ.",
        "3": "Tu découvres que tu n’étais jamais toi : fragment ou clone.",
        "4": "Prisonnier d’un rêve ou d’une simulation, sans corps propre.",
        "5": "Fusion complète avec ce corps et cette existence.",
        "6": "Ouvert : invente la fin selon ton imagination."
    }
}

# ────────────────────────────────────────────────────────────────────────────────
# 🧩 View pour boutons et progression chapitre par chapitre
# ────────────────────────────────────────────────────────────────────────────────
class RPGView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.current_chapter = 0
        self.results = {k: random.randint(1,6) for k in jdr_json.keys() if k != "intro"}

    @discord.ui.button(label="Suivant", style=discord.ButtonStyle.green)
    async def next_chapter(self, interaction: discord.Interaction, button: discord.ui.Button):
        chapters = ["chambre","corps","lieu","objet","souvenir","rencontre","choix","revelation","conclusion"]
        if self.current_chapter < len(chapters):
            chap = chapters[self.current_chapter]
            result = self.results[chap]
            embed = interaction.message.embeds[0]
            embed.add_field(name=f"📖 Chapitre {self.current_chapter+1} – {chap.capitalize()}",
                            value=jdr_json[chap][str(result)],
                            inline=False)
            self.current_chapter += 1
            # Si fin de l’histoire, retirer le bouton
            if self.current_chapter >= len(chapters):
                self.stop()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.send_message("✅ Histoire terminée.", ephemeral=True)

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class TestRPG(commands.Cog):
    """Commande /testrpg et !testrpg — JDR solo 'Réveil' avec progression par boutons"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="testrpg")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_testrpg(self, ctx):
        embed = discord.Embed(
            title="🌌 Réveil – JDR Solo",
            description=jdr_json["intro"],
            color=discord.Color.teal()
        )
        view = RPGView()
        await safe_send(ctx.channel, embed=embed, view=view)

    @discord.app_commands.command(
        name="testrpg",
        description="Commence le JDR solo 'Réveil' avec progression par boutons"
    )
    @discord.app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_testrpg(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🌌 Réveil – JDR Solo",
            description=jdr_json["intro"],
            color=discord.Color.teal()
        )
        view = RPGView()
        await safe_respond(interaction, embed=embed, view=view)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = TestRPG(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Autre"
    await bot.add_cog(cog)
