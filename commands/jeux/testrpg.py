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

jdr_json = {
    "intro": "🌌 **RÉVEIL – Un JDR Solo d’introspection et de mystère**\n\n"
             "Le silence t’enveloppe. L’air semble épais, presque irréel. "
             "Quand tes paupières s’ouvrent enfin, la lumière t’agresse, blanche et immobile. "
             "Tu respires lentement. Ce corps… il n’est pas le tien. "
             "Ton esprit flotte, perdu entre le rêve et la réalité.\n\n"
             "À chaque pression sur un bouton, un fragment de ton existence se révélera. "
             "Observe, imagine, ressens. Ce voyage t’appartient, même si tu n’en connais pas encore la fin.",

    "chambre": {
        "1": "Tu te réveilles dans une chambre simple, méticuleusement rangée. "
              "Chaque objet semble figé dans le temps, à sa juste place, comme s’il craignait de troubler le silence. "
              "Cette perfection a quelque chose d’inquiétant.",
        "2": "Une chambre modeste, au désordre tendre, t’entoure. "
              "Les draps froissés, la poussière légère, tout évoque une présence disparue. "
              "Quelqu’un vivait ici… mais plus toi.",
        "3": "Une pièce élégante, baignée d’une lumière douce. "
              "Tu sens un calme étrange, comme si la chambre te regardait en retour.",
        "4": "Le décor déborde de luxe et de chaos : velours, verre brisé, parfums lourds. "
              "C’est un palais qui a connu la folie. Et toi, spectateur de sa fin.",
        "5": "Autour de toi, une chambre d’un autre monde. "
              "Des objets absurdes — horloge inversée, miroir fissuré, tableau sans visage. "
              "Ici, la logique n’a plus sa place.",
        "6": "Tu te relèves dans une pièce à moitié détruite. "
              "Les murs sont dévorés par le temps. Un souffle ancien te frôle, comme un souvenir effacé."
    },

    "corps": {
        "1": "Tu observes tes mains : fines, jeunes, fragiles. "
              "Ton cœur bat trop vite. Ce corps ne t’appartient pas, et pourtant… il respire avec toi.",
        "2": "Un visage inconnu te fixe dans le reflet. Même âge, autre histoire. "
              "Dans ces yeux étrangers, tu crois lire la trace d’une vie oubliée.",
        "3": "Ton corps est plus âgé. Les articulations grincent, la peau raconte. "
              "Chaque cicatrice murmure un secret que tu n’as pas vécu.",
        "4": "Même sexe, mais plus jeune. Ton souffle est léger, ton regard incertain. "
              "Une vulnérabilité nouvelle t’habite.",
        "5": "Même sexe, même âge, mais les traits changés. "
              "C’est toi, et ce n’est pas toi. Une existence parallèle te contemple.",
        "6": "Ton reflet porte des rides que tu ne reconnais pas. "
              "Elles forment des souvenirs sur une peau qui n’a jamais été la tienne."
    },

    "lieu": {
        "1": "Un appartement moderne, lisse, presque clinique. "
              "Chaque objet est à sa place, mais rien ne semble avoir de sens. "
              "L’ordre ici n’est pas humain.",
        "2": "Tu reconnais la chaleur d’une vieille maison. "
              "Le bois craque, les murs respirent encore. "
              "Des souvenirs étrangers glissent entre les ombres.",
        "3": "Une chambre d’hôtel anonyme. "
              "Les rideaux tremblent au vent d’une fenêtre entrouverte. "
              "Tu es ici, mais tant d’autres y ont dormi avant toi.",
        "4": "Tu ouvres les yeux sur la blancheur froide d’un hôpital. "
              "L’odeur d’alcool et de solitude flotte dans l’air. "
              "Tu entends des pas, mais personne n’entre.",
        "5": "Des machines, des tubes, une lumière crue. "
              "Tu es dans un laboratoire. Tu sens que tu n’es pas un patient… mais un sujet.",
        "6": "Autour de toi, des ruines. "
              "Des colonnes brisées, des inscriptions effacées. "
              "Le vent murmure des noms que tu ne comprends pas."
    },

    "objet": {
        "1": "Sur la table, une carte d’identité. "
              "Le nom t’est inconnu, mais la photo… c’est toi. Ou presque.",
        "2": "Un badge d’entreprise pend à une chaise. "
              "Le logo gravé semble t’observer, comme un œil froid et mécanique.",
        "3": "Une photo. Tu souris, entouré d’inconnus. "
              "Mais leurs regards ne sont pas tournés vers toi. Ils fixent quelque chose derrière.",
        "4": "Une lettre, soigneusement pliée. "
              "Ton prénom apparaît sur l’enveloppe, tracé d’une main tremblante. "
              "L’encre a coulé, comme des larmes anciennes.",
        "5": "Un téléphone vibre. Des messages s’enchaînent : ‘Où es-tu ?’, ‘Réponds-moi’. "
              "Les noms te sont étrangers, mais la peur dans les mots est réelle.",
        "6": "Rien. Seulement ton reflet dans un miroir fendu. "
              "Et pour un instant… ton reflet ne bouge pas en même temps que toi."
    },

    "souvenir": {
        "1": "Un éclat d’image traverse ton esprit : un visage riant sous la pluie. "
              "Tu tends la main, mais le souvenir s’efface avant de le toucher.",
        "2": "Une douleur sourde te serre le cœur. "
              "Une perte, une trahison, une chute. Tu n’étais pas prêt à revivre cela.",
        "3": "Tu te vois ailleurs, dans un autre corps, une autre vie. "
              "La mémoire te trahit ou te protège — tu ne sais plus.",
        "4": "Une rue pavée, un phare au loin, une chaleur familière. "
              "Ce lieu t’appelle, même si tu ne l’as jamais vu.",
        "5": "Une sensation étrange t’envahit : comme une magie douce. "
              "Quelque chose — ou quelqu’un — te guide vers la vérité.",
        "6": "Le vide. Pur, infini. Et dans ce néant, ton esprit dérive, libre et perdu à la fois."
    },

    "rencontre": {
        "1": "Trois coups secs à la porte. Ton cœur s’emballe. "
              "Tu n’attendais personne, mais quelqu’un t’attend, lui.",
        "2": "Une voix murmure à l’intérieur de ta tête. "
              "Elle te parle comme à un vieil ami, avec une tendresse inquiétante.",
        "3": "Un craquement soudain. Le sol cède, une ombre surgit. "
              "Le danger a toujours le visage du réveil.",
        "4": "Une main se tend vers toi, invisible mais rassurante. "
              "Peut-être n’es-tu pas seul, finalement.",
        "5": "Une vision éclate dans ton esprit — un symbole, une flamme, un œil qui s’ouvre. "
              "Le sens t’échappe, mais ton cœur comprend.",
        "6": "Rien. Le monde s’efface. "
              "Il ne reste que toi, face à toi-même, dans un silence parfait."
    },

    "choix": {
        "1": "Un obstacle se dresse : une porte verrouillée, une peur ancienne, un doute persistant. "
              "Le passage t’échappe.",
        "2": "Tu avances prudemment. Chaque pas résonne dans un couloir d’incertitude. "
              "Tu sens que quelque chose veille.",
        "3": "Une lueur d’espoir éclaire ta route. "
              "Tu as compris une part du mystère, mais la vérité reste voilée.",
        "4": "Encore un mur. Encore un détour. "
              "Le destin se joue de toi, t’obligeant à chercher plus loin.",
        "5": "Tu suis ton instinct. La peur te guide mieux que la raison.",
        "6": "Un instant suspendu. Tu vois enfin le fil qui relie chaque énigme. "
              "Le sens commence à naître."
    },

    "revelation": {
        "1": "Ce corps… appartenait à quelqu’un que tu as aimé. "
              "Et c’est dans sa peau que tu cherches à comprendre ta propre histoire.",
        "2": "Tout s’éclaire : ce monde n’est qu’un souvenir, une illusion. "
              "Tu n’étais qu’un esprit errant dans la mémoire d’un autre.",
        "3": "Ton esprit est fragmenté. D’autres voix parlent en toi, t’observent, te jugent.",
        "4": "Tu étais le sujet d’une expérience. Une conscience déplacée. "
              "Un esprit transplanté dans un corps volé.",
        "5": "Un nom, un lieu, une voix. Tout se connecte en une mosaïque claire. "
              "Tu commences à comprendre.",
        "6": "La vérité s’impose. Tu sais enfin qui tu es. "
              "Et cette certitude te fait peur."
    },

    "conclusion": {
        "1": "Tu retrouves ton corps d’origine, mais quelque chose est resté derrière toi. "
              "Ton esprit n’est plus le même.",
        "2": "Tu acceptes cette nouvelle existence. "
              "Ce corps devient le tien, cette vie ton destin.",
        "3": "Tu découvres que tu n’as jamais existé. "
              "Tu n’es qu’une copie, un souvenir matérialisé.",
        "4": "Tu comprends enfin : tout cela n’était qu’un rêve. "
              "Mais qui te dit que l’éveil sera différent ?",
        "5": "Ton esprit fusionne avec cette chair étrangère. "
              "Il n’y a plus de ‘toi’ ni ‘d’autre’. Seulement l’unité.",
        "6": "Le récit s’achève ici. La suite dépend de ton imagination. "
              "Après tout, chaque réveil cache une nouvelle naissance."
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
