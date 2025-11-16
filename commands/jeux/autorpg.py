# ────────────────────────────────────────────────────────────────────────────────
# 📌 autorpg.py — Commande /autorpg et !autorpg
# Objectif : JDR solo “Réveil” raconté d'un seul bloc, sans boutons
# Catégorie : Jeux
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands
import random
from utils.discord_utils import safe_send, safe_respond

# ────────────────────────────────────────────────────────────────────────────────
# 🎮 JDR Sets — plusieurs versions d’histoire
# ────────────────────────────────────────────────────────────────────────────────
jdr_sets = {
    # -------------------------------------------------------------------------
    # SET 1 : Ton histoire actuelle (inchangée)
    # -------------------------------------------------------------------------
    "set1": {
        "intro": (
            "Tu te réveilles dans un monde incertain, sans souvenir clair de ton passé. "
            "Ce réveil n’est pas seulement le début d’une aventure, mais celui d’une prise de conscience."
        ),
        "chambre": {
            "1": "Tu ouvres les yeux dans une chambre trop parfaite, comme préparée pour toi.",
            "2": "Tu te trouves dans une pièce abandonnée, témoin d'une présence récente.",
            "3": "Une lumière paisible traverse la chambre, mais elle n’est pas la tienne.",
            "4": "Tu te réveilles dans une chambre luxueuse mais étrangement abîmée.",
            "5": "Devant toi, une chambre aux phénomènes impossibles, défiant la logique.",
            "6": "Tu découvres une pièce en ruine, avalée par le temps et la nature."
        },
        "corps": {
            "1": "Ton propre corps t’échappe : ce n’est pas le tien.",
            "2": "Ton reflet te surprend : familier et étranger à la fois.",
            "3": "Ton corps semble vieux, fatigué, alors que ton esprit reste vif.",
            "4": "Tu sens l’énergie d’un corps jeune… qui n’est pourtant pas le tien.",
            "5": "Ton corps ressemble au tien, mais tout sonne faux.",
            "6": "Tu portes un corps marqué par une vie que tu n’as pas vécue."
        },
        "lieu": {
            "1": "L’appartement où tu te trouves est trop propre pour être naturel.",
            "2": "Tu explores une vieille maison chaleureuse mais hantée par l’absence.",
            "3": "Tu te tiens dans une chambre d’hôtel impersonnelle, un lieu de passage.",
            "4": "Une chambre d’hôpital t’entoure, froide et silencieuse.",
            "5": "Tu es entouré de machines : un laboratoire responsable de ton réveil.",
            "6": "Le monde autour de toi n’est que ruines et vestiges d’une civilisation passée."
        },
        "objet": {
            "1": "Une carte d’identité t’inquiète : ta photo, mais un autre nom.",
            "2": "Un badge d’entreprise évoque une vie que tu as peut-être menée.",
            "3": "Une photo effacée révèle un passé perdu.",
            "4": "Une lettre cachetée t’avertit : ‘Ne te fie à personne’.",
            "5": "Un téléphone clignote : ‘Fuis. On t’a retrouvé.’",
            "6": "Un miroir fissuré déforme un sourire qui n’est pas le tien."
        },
        "souvenir": {
            "1": "Une voix douce te rappelle un bonheur oublié.",
            "2": "Un souvenir d’adieu remonte, flou mais douloureux.",
            "3": "Des fragments de vies multiples semblent se mêler en toi.",
            "4": "Tu revois un phare au loin, symbole d’un retour nécessaire.",
            "5": "Une lumière intérieure tente de t’aider à comprendre.",
            "6": "Rien. Ton passé est un vide insondable."
        },
        "rencontre": {
            "1": "Trois coups frappent une porte invisible.",
            "2": "Une voix intérieure murmure ton vrai nom.",
            "3": "Une silhouette fuit dans l’ombre derrière toi.",
            "4": "Une présence apaisante te frôle avant de disparaître.",
            "5": "Un symbole ardent illumine ton esprit un instant.",
            "6": "Le silence absolu s’impose : tu es seul."
        },
        "choix": {
            "1": "Tu ouvres une porte gravée du mot ‘Souviens-toi’.",
            "2": "Tu avances dans un long couloir résonnant.",
            "3": "Tu suis une lumière vacillante aux intentions incertaines.",
            "4": "Tes décisions semblent modifier la réalité elle-même.",
            "5": "Tu avances les yeux fermés, guidé par ton instinct.",
            "6": "Les fragments du monde s’assemblent lentement autour de toi."
        },
        "revelation": {
            "1": "Ce corps n’est pas le tien, mais ton esprit reste intact.",
            "2": "Tu es le résultat d’une expérience inachevée.",
            "3": "Ton esprit est un puzzle fait de souvenirs empruntés.",
            "4": "Quelqu’un t’a observé, étudié, guidé dans l’ombre.",
            "5": "Tu approches d’une vérité fragile et incomplète.",
            "6": "Tu comprends une partie du mystère… mais pas tout."
        },
        "conclusion": {
            "1": "Tu marches vers un avenir nouveau, riche de choix et de liberté.",
            "2": "Tu choisis de rester pour reconstruire ce lieu étrange.",
            "3": "Tu acceptes ton identité nouvelle, en paix avec ton passé brisé.",
            "4": "Tu avances dans un monde changeant, curieux de ce qu’il deviendra.",
            "5": "Tu continues ton chemin, entre passé et futur, guidé par ta volonté.",
            "6": "Le silence devient ton allié, symbole d’un renouveau calme."
        }
    },

    # -------------------------------------------------------------------------
    # SET 2 : Version sombre / paranoïaque
    # -------------------------------------------------------------------------
    "set2": {
        "intro": "Tu te réveilles avec la sensation d’être observé, même si personne n’est là.",
        "chambre": {
            "1": "La chambre semble surveillée, chaque objet placé comme un piège.",
            "2": "La pièce porte les traces d’une lutte récente.",
            "3": "La lumière clignote comme si quelque chose approchait.",
            "4": "L’endroit est intact, trop intact, comme un décor falsifié.",
            "5": "Un souffle froid traverse la pièce pourtant close.",
            "6": "L’air est lourd, saturé d’une tension invisible."
        },
        "corps": {
            "1": "Ton corps te semble manipulé, retouché.",
            "2": "Des marques étranges parcourent ta peau.",
            "3": "Tes mains tremblent sans que tu le veuilles.",
            "4": "Ton rythme cardiaque n’est pas normal.",
            "5": "Tu portes une fatigue qui ne t’appartient pas.",
            "6": "Chaque mouvement semble appartenir à quelqu’un d’autre."
        },
        "lieu": {
            "1": "L’appartement est rempli de caméras brisées.",
            "2": "La maison semble abandonner un secret qu’elle ne veut pas révéler.",
            "3": "L’hôtel est désert, comme si tout le monde avait fui.",
            "4": "La chambre médicale porte des traces d’expériences répétées.",
            "5": "Le laboratoire est en alerte rouge silencieuse.",
            "6": "Le monde extérieur n’est que ruines et cendres."
        },
        "objet": {
            "1": "Un carnet rempli d’alertes écrites par toi-même.",
            "2": "Une clé magnétique avec ton empreinte… mais pas ta mémoire.",
            "3": "Un enregistrement audio où tu te mets en garde.",
            "4": "Une seringue vide portant ton nom.",
            "5": "Un message : ‘Ils arrivent’.",
            "6": "Un masque identique à ton visage."
        },
        "souvenir": {
            "1": "Tu vois des ombres t’observer derrière une vitre.",
            "2": "Tu te rappelles avoir couru sans savoir pourquoi.",
            "3": "Tu te vois attaché sur une table.",
            "4": "Tu revois une silhouette qui efface ta mémoire.",
            "5": "Un compte à rebours résonne dans ta tête.",
            "6": "Aucun souvenir, seulement une peur primitive."
        },
        "rencontre": {
            "1": "Une ombre se penche derrière toi puis disparaît.",
            "2": "Une voix dit ‘Tu n’aurais pas dû te réveiller’.",
            "3": "Des pas se rapprochent mais personne n’apparaît.",
            "4": "Ton double passe dans l’embrasure d’une porte.",
            "5": "Un cri silencieux traverse ton esprit.",
            "6": "Nul ne vient. Tu es traqué par l’invisible."
        },
        "choix": {
            "1": "Tu forces une porte scellée par l’extérieur.",
            "2": "Tu suis des traces ensanglantées.",
            "3": "Tu désactives un panneau de contrôle inconnu.",
            "4": "Tu caches ton souffle pour éviter d’être repéré.",
            "5": "Tu te faufiles à travers un couloir détruit.",
            "6": "Tu fouilles les vestiges d’un combat."
        },
        "revelation": {
            "1": "Tu n’es pas recherché : tu es l’arme.",
            "2": "Tu n’as pas perdu ta mémoire : on te l’a arrachée.",
            "3": "Tu n’es pas seul, mais ceux qui restent te craignent.",
            "4": "Ton passé a été effacé pour en créer un nouveau.",
            "5": "Tu n’es pas victime : tu es responsable.",
            "6": "Tu comprends trop tard que tu t’es réveillé trop tôt."
        },
        "conclusion": {
            "1": "Tu fuis, poursuivi par ta propre création.",
            "2": "Tu décides d’affronter ceux qui t’ont manipulé.",
            "3": "Tu disparais dans l’ombre pour survivre.",
            "4": "Tu détruis ce qui a fait de toi un monstre.",
            "5": "Tu acceptes de devenir l’inconnu qu’on a voulu créer.",
            "6": "Tu marches dans un monde hanté par tes propres ombres."
        }
    },

    # -------------------------------------------------------------------------
    # SET 3 : Version onirique / surréaliste
    # -------------------------------------------------------------------------
    "set3": {
        "intro": "Tu t’éveilles comme si tu sortais d’un rêve trop réel pour être inventé.",
        "chambre": {
            "1": "La chambre flotte légèrement, comme suspendue dans le vide.",
            "2": "Les murs respirent lentement.",
            "3": "La lumière danse comme une aurore intérieure.",
            "4": "Le sol semble liquide mais te porte.",
            "5": "Les objets changent de place quand tu détournes le regard.",
            "6": "La pièce se réarrange selon tes émotions."
        },
        "corps": {
            "1": "Ton corps semble fait d’échos.",
            "2": "Ta peau scintille comme un rêve qui s’efface.",
            "3": "Ton souffle produit de légères notes musicales.",
            "4": "Ton ombre agit une seconde après toi.",
            "5": "Ton reflet affiche une autre humeur que la tienne.",
            "6": "Tu changes légèrement de forme à chaque pensée."
        },
        "lieu": {
            "1": "L’appartement flotte sur une mer silencieuse.",
            "2": "La maison est un labyrinthe aux couloirs mouvants.",
            "3": "L’hôtel semble construit à partir de souvenirs perdus.",
            "4": "La chambre médicale ressemble à un cocon",
            "5": "Le laboratoire brille d’une lumière intérieure.",
            "6": "Le monde est une fresque vivante, peinte autour de toi."
        },
        "objet": {
            "1": "Une montre qui tourne à l’envers.",
            "2": "Un livre qui écrit ton histoire en temps réel.",
            "3": "Une photo mouvante de toi dans un autre monde.",
            "4": "Une plume qui flotte et te regarde.",
            "5": "Un masque souriant que tu n’as jamais porté.",
            "6": "Un cristal qui pulse comme un cœur."
        },
        "souvenir": {
            "1": "Un rire d’enfant chantonne dans ton esprit.",
            "2": "Tu te souviens d’avoir volé au-dessus d’une mer d’ombres.",
            "3": "Un souvenir de lumière pure t’enveloppe.",
            "4": "Tu revois un arbre géant porteur d’étoiles.",
            "5": "Ton passé se présente comme un rêve récurrent.",
            "6": "Rien… un vide blanc où tout est encore possible."
        },
        "rencontre": {
            "1": "Un être de lumière te frôle doucement.",
            "2": "Ta propre voix t’appelle depuis ailleurs.",
            "3": "Un animal aux yeux humains te regarde.",
            "4": "Une silhouette faite de poussière d’or apparaît.",
            "5": "Un souvenir prend forme devant toi.",
            "6": "Tu restes seul dans un calme irréel."
        },
        "choix": {
            "1": "Tu pousses une porte vers un autre rêve.",
            "2": "Tu suis un chemin de plumes lumineuses.",
            "3": "Tu t’avances vers ta propre ombre qui te guide.",
            "4": "Tu crées un passage par ta seule volonté.",
            "5": "Tu t’élèves légèrement du sol.",
            "6": "Tu laisses le monde s’écrire autour de toi."
        },
        "revelation": {
            "1": "Tu n’es pas prisonnier du rêve : tu en es l’auteur.",
            "2": "Ton corps réel dort ailleurs.",
            "3": "Ton passé n’a jamais été figé.",
            "4": "Une partie de toi t’attend au bout de ce monde.",
            "5": "Tu as façonné ce monde pour guérir.",
            "6": "Tu comprends que tu peux tout remodeler."
        },
        "conclusion": {
            "1": "Tu t’envoles vers un nouvel horizon intérieur.",
            "2": "Tu fusionnes avec ta lumière intérieure.",
            "3": "Tu choisis de rester pour créer davantage.",
            "4": "Tu retournes à ton corps avec une paix nouvelle.",
            "5": "Le rêve t’emporte vers une autre aventure.",
            "6": "Tu marches dans un monde que tu recrées à chaque pas."
        }
    },

    # -------------------------------------------------------------------------
    # SET 4 : Version Sci-Fi froide
    # -------------------------------------------------------------------------
    "set4": {
        "intro": "Système actif : conscience restaurée. Tu te réveilles dans un environnement contrôlé.",
        "chambre": {
            "1": "La chambre est entièrement métallique et stérile.",
            "2": "Les murs affichent des données biométriques te concernant.",
            "3": "Des modules de maintenance s’affairent autour de toi.",
            "4": "Une capsule cryogénique ouverte fume encore.",
            "5": "La pièce est éclairée par des néons pulsants.",
            "6": "Un générateur ronronne au-dessus de ta tête."
        },
        "corps": {
            "1": "Tes articulations semblent mécaniques.",
            "2": "Des implants clignotent sous ta peau.",
            "3": "Une interface s’affiche dans ton champ de vision.",
            "4": "Ton rythme cardiaque est régulé artificiellement.",
            "5": "Ta force excède les limites humaines.",
            "6": "Ton corps semble en partie synthétique."
        },
        "lieu": {
            "1": "Tu es dans une station orbitale en dérive.",
            "2": "Tu te trouves dans un bunker de quarantaine.",
            "3": "Un complexe scientifique s’étend autour de toi.",
            "4": "Un centre médical automatisé t’analyse.",
            "5": "Un laboratoire de clonage t’entoure.",
            "6": "L’extérieur révèle une planète morte."
        },
        "objet": {
            "1": "Une carte d’accès à ton propre dossier.",
            "2": "Un drone inactif portant ton numéro de série.",
            "3": "Un module de mémoire fragmenté.",
            "4": "Une puce d’identification défectueuse.",
            "5": "Un écran affiche ‘REBOOT NÉCESSAIRE’.",
            "6": "Un dispositif pouvant altérer ta trajectoire génétique."
        },
        "souvenir": {
            "1": "Tu te rappelles un protocole d’évacuation.",
            "2": "Des voix de chercheurs te donnent des ordres.",
            "3": "Une mission avortée revient en flash.",
            "4": "Tu te vois initialisé dans un tube de stase.",
            "5": "Un code d’accès te revient soudain.",
            "6": "Aucun souvenir, seulement un numéro : le tien."
        },
        "rencontre": {
            "1": "Un drone sentinelle t’analyse.",
            "2": "Une voix synthétique dit ‘Bienvenue, unité retrouvée’.",
            "3": "Un hologramme d’un scientifique apparaît.",
            "4": "Un robot médical te diagnostique.",
            "5": "Un système d’alarme active une surveillance.",
            "6": "Aucun contact : le système te laisse libre."
        },
        "choix": {
            "1": "Tu accèdes au terminal central.",
            "2": "Tu explores un module interdit.",
            "3": "Tu répares ton implant principal.",
            "4": "Tu désactives les protocoles de sécurité.",
            "5": "Tu utilises une carte d’accès détériorée.",
            "6": "Tu suis le guide holographique."
        },
        "revelation": {
            "1": "Tu es un prototype abandonné.",
            "2": "Tu as été créé pour remplacer quelqu’un.",
            "3": "Tu es la dernière unité fonctionnelle.",
            "4": "Ton identité a été écrasée par une nouvelle.",
            "5": "Tu n’es pas en panne : tu es libre.",
            "6": "Tu deviens plus qu’un programme."
        },
        "conclusion": {
            "1": "Tu quittes la station vers un monde inconnu.",
            "2": "Tu prends le contrôle du système central.",
            "3": "Tu effaces ton ancien code et repars à zéro.",
            "4": "Tu répares le complexe et deviens son gardien.",
            "5": "Tu pars explorer les ruines de l’humanité.",
            "6": "Tu te libères de toute programmation."
        }
    },

    # -------------------------------------------------------------------------
    # SET 5 : Version mystique / introspective
    # -------------------------------------------------------------------------
    "set5": {
        "intro": "Tu t’éveilles comme si l’univers lui-même t’avait ramené à la surface.",
        "chambre": {
            "1": "La chambre est emplie d’un silence sacré.",
            "2": "Une odeur d’encens flotte doucement.",
            "3": "Des symboles anciens sont gravés dans les murs.",
            "4": "Une lumière chaude émane d’un point invisible.",
            "5": "Le sol semble te reconnaître.",
            "6": "Un murmure ancien traverse la pièce."
        },
        "corps": {
            "1": "Ton corps semble habité par une puissance oubliée.",
            "2": "Tes veines brillent de l’intérieur.",
            "3": "Ton cœur résonne comme un tambour sacré.",
            "4": "Tu sens une présence à l’intérieur de toi.",
            "5": "Tu portes la marque d’un ancien rituel.",
            "6": "Tu sens que ton corps n’est pas seul."
        },
        "lieu": {
            "1": "Un sanctuaire ancien t’entoure.",
            "2": "Une maison ancestrale veille sur toi.",
            "3": "Tu te tiens dans un lieu de pèlerinage oublié.",
            "4": "Une chambre de temple t’accueille.",
            "5": "Une salle d’initiation te met à l’épreuve.",
            "6": "Tu es au cœur d’un monde régi par les esprits."
        },
        "objet": {
            "1": "Un talisman vibrant de puissance.",
            "2": "Un parchemin écrit dans une langue perdue.",
            "3": "Une amulette qui pulse à ton rythme.",
            "4": "Un bâton rituel marqué par le temps.",
            "5": "Une pierre runique qui s’illumine à ton contact.",
            "6": "Une flamme enfermée dans un verre sacré."
        },
        "souvenir": {
            "1": "Tu revois un maître spirituel te sourire.",
            "2": "Tu te rappelles une épreuve initiatique.",
            "3": "Un chant ancien résonne dans ton cœur.",
            "4": "Un souvenir d’un autre monde t’effleure.",
            "5": "Une voix intérieure t’appelle ‘Élu’.",
            "6": "Ton passé se dissout dans une paix profonde."
        },
        "rencontre": {
            "1": "Un guide spirituel se manifeste un instant.",
            "2": "Une silhouette lumineuse t’observe.",
            "3": "Un esprit ancien t’offre un conseil silencieux.",
            "4": "Un animal totémique se manifeste.",
            "5": "Une présence invisible t’accompagne.",
            "6": "Aucune présence : l’épreuve est intérieure."
        },
        "choix": {
            "1": "Tu acceptes ton rite de passage.",
            "2": "Tu franchis un seuil marqué de runes.",
            "3": "Tu médites pour trouver ta voie.",
            "4": "Tu tends la main vers une lumière sacrée.",
            "5": "Tu prononces un ancien serment.",
            "6": "Tu laisses ton intuition guider tes pas."
        },
        "revelation": {
            "1": "Tu es l’héritier d’une force oubliée.",
            "2": "Ton âme a déjà parcouru ces lieux.",
            "3": "Tu es le dernier à pouvoir restaurer l’équilibre.",
            "4": "Le monde t’a appelé pour une raison précise.",
            "5": "Ton existence est liée au sacré.",
            "6": "Tu comprends enfin l’harmonie en toi."
        },
        "conclusion": {
            "1": "Tu marches sur un chemin de sagesse.",
            "2": "Tu deviens gardien de l’ancien savoir.",
            "3": "Tu retrouves ta place parmi les esprits.",
            "4": "Tu t’en vas répandre la paix.",
            "5": "Tu commences une nouvelle ascension spirituelle.",
            "6": "Tu trouves la paix absolue."
        }
    },
}

# ────────────────────────────────────────────────────────────────────────────────
# 💬 Morales aléatoires
# ────────────────────────────────────────────────────────────────────────────────
morales = [
    "Même lorsque tout semble flou et incertain, chaque pas construit celui que tu deviens.",
    "La vérité n’est jamais unique : elle dépend du chemin que tu empruntes.",
    "Ce n’est pas le passé qui te définit, mais ce que tu décides d’en faire.",
    "Chaque réveil est une seconde chance de devenir toi-même.",
    "Même dans le doute, tu n’as jamais cessé d’avancer.",
]

# ────────────────────────────────────────────────────────────────────────────────
# 📝 Fonction : génère une histoire complète depuis un set aléatoire
# ────────────────────────────────────────────────────────────────────────────────
def generate_full_story():
    set_choice = random.choice(list(jdr_sets.values()))
    story = []
    story.append(set_choice["intro"])
    order = ["chambre", "corps", "lieu", "objet", "souvenir", "rencontre", "choix", "revelation", "conclusion"]
    for key in order:
        result = str(random.randint(1, 6))
        story.append(set_choice[key][result])
    story.append("\n**Morale :** " + random.choice(morales))
    return "\n\n".join(story)

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class AutoRPG(commands.Cog):
    """Commande /autorpg et !autorpg — Histoire complète en un seul message"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="autorpg")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_autorpg(self, ctx):
        story = generate_full_story()
        await safe_send(ctx.channel, content=story)

    @discord.app_commands.command(
        name="autorpg",
        description="Génère une histoire complète de JDR solo en un seul bloc."
    )
    @discord.app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_autorpg(self, interaction: discord.Interaction):
        story = generate_full_story()
        await safe_respond(interaction, content=story)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = AutoRPG(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Jeux"
    await bot.add_cog(cog)
