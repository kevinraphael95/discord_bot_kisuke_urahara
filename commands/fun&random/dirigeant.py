# ================================================================================
# 📌 dirigeant.py — Commande /dirigeant et !dirigeant
# Objectif : Roast aléatoire d'un dirigeant FICTIF (généré au hasard) ou d'un
#            capitaine du Gotei 13. Aucune personne réelle n'est ciblée.
# Catégorie : Fun & Random
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# Usage prefix : !dirigeant [bleach]
# ================================================================================

# ================================================================================
# 📦 Imports nécessaires
# ================================================================================
import random

import discord
from discord import app_commands
from discord.ext import commands

CATEGORY = "Fun & Random"

# ================================================================================
# 🎲 Générateur de dirigeant fictif
# ================================================================================
TITRES = [
    "Président", "Empereur suprême", "Grand Chancelier", "Maréchal-Président",
    "Premier Ministre perpétuel", "Sultan", "Généralissime", "Roi",
]
SYLLABES = ["bor", "kal", "zu", "mir", "vlad", "tek", "no", "ras", "gul", "pi", "dan", "ox", "fre", "lum", "wak"]
PAYS = [
    "la République démocratique de Bananie", "le Royaume uni de Patatistan",
    "l'Empire de Moldavie-du-Sud", "la Principauté de Trucbidule",
    "la Fédération des Îles Quelque-Part", "le Grand Duché de Pasdidée",
]

INSULTES_FICTIF = [
    "{nom} a mis trois mandats à comprendre que le bouton « démissionner » existait.",
    "Même le GPS de {pays} refuse de suivre la direction que prend {nom}.",
    "{nom} a déjà signé un traité de paix avec lui-même. Il l'a perdu le lendemain.",
    "{nom} dirige {pays} comme on conduit un caddie de supermarché : en zigzag et sans savoir où ça va.",
    "Le discours de {nom} durait 4 heures, et il a quand même réussi à ne rien dire.",
    "{nom} a nommé son chat ministre des Finances. Le chat s'en sort mieux.",
    "{nom} a inauguré un pont. Il n'y avait pas de rivière. Personne n'a osé le dire.",
    "Le budget de {pays} sous {nom} : 90 % de statues de {nom}, 10 % de statues plus grandes de {nom}.",
    "{nom} a perdu un référendum qu'il avait lui-même organisé. À un seul votant.",
    "{nom} a dit « je n'ai peur de rien », puis a fui devant un pigeon.",
    "{nom} est le seul dirigeant à avoir été destitué par un diaporama PowerPoint.",
    "Pour {nom}, un plan quinquennal, c'est cinq fois le même plan, avec des fautes différentes.",
]

# ================================================================================
# ⚔️ Capitaines du Gotei 13 (personnages fictifs)
# ================================================================================
BLEACH = {
    "Yamamoto": [
        "{nom} a 2000 ans d'expérience et toujours aucun sens de la diplomatie.",
        "{nom} règle chaque réunion d'équipe en brûlant la salle. Les RH ont renoncé.",
        "{nom} a transformé le mot « mesure proportionnée » en insulte.",
    ],
    "Aizen": [
        "{nom} a un plan pour tout, surtout pour te dire que tout était prévu depuis le début.",
        "{nom} a trahi tout le monde et trouve ça « plutôt cohérent avec son agenda ».",
        "Dans une partie de cache-cache, {nom} annoncerait que tu l'avais trouvé exprès.",
    ],
    "Kurotsuchi": [
        "{nom} appelle ça une « expérience », la Soul Society appelle ça un incident de sécurité.",
        "Les comités d'éthique ont cessé d'envoyer des mails à {nom}, ils font directement des prières.",
        "{nom} a un labo plus grand que son sens de l'empathie, et ce n'est pas peu dire.",
    ],
    "Zaraki": [
        "{nom} s'est perdu dans son propre escalier. Il l'a coupé en deux pour être sûr.",
        "{nom} ne lit jamais les notices : il les découpe.",
        "Pour {nom}, une réunion se termine quand il n'y a plus de chaises debout.",
    ],
    "Byakuya": [
        "{nom} regarde les gens de haut. Même ceux qui sont plus grands. Surtout eux.",
        "{nom} a pris 40 ans à dire « merci ». Il a fallu un décret.",
        "Le règlement de {nom} contient un règlement pour le règlement.",
    ],
    "Ukitake": [
        "{nom} annule une réunion sur deux. Et pourtant c'est lui qu'on attend le plus.",
        "{nom} est tellement gentil que les ennemis lui demandent des conseils de carrière.",
    ],
    "Kyoraku": [
        "{nom} a transformé « je vais faire une sieste » en politique d'État.",
        "Le plan de bataille de {nom} : improviser, puis dire que c'était voulu.",
    ],
    "Hitsugaya": [
        "{nom} est capitaine, ne l'appelle jamais « petit ». Il le fait savoir, très froidement.",
        "{nom} fait baisser la température des réunions de 15 degrés, y compris les relations humaines.",
    ],
}

# ================================================================================
# 🔧 Génération
# ================================================================================
def fictional_leader() -> str:
    nom = "".join(random.choices(SYLLABES, k=random.randint(2, 3))).capitalize()
    nom = f"{random.choice(TITRES)} {nom}"
    pays = random.choice(PAYS)
    return random.choice(INSULTES_FICTIF).format(nom=nom, pays=pays)


def bleach_leader() -> str:
    nom = random.choice(list(BLEACH))
    return random.choice(BLEACH[nom]).format(nom=f"Capitaine {nom}")


def make_embed(bleach: bool) -> discord.Embed:
    text = bleach_leader() if bleach else fictional_leader()
    return discord.Embed(
        title="🎭 Roast d'un dirigeant (fictif)",
        description=text,
        color=discord.Color.dark_red(),
    ).set_footer(text="Personnage inventé. Aucune ressemblance avec des personnes réelles.")


# ================================================================================
# 🧠 Cog principal
# ================================================================================
class Dirigeant(commands.Cog):
    """Commande /dirigeant et !dirigeant — Roast aléatoire d'un dirigeant fictif"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ============================================================================
    # 🔹 Commande SLASH
    # ============================================================================
    @app_commands.command(name="dirigeant", description="Un dirigeant fictif tiré au hasard se fait descendre.")
    @app_commands.describe(bleach="Cible un capitaine du Gotei 13 au lieu d'un dirigeant inventé")
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_dirigeant(self, interaction: discord.Interaction, bleach: bool = False):
        await interaction.response.send_message(embed=make_embed(bleach))

    # ============================================================================
    # 🔹 Commande PREFIX
    # ============================================================================
    @commands.command(name="dirigeant", help="Roast aléatoire d'un dirigeant fictif. Ajoute 'bleach' pour un capitaine.")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_dirigeant(self, ctx: commands.Context, mode: str = ""):
        await ctx.send(embed=make_embed(mode.lower() == "bleach"))


# ================================================================================
# 🔌 Setup du Cog
# ================================================================================
async def setup(bot: commands.Bot):
    cog = Dirigeant(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = CATEGORY
    await bot.add_cog(cog)
