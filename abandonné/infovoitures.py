# ────────────────────────────────────────────────────────────────────────────────
# 📌 infovoitures.py — Commande /infovoitures et !infovoitures
# Objectif : Afficher la liste des voitures ou la fiche complète d'une voiture
# Catégorie : Voiture
# Accès : Tous
# Cooldown : 5 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands
from discord import app_commands
import os, json

from utils.discord_utils import safe_send

# ────────────────────────────────────────────────────────────────────────────────
# 📂 Chargement des données JSON des voitures
# ────────────────────────────────────────────────────────────────────────────────
DATA_PATH = "data/voitures"

def load_voitures():
    voitures = []
    for file in os.listdir(DATA_PATH):
        if file.endswith(".json"):
            with open(os.path.join(DATA_PATH, file), "r", encoding="utf-8") as f:
                voitures.append(json.load(f))
    return voitures

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class InfoVoitures(commands.Cog):
    """
    Commande /infovoitures et !infovoitures — Liste des voitures ou fiche détaillée
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.voitures = load_voitures()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction pour afficher toutes les voitures (pagination 20 par page)
    # ────────────────────────────────────────────────────────────────────────────
    async def send_liste_voitures(self, channel):
        voitures_sorted = sorted(self.voitures, key=lambda x: x["nom"])
        pages = [voitures_sorted[i:i + 20] for i in range(0, len(voitures_sorted), 20)]

        class VoituresPaginator(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=120)
                self.current_page = 0

            async def update_message(self, interaction=None):
                page_voitures = pages[self.current_page]
                embed = discord.Embed(
                    title="📋 Liste des voitures disponibles",
                    color=discord.Color.blurple()
                )
                embed.description = "\n".join(
                    f"**{v['nom']}** — 🏅 {v['rarete'].capitalize()}" for v in page_voitures
                )
                embed.set_footer(text=f"Page {self.current_page + 1}/{len(pages)} — {len(voitures_sorted)} voitures disponibles")

                if interaction:
                    await interaction.response.edit_message(embed=embed, view=self)
                else:
                    await safe_send(channel, embed=embed, view=self)

            @discord.ui.button(label="◀️", style=discord.ButtonStyle.grey)
            async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
                if self.current_page > 0:
                    self.current_page -= 1
                    await self.update_message(interaction)

            @discord.ui.button(label="▶️", style=discord.ButtonStyle.grey)
            async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
                if self.current_page < len(pages) - 1:
                    self.current_page += 1
                    await self.update_message(interaction)

        paginator = VoituresPaginator()
        await paginator.update_message()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction pour afficher une voiture spécifique
    # ────────────────────────────────────────────────────────────────────────────
    async def send_voiture_details(self, channel, nom_voiture):
        voiture = next(
            (v for v in self.voitures if nom_voiture.lower() in v["nom"].lower()), 
            None
        )

        if not voiture:
            return await safe_send(channel, f"❌ Voiture `{nom_voiture}` introuvable.")

        # Couleurs selon rareté
        colors = {
            "commun": discord.Color.light_grey(),
            "rare": discord.Color.blue(),
            "épique": discord.Color.purple(),
            "légendaire": discord.Color.gold()
        }
        color = colors.get(voiture["rarete"].lower(), discord.Color.green())

        embed = discord.Embed(
            title=f"{voiture['nom']} — {voiture['rarete'].capitalize()}",
            description=voiture.get("description", "Aucune description disponible."),
            color=color
        )

        # Image
        image_url = voiture.get("image")
        if image_url and image_url.startswith(("http://", "https://")):
            embed.set_thumbnail(url=image_url)
        else:
            embed.set_thumbnail(url="https://upload.wikimedia.org/wikipedia/commons/6/65/No-Image-Placeholder.svg")

        # Stats
        stats = voiture.get("stats", {})
        formatted_stats = "\n".join(
            [f"**{k.replace('_', ' ').capitalize()}** : {v}" for k, v in stats.items()]
        )
        embed.add_field(name="📊 Caractéristiques", value=formatted_stats or "Aucune donnée", inline=False)

        await safe_send(channel, embed=embed)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(name="infovoitures", description="Liste les voitures ou affiche leurs détails")
    @app_commands.describe(nom="Nom de la voiture (optionnel)")
    async def slash_infovoitures(self, interaction: discord.Interaction, nom: str = None):
        await interaction.response.defer(ephemeral=True)
        if nom:
            await self.send_voiture_details(interaction.channel, nom)
        else:
            await self.send_liste_voitures(interaction.channel)
        await interaction.delete_original_response()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="infovoitures", aliases=["iv"])
    async def prefix_infovoitures(self, ctx: commands.Context, *, nom: str = None):
        if nom:
            await self.send_voiture_details(ctx.channel, nom)
        else:
            await self.send_liste_voitures(ctx.channel)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = InfoVoitures(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Voiture"
    await bot.add_cog(cog)
