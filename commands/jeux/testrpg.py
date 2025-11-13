# ────────────────────────────────────────────────────────────────────────────────
# 📌 testrpg.py — Commande simple /testrpg et !testrpg
# Objectif : JDR solo “Réveil” avec boutons pour découvrir l’histoire chapitre par chapitre
# Catégorie : Autre
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands
import random
from utils.discord_utils import safe_send, safe_respond  # Utilitaires sécurisés

# ────────────────────────────────────────────────────────────────────────────────
# 🎮 JDR JSON — version "raconte ton histoire"
# ────────────────────────────────────────────────────────────────────────────────
jdr_json = {
    "intro": (
        "🌌 **Réveil étrange**\n\n"
        "Tu ouvres les yeux. L’air est froid. Ton corps te semble étranger. "
        "Tes souvenirs se dispersent comme de la fumée. Où es-tu ? Et surtout… qui es-tu ?"
    ),

    "chambre": {
        "1": "Une chambre trop parfaite. Rien ne dépasse, pas un grain de poussière. "
              "Tu ressens une gêne, comme si l’ordre des lieux cachait un secret.",
        "2": "La pièce semble abandonnée. Le lit défait, une tasse vide, une fenêtre entrouverte. "
              "Quelqu’un vivait ici… récemment.",
        "3": "La lumière du matin traverse les rideaux. Tout semble paisible, presque familier. "
              "Tu pourrais croire que tu es chez toi, mais ce n’est pas le cas.",
        "4": "Une chambre luxueuse, décorée avec soin. Mais les détails trahissent la hâte : "
              "une porte forcée, un miroir fissuré, un parfum qui flotte encore.",
        "5": "Tout ici défie la logique : les aiguilles d’une horloge tournent à l’envers, "
              "un tableau change quand tu ne le regardes pas. Tu n’es pas dans un lieu ordinaire.",
        "6": "La pièce est en ruine. Des plantes ont envahi le sol, la pluie s’infiltre. "
              "Ce lieu a été oublié depuis longtemps."
    },

    "corps": {
        "1": "Tu observes tes mains : ce ne sont pas les tiennes. Trop jeunes, trop fines. "
              "Tu habites le corps d’un autre.",
        "2": "Ton reflet te fixe dans une vitre. Le visage est le tien, mais différent. "
              "Quelque chose d’autre vit derrière ces yeux.",
        "3": "Tu ressens la lourdeur de l’âge. Chaque mouvement est une épreuve. "
              "Ton souffle est court, mais ton esprit est vif.",
        "4": "Ton corps est jeune, plein d’énergie. Tu sens que tu pourrais courir des heures. "
              "Mais ce n’est pas ton corps.",
        "5": "Même sexe, même âge, mais tout sonne faux. "
              "Ta voix, ton regard, ta démarche — rien ne colle à ton souvenir.",
        "6": "Tu portes un corps marqué par la vie. Chaque ride raconte une histoire que tu ignores."
    },

    "lieu": {
        "1": "Un appartement blanc, sans bruit, sans odeur. Trop propre. "
              "Tu comprends qu’il a été préparé pour toi.",
        "2": "Une vieille maison t’accueille. Le parquet grince, un feu s’éteint dans la cheminée. "
              "Tu ressens une étrange chaleur familière.",
        "3": "Une chambre d’hôtel anonyme. Un lieu de passage. "
              "Tu te demandes combien d’inconnus se sont réveillés ici avant toi.",
        "4": "Tu es dans une chambre d’hôpital. Les murs pâles te renvoient ton silence. "
              "Un moniteur émet un bip régulier, presque rassurant.",
        "5": "Des machines t’entourent. Des câbles sont branchés à ton bras. "
              "Tu es dans un laboratoire. Ton réveil n’était pas naturel.",
        "6": "Autour de toi, des ruines. Le vent siffle à travers des pierres effondrées. "
              "Ce monde semble avoir survécu à quelque chose."
    },

    "objet": {
        "1": "Sur la table, une carte d’identité. Ta photo, mais un autre nom. "
              "Tu trembles en la lisant.",
        "2": "Un badge d’entreprise. Le logo t’est inconnu, mais tu sens que tu y as travaillé. "
              "Ton passé n’est peut-être pas perdu.",
        "3": "Une vieille photo. Tu y es, entouré d’inconnus souriants. "
              "Mais leurs visages sont flous, effacés par le temps.",
        "4": "Une lettre cachetée porte ton nom. Les mots à l’intérieur te glacent : "
              "« Ne te fie à personne. »",
        "5": "Un téléphone clignote. Des dizaines de messages : ‘Fuis.’, ‘On t’a retrouvé.’, ‘Vite.’ "
              "Quelque chose approche.",
        "6": "Rien, sauf un miroir fissuré. Ton reflet te sourit, alors que tu ne bouges pas."
    },

    "souvenir": {
        "1": "Tu entends une voix. Douce, familière. "
              "Un souvenir heureux, puis la douleur de l’avoir perdu.",
        "2": "Une image revient : un départ, un adieu. Tu te souviens de la tristesse, pas des visages.",
        "3": "Des vies s’entremêlent dans ton esprit. Tu as été plusieurs personnes, ou peut-être aucune.",
        "4": "Tu vois la mer. Un phare au loin. Quelqu’un t’y attend. "
              "Tu ressens l’urgence d’y retourner.",
        "5": "Une lumière te guide, bienveillante. Tu sens qu’elle veut t’aider à comprendre.",
        "6": "Le vide. Aucun souvenir. Tu existes, mais tu ignores pourquoi."
    },

    "rencontre": {
        "1": "Trois coups frappent à la porte. Personne dehors. "
              "Mais la poignée est encore chaude.",
        "2": "Une voix parle dans ta tête. Elle t’appelle par ton vrai nom. "
              "Tu n’en avais aucun souvenir.",
        "3": "Un bruit derrière toi. Une silhouette se jette dans l’ombre. "
              "Ton cœur s’emballe.",
        "4": "Une présence approche. Elle ne te veut pas de mal. "
              "Tu ressens une paix étrange avant qu’elle disparaisse.",
        "5": "Une vision t’aveugle. Un symbole ardent te traverse l’esprit. "
              "Tu comprends… mais trop tard.",
        "6": "Rien. Le silence absolu. Tu es seul, complètement seul."
    },

    "choix": {
        "1": "Une porte close. Sur le bois, un mot gravé : ‘Souviens-toi’. "
              "La poignée brûle sous ta main.",
        "2": "Un long couloir s’étend devant toi. Tu avances, sans savoir où il mène.",
        "3": "Une lumière t’appelle au loin. Elle semble t’attendre, ou te piéger.",
        "4": "Le sol se dérobe. Le monde change autour de toi. Rien n’a plus de sens.",
        "5": "Tu décides d’avancer les yeux fermés. Parfois, il faut croire sans comprendre.",
        "6": "Tout devient clair. Les fragments s’assemblent. Tu vois enfin le tableau entier."
    },

    "revelation": {
        "1": "Ce corps n’est pas le tien. Tu vis la mémoire d’un autre.",
        "2": "Tu n’es pas réel. Tu es un souvenir piégé dans une conscience artificielle.",
        "3": "Tu comprends : tu es plusieurs à la fois. Un esprit fragmenté, un être éclaté.",
        "4": "Tu as été créé. Une expérience, un test. Une conscience transplantée.",
        "5": "Tout revient : un nom, un lieu, une histoire. La vérité est là, terrifiante et belle.",
        "6": "Tu sais enfin. Mais cette vérité te hante plus encore que le doute."
    },

    "conclusion": {
        "1": "Tu retrouves ton vrai corps. Mais quelque chose en toi est resté de ce voyage.",
        "2": "Tu décides de rester. Ce nouveau corps devient ton refuge.",
        "3": "Tu comprends que tu n’as jamais vécu. Tu n’étais qu’une idée fugace.",
        "4": "Tu ouvres les yeux dans un autre monde. Peut-être un rêve. Peut-être le vrai réveil.",
        "5": "Ton passé s’efface. Ton avenir commence ici.",
        "6": "Le silence t’enveloppe. L’histoire s’achève… ou recommence ailleurs."
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
