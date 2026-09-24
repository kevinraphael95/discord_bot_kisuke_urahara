# ================================================================================
# 📌 tutoreiatsu.py — Tutoriel interactif /tutoreiatsu et !tutoreiatsu
# Objectif : Afficher un guide interactif paginé pour les nouveaux joueurs
# Catégorie : Reiatsu
# Accès : Tous
# Cooldown : 1 utilisation / 10 secondes / utilisateur
# ================================================================================

# ================================================================================
# 📦 Imports nécessaires
# ================================================================================
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button
from utils.discord_utils import safe_send, safe_edit, safe_interact

# ================================================================================
# 📂 Données du tutoriel
# ================================================================================
PAGES = [
    {
        "title": "📖 Bienvenue dans le mini-jeu de absorption Reiatsu",
        "description": (
            "💠 Le Reiatsu apparaît régulièrement sur le serveur sur le salon [insérer nom du salon].\n\n"
            "- Quand un Reiatsu apparaît sur le serveur, absorbe le en cliquant sur l'emoji en réaction.\n"
            "- Un Reiatsu normal rapporte +1 et un Super Reiatsu rapporte +100 (rare)\n"
            "- Le but est de récupérer le plus de Reiatsu possible, le Reiatsu aura des utilités plus tard."
        ),
        "color": discord.Color.purple()
    },
    {
        "title": "⚡ Commandes principales",
        "description": (
            "- `!!reiatsu` ou `!!rts` : Voir les infos générales : sur quel salon le reiatsu apparaît et dans combien de temps et le classement (top 10).\n"
            "- `!!reiatsuprofil` ou `!!p` : Voir ton profil qui contient toutes tes infos : ta quantité de Reiatsu, ta classe, et le cooldown de ton skill\n"
            "- `!!classe` pour choisir ou changer ta classe"
        ),
        "color": discord.Color.blue()
    },
    {
        "title": "🎭 Choisir une classe",
        "description": (
            "Chaque classe a un **passif** et un **skill actif**\n"
            "Le passif s'active automatiqument, le skill doit être activé avec la commande `!!skill`.\n\n"
            "[insérer classes passifs et skills]"
        ),
        "color": discord.Color.green()
    }, 
    {
        "title": "🩸 Voler du Reiatsu",
        "description": (
            "📌 Commande : `!!reiatsuvol @joueur` ou `!rtsv @joueur` pour voler du reiatsu à un autre joueur.\n\n"
            "- De base tu as 25% de chance de voler 10% du reiatsu d'un joueur et un cooldown de 24h.\n"
            "- Mais les classes Voleur et Illusioniste influencent ces stats."
        ),
        "color": discord.Color.red()
    },
    {
        "title": "Monter de niveaux grace aux quêtes",
        "description": (
            "La commande `!!quetes` permet de voir les quêtes à faire pour monter de niveau.\n"
            "Le niveau de départ est 0. Chaque quête accomplie fait monter le niveau de 1.\n"
            "Chaque niveau supplémentaire donnera ces boosts :\n"
            "- +0.5% de chance d'avoir un Super Reiatsu lors d'une absorption d'un Reiatsu\n"
            "- Autre chose ?"
        ),
        "color": discord.Color.teal()
    },
    {
        "title": "💡 Astuces",
        "description": (
            "1. La commande `!!motsecret` permet de gagner jusqu'à 1000 reiatsu, vas voir.\n"
            "2. La commande `!!keylottery` ou `!!kl` permet de miser 250 reiatsu pour les doubler ou gagner une clé steam.\n"
            "3. Coucou comment ça va yo.\n"
            "4. [insérer astuce]"
        ),
        "color": discord.Color.teal()
    }
]

# ================================================================================
# 🎛️ UI — Navigation paginée avec boutons
# ================================================================================
class TutoView(View):
    def __init__(self, user_id: int):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.index = 0
        self.message = None

    def get_embed(self):
        page = PAGES[self.index]
        embed = discord.Embed(
            title=page["title"],
            description=page["description"],
            color=page["color"]
        )
        embed.set_footer(text=f"Page {self.index + 1}/{len(PAGES)}")
        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await safe_interact(interaction, content="❌ Tu ne peux pas interagir avec ce tutoriel.", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            await safe_edit(self.message, view=self)

    @discord.ui.button(label="⬅️ Précédent", style=discord.ButtonStyle.secondary)
    async def prev_page(self, interaction: discord.Interaction, button: Button):
        self.index = (self.index - 1) % len(PAGES)
        await safe_interact(interaction, embed=self.get_embed(), view=self, edit=True)

    @discord.ui.button(label="➡️ Suivant", style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction: discord.Interaction, button: Button):
        self.index = (self.index + 1) % len(PAGES)
        await safe_interact(interaction, embed=self.get_embed(), view=self, edit=True)

# ================================================================================
# 🧠 Cog principal
# ================================================================================
class TutoReiatsu(commands.Cog):
    """Commande /tutoreiatsu et !tutoreiatsu — Tutoriel interactif Reiatsu"""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # 🔹 Fonction interne pour envoyer le tutoriel
    async def _send_tuto(self, channel: discord.abc.Messageable, user_id: int):
        view = TutoView(user_id)
        view.message = await safe_send(channel, embed=view.get_embed(), view=view)

    # 🔹 Commande SLASH
    @app_commands.command(
        name="tutoreiatsu",
        description="Affiche le tutoriel complet pour les nouveaux joueurs."
    )
    @app_commands.checks.cooldown(rate=1, per=10.0, key=lambda i: i.user.id)
    async def slash_tuto(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self._send_tuto(interaction.channel, interaction.user.id)
        await interaction.delete_original_response()

    # 🔹 Commande PREFIX
    @commands.command(
        name="tutoreiatsu", aliases=["tutorts", "reiatsututo", "rtstuto"],
        help="Affiche le tutoriel complet pour les nouveaux joueurs."
    )
    @commands.cooldown(1, 10.0, commands.BucketType.user)
    async def prefix_tuto(self, ctx: commands.Context):
        await self._send_tuto(ctx.channel, ctx.author.id)

# ================================================================================
# 🔌 Setup du Cog
# ================================================================================
async def setup(bot: commands.Bot):
    cog = TutoReiatsu(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Reiatsu"
    await bot.add_cog(cog)
