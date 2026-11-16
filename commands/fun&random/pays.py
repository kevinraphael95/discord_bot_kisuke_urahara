# ================================================================================
# 📌 genererpays.py
# Objectif : Générateur de pays fictif ultra-réaliste
# Catégorie : Fun&Random
# Accès : Tous
# Cooldown : 1 utilisation / 5 sec / utilisateur
# ================================================================================

# ================================================================================
# 📦 Modules standards
# ================================================================================
import random

# ================================================================================
# 📦  Modules tiers
# ================================================================================
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Select

# ================================================================================
# 📦 Modules internes
# ================================================================================
from utils.discord_anti429 import safe_send, safe_edit, safe_respond, safe_delete

# ================================================================================
# 🏷️ Données pondérées intégrées
# ================================================================================
DATA = {
    "forme_etat": [("République unitaire", 40), ("République fédérale", 15), ("Monarchie constitutionnelle", 20), ("Monarchie absolue", 5), ("République islamique", 5), ("État communiste", 3), ("Dictature militaire", 2), ("Théocratie", 3), ("Confédération", 4)],
    "religion": [("Christianisme (Catholicisme)", 30), ("Christianisme (Protestantisme)", 20), ("Islam (Sunnisme)", 25), ("Islam (Chiisme)", 10), ("Hindouisme", 15), ("Bouddhisme", 10), ("Sans religion / Athéisme", 15), ("Religions traditionnelles", 8)],
    "continent": [("Afrique", 54), ("Asie", 48), ("Europe", 44), ("Amérique du Nord", 23), ("Amérique du Sud", 12), ("Océanie", 14)],
    "acces_mer": [("Accès à la mer", 80), ("Enclavé", 20)],
    "ressources": [("Pétrole et Gaz", 20), ("Minerais précieux", 15), ("Bois et Forêts", 20), ("Terres agricoles fertiles", 30), ("Eau douce", 10), ("Rares ou inexistantes", 5)],
    "impact_regional": [("Superpuissance régionale", 10), ("Puissance économique majeure", 20), ("Pays stable et influent", 30), ("Pays neutre / isolé", 25), ("Pays en crise / instable", 15)],
    "climat": [("Tempéré", 30), ("Tropical", 25), ("Aride (Désertique)", 15), ("Polaire", 5), ("Montagneux", 15), ("Méditerranéen", 10)]
}

LANGUES = ["Français", "Anglais", "Espagnol", "Arabe", "Mandarin", "Russe", "Portugais", "Allemand", "Japonais", "Hindi"]
CAPITALES_PREFIX = ["San", "Nova", "Port", "Saint-", "Fort", "Villa", "Val"]
CAPITALES_SUFFIX = ["ville", "bourg", "grad", "polis", "heim", "ton", "city"]

# ================================================================================
# 🎲 Utilitaires
# ================================================================================
def tirer_pondere(options):
    valeurs = [opt[0] for opt in options]
    poids = [opt[1] for opt in options]
    return random.choices(valeurs, weights=poids, k=1)[0]

# ================================================================================
# 🏗️ Générateur de pays (logique ultra-réaliste)
# ================================================================================
def generer_pays(continent_force=None):
    forme_etat = tirer_pondere(DATA["forme_etat"])
    religion = tirer_pondere(DATA["religion"])
    continent = continent_force if continent_force else tirer_pondere(DATA["continent"])
    acces_mer = tirer_pondere(DATA["acces_mer"])
    ressources = tirer_pondere(DATA["ressources"])
    impact_regional = tirer_pondere(DATA["impact_regional"])
    climat = tirer_pondere(DATA["climat"])

    # --- Logique de richesse ---
    score_richesse = random.randint(20, 80)
    if acces_mer == "Accès à la mer": score_richesse += 15
    if ressources in ["Pétrole et Gaz", "Minerais précieux"]: score_richesse += 20
    elif ressources == "Rares ou inexistantes": score_richesse -= 25
    if impact_regional == "Superpuissance régionale": score_richesse += 30
    elif impact_regional == "Pays en crise / instable": score_richesse -= 35

    # --- Logique politique ---
    democratie = 5.0
    armee_bonus = 0
    if "République" in forme_etat or "Monarchie constitutionnelle" in forme_etat:
        democratie += random.uniform(2, 5)
        score_richesse += 10
    elif "Dictature" in forme_etat or "communiste" in forme_etat:
        democratie -= random.uniform(2, 4)
        score_richesse -= 15
        armee_bonus = 100000
    elif "Théocratie" in forme_etat or "Monarchie absolue" in forme_etat:
        democratie -= random.uniform(3, 5)
        score_richesse -= 20
    democratie = max(0.5, min(10, democratie))

    # --- Économie ---
    if score_richesse > 75:
        economie = "Développée"; idh = round(random.uniform(0.85, 0.98), 3)
        pib_par_hab = random.randint(30000, 80000); esperance = random.randint(78, 86)
    elif score_richesse > 40:
        economie = "Émergente"; idh = round(random.uniform(0.65, 0.84), 3)
        pib_par_hab = random.randint(6000, 25000); esperance = random.randint(65, 77)
    else:
        economie = "En développement"; idh = round(random.uniform(0.30, 0.64), 3)
        pib_par_hab = random.randint(500, 5000); esperance = random.randint(50, 64)

    # --- Démographie (cohérence climat) ---
    superficie = random.randint(10000, 5000000)
    densite_base = random.randint(20, 150)
    if climat == "Aride (Désertique)": superficie = random.randint(500000, 7000000); densite_base = random.randint(2, 20)
    if climat == "Polaire": superficie = random.randint(500000, 8000000); densite_base = random.randint(1, 10)
    if climat in ["Tempéré", "Méditerranéen"]: densite_base += 30
    if climat == "Tropical": densite_base += 20
    if democratie < 3: densite_base = int(densite_base * 0.8)
    
    population = superficie * densite_base
    densite = round(population / superficie, 1)
    pib_total = int((population * pib_par_hab) / 1000000)

    # --- Armée ---
    if impact_regional == "Superpuissance régionale": armee = random.randint(500000, 1500000)
    elif score_richesse > 70: armee = random.randint(100000, 400000)
    elif score_richesse < 30: armee = random.randint(5000, 50000)
    else: armee = random.randint(20000, 200000)
    armee += armee_bonus

    # --- Divers ---
    chomage = round(random.uniform(10 - (score_richesse/10), 25 - (score_richesse/5)), 1)
    dette = round(random.uniform(20, 180), 1)
    
    nom = f"{random.choice(['République', 'Royaume', 'Empire', 'Fédération', 'Union', 'Principauté'])} de {random.choice(['Valoria', 'Zephyria', 'Aethelgard', 'Kaltara', 'Oseron', 'Virelia', 'Brumelande', 'Thalassa', 'Necromia', 'Aurelia'])}"
    capitale = f"{random.choice(CAPITALES_PREFIX)}{random.choice(CAPITALES_SUFFIX)}"
    langue = random.choice(LANGUES)
    mois = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
    fete = f"{random.randint(1, 28)} {random.choice(mois)}"

    return {
        "nom": nom, "forme_etat": forme_etat, "religion": religion, "continent": continent,
        "acces_mer": acces_mer, "ressources": ressources, "impact_regional": impact_regional,
        "climat": climat, "economie": economie, "idh": idh, "pib_total": pib_total,
        "chomage": chomage, "esperance": esperance, "superficie": superficie,
        "population": population, "densite": densite, "armee": armee, "dette": dette,
        "fete": fete, "democratie": round(democratie, 1), "capitale": capitale, "langue": langue
    }

# ================================================================================
# 🎛️ UI — Premier menu interactif
# ================================================================================
class FirstSelectView(View):
    def __init__(self, bot):
        super().__init__(timeout=120)
        self.bot = bot
        self.message = None
        self.add_item(FirstSelect(self))

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message:
            await safe_edit(self.message, view=self)

class FirstSelect(Select):
    def __init__(self, parent_view: FirstSelectView):
        self.parent_view = parent_view
        options = [
            discord.SelectOption(label="🌍 Monde entier (Aléatoire)", value="TOUS"),
            discord.SelectOption(label="Europe", value="Europe"),
            discord.SelectOption(label="Asie", value="Asie"),
            discord.SelectOption(label="Afrique", value="Afrique"),
            discord.SelectOption(label="Amérique du Nord", value="Amérique du Nord"),
            discord.SelectOption(label="Amérique du Sud", value="Amérique du Sud"),
            discord.SelectOption(label="Océanie", value="Océanie"),
        ]
        super().__init__(placeholder="Sélectionne un continent", options=options)

    async def callback(self, interaction: discord.Interaction):
        selected_key = self.values[0]
        new_view = SecondSelectView(self.parent_view.bot, selected_key)
        new_view.message = interaction.message
        await safe_edit(
            interaction.message,
            content=f"Continent sélectionné : **{selected_key}**\nPrêt à générer ?",
            embed=None,
            view=new_view
        )

# ================================================================================
# 🎛️ UI — Deuxième menu interactif
# ================================================================================
class SecondSelectView(View):
    def __init__(self, bot, continent):
        super().__init__(timeout=120)
        self.bot = bot
        self.continent = continent
        self.message = None
        self.add_item(SecondSelect(self))

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message:
            await safe_edit(self.message, view=self)

class SecondSelect(Select):
    def __init__(self, parent_view: SecondSelectView):
        self.parent_view = parent_view
        options = [
            discord.SelectOption(label="🎲 Générer le pays", value="generer"),
            discord.SelectOption(label="🔙 Retour", value="retour")
        ]
        super().__init__(placeholder="Que veux-tu faire ?", options=options)

    async def callback(self, interaction: discord.Interaction):
        action = self.values[0]
        
        if action == "retour":
            new_view = FirstSelectView(self.parent_view.bot)
            new_view.message = interaction.message
            await safe_edit(
                interaction.message,
                content="🌍 **Générateur de pays**\nChoisis un continent :",
                embed=None,
                view=new_view
            )
            return

        # Action "generer"
        pays = generer_pays()
        if self.parent_view.continent != "TOUS":
            pays["continent"] = self.parent_view.continent

        embed = discord.Embed(
            title=f"🌍 {pays['nom']}",
            description=f"Un pays situé en **{pays['continent']}**, avec un climat **{pays['climat']}**.\n"
                        f"Capitale : **{pays['capitale']}** — Langue : **{pays['langue']}**",
            color=discord.Color.random()
        )
        
        embed.add_field(name="🏛️ Forme d'État", value=pays['forme_etat'], inline=True)
        embed.add_field(name="🗳️ Démocratie", value=f"{pays['democratie']}/10", inline=True)
        embed.add_field(name="🌊 Accès mer", value=pays['acces_mer'], inline=True)

        embed.add_field(name="⛪ Religion", value=pays['religion'], inline=True)
        embed.add_field(name="🎉 Fête nationale", value=pays['fete'], inline=True)
        embed.add_field(name="🌍 Impact régional", value=pays['impact_regional'], inline=True)

        embed.add_field(name="💎 Ressources", value=pays['ressources'], inline=True)
        embed.add_field(name="💰 Économie", value=pays['economie'], inline=True)
        embed.add_field(name="📊 IDH", value=str(pays['idh']), inline=True)

        embed.add_field(name="💸 PIB total", value=f"{pays['pib_total']:,} M$", inline=True)
        embed.add_field(name="📉 Chômage", value=f"{pays['chomage']} %", inline=True)
        embed.add_field(name="💳 Dette", value=f"{pays['dette']} % du PIB", inline=True)

        embed.add_field(name="👥 Population", value=f"{pays['population']:,} hab.", inline=True)
        embed.add_field(name="📏 Superficie", value=f"{pays['superficie']:,} km²", inline=True)
        embed.add_field(name="🏙️ Densité", value=f"{pays['densite']} hab/km²", inline=True)

        embed.add_field(name="⏳ Espérance de vie", value=f"{pays['esperance']} ans", inline=True)
        embed.add_field(name="🪖 Armée", value=f"{pays['armee']:,} soldats", inline=True)

        await safe_edit(
            interaction.message,
            content=None,
            embed=embed,
            view=None
        )

# ================================================================================
# 🧠 Cog principal (SANS gestion des cooldowns)
# ================================================================================
class GenerateurPaysCommand(commands.Cog):
    """
    Commande /genererpays et !genererpays — Génère un pays fictif via menus
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ============================================================================
    # 🔹 Fonction interne commune
    # ============================================================================
    async def _send_menu(self, channel: discord.abc.Messageable):
        view = FirstSelectView(self.bot)
        view.message = await safe_send(channel, "🌍 **Générateur de pays**\nChoisis un continent (ou aléatoire) :", view=view)

    # ============================================================================
    # 🔹 Commande SLASH
    # ============================================================================
    @app_commands.command(name="genererpays", description="🌍 Génère un pays fictif aléatoire complet.")
    @app_commands.checks.cooldown(rate=1, per=5.0, key=lambda i: i.user.id)
    async def slash_genererpays(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self._send_menu(interaction.channel)
        await interaction.delete_original_response()

    # ============================================================================
    # 🔹 Commande PREFIX
    # ============================================================================
    @commands.command(name="genererpays", aliases=["genpays"])
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_genererpays(self, ctx: commands.Context):
        await self._send_menu(ctx.channel)

# ================================================================================
# 🔌 Setup du Cog
# ================================================================================
async def setup(bot: commands.Bot):
    cog = GenerateurPaysCommand(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Fun&Random"
    await bot.add_cog(cog)
