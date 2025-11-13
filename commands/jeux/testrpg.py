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
# 🧠 JSON narratif complet – version immersive et littéraire
# ────────────────────────────────────────────────────────────────────────────────
jdr_json = {
    "intro": "🌌 **JDR Solo Test**\n\n"
             "Le silence t’entourre, lorsque tes yeux s’ouvrent, tu te réveille dans une pièce que tu ne reconnais pas. "
             "Quelque chose ne vas pas avec ton corps, tu es encore endormi mais tu ne te sens pas comme d'habitude. ",

    "chambre": {
        "1": "La pièce où tu te trouves est d’une propreté irréelle. "
              "Chaque livre est aligné, chaque cadre parfaitement droit. "
              "L’air y est froid, comme si personne n’y avait respiré depuis des années. "
              "Une lampe solitaire éclaire une chaise vide, témoin d’une attente interminable. "
              "Tu as la sensation d’être observé… non par un être, mais par la perfection elle-même.",
        "2": "Autour de toi, une chambre simple, habitée par la poussière. "
              "Le lit est défait, les rideaux entrouverts laissent filtrer un souffle d’air fatigué. "
              "Sur la table, une tasse renversée a séché depuis longtemps. "
              "Tu ne reconnais rien, mais ton cœur bat plus vite, comme s’il se souvenait à ta place.",
        "3": "Une chambre baignée d’une lumière dorée, presque apaisante. "
              "Les murs racontent une histoire silencieuse : celle d’un lieu aimé puis oublié. "
              "Le temps y circule autrement, ralenti, doux et mélancolique. "
              "Tu pourrais t’y endormir à nouveau, si la peur ne te retenait pas.",
        "4": "L’opulence t’écrase. Draps de soie, miroirs dorés, parfum sucré de roses fanées. "
              "Mais sous cette beauté se cache une tension : des griffures sur la porte, "
              "un verre brisé dans le coin, un manteau jeté à la hâte. "
              "Quelqu’un vivait ici… et il est parti trop vite.",
        "5": "Des objets absurdes s’entassent autour de toi : une horloge qui tourne à l’envers, "
              "un tableau sans visage, un livre sans mots. "
              "La pièce respire une logique étrangère, comme un rêve lucide. "
              "Tu te demandes si tu t’es éveillé… ou endormi plus profondément.",
        "6": "La chambre est en ruine. Les murs sont couverts de lierre, le plafond s’effrite. "
              "Sous tes doigts, la poussière cache d’anciennes gravures — des noms effacés. "
              "Le vent s’engouffre, portant des murmures indistincts. "
              "Tu comprends que ce lieu n’appartient plus à personne depuis longtemps."
    },

    "corps": {
        "1": "Tu lèves une main tremblante, et ton cœur s’arrête. "
              "Cette peau n’est pas la tienne. Plus jeune, plus frêle, presque translucide. "
              "Chaque geste semble emprunté, comme si tu volais la vie d’un autre.",
        "2": "Ton reflet te fixe dans une vitre fêlée. "
              "Ce visage a ton âge, mais ses traits racontent une autre histoire. "
              "Des cicatrices invisibles se lisent dans son regard, un fardeau dont tu ignores tout.",
        "3": "Tes articulations craquent. Ce corps est vieux, usé par le temps. "
              "Tu portes maintenant le poids d’années que tu n’as pas vécues.",
        "4": "Tu te découvres plus jeune. Ton souffle est vif, ton sang pulse fort. "
              "Tu n’as pas grandi ici, dans cette chair neuve.",
        "5": "Même sexe, même âge, mais tout est différent : le nez, la voix, le regard. "
              "Est-ce toi? Une autre version de toi-même? ",
        "6": "Tu habites un corps vieilli, mais digne. "
              "Chaque ride semble te parler, chaque souffle porte une mémoire. "
              "Tu ressens à la fois la fatigue et la paix d’une existence accomplie."
    },

    "lieu": {
        "1": "L’appartement est immaculé, presque clinique. "
              "Aucun bruit, aucune trace de vie. Les murs blancs reflètent ton absence. "
              "Un ordre si parfait qu’il en devient inhumain.",
        "2": "Une maison ancienne t’accueille. "
              "Le bois craque sous tes pas, les portraits te suivent du regard. "
              "Un feu mourant lutte encore dans la cheminée. "
              "Tu ressens une chaleur étrange, celle d’un souvenir que tu n’as jamais eu.",
        "3": "Une chambre d’hôtel impersonnelle. "
              "Le papier peint se décolle, le néon grésille. "
              "Des centaines de vies sont passées ici, mais aucune n’a laissé de trace durable.",
        "4": "Un hôpital. Blême, silencieux. "
              "Le bip d’une machine rythme ton souffle. "
              "Tu es seul, mais les murs semblent écouter. "
              "Ici, tout est stérile, sauf la peur.",
        "5": "Des câbles, des écrans, des seringues. "
              "Tu es dans un laboratoire. Ton existence ici n’est pas naturelle. "
              "Quelque chose t’a créé, ou t’a copié.",
        "6": "Des ruines s’étendent à perte de vue. "
              "Le vent emporte des bribes de voix anciennes. "
              "Chaque pierre raconte une histoire que plus personne n’écoute."
    },

    "objet": {
        "1": "Sur la table, une carte d’identité. Ton visage y sourit, mais le nom est étranger. "
              "Tu trembles. Qui es-tu vraiment ?",
        "2": "Un badge d’entreprise. Le logo t’est inconnu, mais tu ressens un frisson en le touchant. "
              "Tu sens qu’il a été ton dernier lien avec une vie effacée.",
        "3": "Une photo jaunie. Ton visage y apparaît, entouré de rires et d’inconnus. "
              "Mais leurs regards sont vides, absents, figés dans un instant sans fin.",
        "4": "Une lettre pliée, adressée à toi. L’écriture est nerveuse, les mots tremblants : "
              "‘Ne cherche pas à comprendre.’ Tu relis encore et encore, sans oser l’ouvrir davantage.",
        "5": "Un téléphone vibre. Des dizaines de messages attendent. ‘Où es-tu ?’, ‘On sait.’, ‘Fuis.’ "
              "Tu sens le danger approcher, mais tu ignores de quoi il s’agit.",
        "6": "Rien. Juste ton reflet dans un miroir fissuré. "
              "Un instant, ton image sourit alors que toi, non."
    },

    "souvenir": {
        "1": "Une voix douce te parvient, lointaine. "
              "Tu ris, sous la pluie, aux côtés de quelqu’un que tu aimes. "
              "Puis la scène s’efface, ne laissant qu’une chaleur dans ta poitrine.",
        "2": "Une douleur remonte. Une trahison, un adieu. "
              "Tu revois un regard que tu n’as pas su retenir. "
              "Ton cœur se serre, incapable de distinguer le réel du souvenir.",
        "3": "Tu te souviens d’une autre vie. Une rue différente, un corps différent. "
              "Les visages changent, mais la peur reste la même.",
        "4": "Un phare. Une mer calme. Une silhouette t’attend, au loin. "
              "Tu sais que ce lieu détient une vérité enfouie.",
        "5": "Une sensation étrange, une lumière chaude. "
              "Quelque chose ou quelqu’un te guide, bienveillant mais invisible. "
              "Tu n’es peut-être pas seul.",
        "6": "Le vide. Tu tends la main, mais il n’y a rien. "
              "Ton esprit flotte, libre, effrayé, face à l’infini de lui-même."
    },

    "rencontre": {
        "1": "Un bruit à la porte. Trois coups précis. "
              "Tu retiens ton souffle. L’air se fige. "
              "Quand tu ouvres, il n’y a personne… mais la poignée est encore tiède.",
        "2": "Une voix naît dans ta tête, familière. "
              "Elle t’appelle par ton vrai nom — celui que tu ne te rappelais plus. "
              "Elle murmure : ‘Il est temps de te souvenir.’",
        "3": "Un craquement derrière toi. Une ombre bondit. "
              "Tu tombes, le souffle coupé. La peur pure. Et pourtant, tu te sens vivant.",
        "4": "Une silhouette t’approche. Son visage est flou, mais sa présence apaise. "
              "‘Tu n’as jamais été seul’, dit-elle avant de disparaître.",
        "5": "Une vision t’aveugle : un œil immense, un symbole ardent. "
              "La vérité cherche à te parler, mais ton esprit se déchire sous le poids de sa lumière.",
        "6": "Rien. Le monde s’éteint. "
              "Tu es seul avec toi-même, et c’est peut-être la pire des rencontres."
    },

    "choix": {
        "1": "Une porte close. Un mot gravé : ‘Souviens-toi’. "
              "Tu hésites. La poignée brûle sous tes doigts.",
        "2": "Tu marches dans un couloir sans fin. "
              "Chaque pas t’éloigne de toi-même, mais tu continues, poussé par l’instinct.",
        "3": "Une lumière au bout du chemin. Tu veux y croire, même si tu sens le piège.",
        "4": "Tu trébuches. Le sol se dérobe. Rien ne répond plus à la logique. "
              "Le monde se transforme, ou c’est toi qui changes.",
        "5": "Tu fermes les yeux et avances sans réfléchir. "
              "Le courage et la folie ont parfois le même goût.",
        "6": "Tout devient clair. Chaque élément trouve sa place. "
              "La cohérence naît enfin de la confusion."
    },

    "revelation": {
        "1": "Ce corps appartenait à une âme disparue. "
              "Tu portes désormais la mémoire d’un autre, ses regrets, ses espoirs. "
              "Peut-être n’es-tu qu’un hôte de passage.",
        "2": "Tu comprends : rien de tout cela n’est réel. "
              "Tu es un souvenir errant, une conscience oubliée dans une machine de chair.",
        "3": "Des voix s’élèvent en toi. Elles sont toutes toi, et pourtant différentes. "
              "Ton esprit est une mosaïque brisée.",
        "4": "La vérité tombe : tu es le fruit d’une expérience. "
              "Un esprit transplanté, une conscience déchirée. "
              "Ton existence est un mensonge bien programmé.",
        "5": "Les pièces du puzzle s’assemblent. Un nom revient, une ville, un visage. "
              "La clarté t’envahit, belle et terrifiante à la fois.",
        "6": "Tu sais. Enfin. Et cette vérité te fait trembler plus que le mensonge ne l’aurait fait."
    },

    "conclusion": {
        "1": "Tu retrouves ton corps d’origine, mais quelque chose de ce voyage est resté en toi. "
              "Tu n’es plus la même personne.",
        "2": "Tu choisis de rester. Ce nouveau corps devient le tien, cette vie, ton nouveau commencement.",
        "3": "Tu comprends que tu n’as jamais existé. Tu es un souvenir né d’un autre rêve.",
        "4": "Tout s’efface. Tu ouvres les yeux. "
              "Mais au fond de toi, une voix murmure : ‘Et si tu dormais encore ?’",
        "5": "Ton esprit et ce corps ne font plus qu’un. "
              "Le passé s’efface, le futur s’ouvre, vaste et inconnu.",
        "6": "Le silence retombe. L’histoire s’achève ici… ou recommence ailleurs. "
              "Car chaque réveil est une nouvelle naissance."
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
