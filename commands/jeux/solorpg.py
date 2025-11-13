# ────────────────────────────────────────────────────────────────────────────────
# 📌 solorpg.py — Commande Solo RPG / Livres dont vous êtes le héros
# Objectif : Permet de choisir une histoire et de progresser dedans
# Catégorie : Autre
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

import discord
from discord import app_commands
from discord.ext import commands
import json
import os
from utils.discord_utils import safe_send, safe_respond

# ────────────────────────────────────────────────────────────────────────────────
class SoloRPG(commands.Cog):
    """Commande /solorpg et !solorpg — Choisis une histoire et progresse dedans."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.histoires_path = "data/solorpg"
        self.histoires = self.load_histoires()

    def load_histoires(self):
        histoires = {}
        for fichier in os.listdir(self.histoires_path):
            if fichier.endswith(".json"):
                chemin = os.path.join(self.histoires_path, fichier)
                with open(chemin, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    histoires[data["titre"]] = data
        return histoires

    async def afficher_etape(self, ctx_or_interaction, histoire, index):
        """Affiche une étape et ses options sous forme de boutons."""
        contenu = histoire["contenu"]
        if index >= len(contenu):
            embed = discord.Embed(title=histoire["titre"],
                                  description="🏁 Fin de l'histoire !",
                                  color=discord.Color.green())
            if isinstance(ctx_or_interaction, commands.Context):
                await safe_send(ctx_or_interaction.channel, embed=embed)
            else:
                await safe_respond(ctx_or_interaction, embed=embed)
            return

        etape = contenu[index]
        description = etape["texte"]
        options = etape.get("options", [])

        embed = discord.Embed(title=histoire["titre"], description=description, color=discord.Color.green())

        view = discord.ui.View()
        if options:
            for i, option in enumerate(options):
                bouton = discord.ui.Button(label=option["texte"], style=discord.ButtonStyle.primary)
                async def callback(interaction: discord.Interaction, i=i):
                    # On passe à l'étape suivante définie dans "suivant"
                    prochain_index = options[i].get("suivant", index + 1)
                    await self.afficher_etape(interaction, histoire, prochain_index)
                bouton.callback = callback
                view.add_item(bouton)
        else:
            # Pas d'options : bouton pour terminer
            bouton = discord.ui.Button(label="Terminer", style=discord.ButtonStyle.secondary, disabled=True)
            view.add_item(bouton)

        if isinstance(ctx_or_interaction, commands.Context):
            await safe_send(ctx_or_interaction.channel, embed=embed, view=view)
        else:
            await safe_respond(ctx_or_interaction, embed=embed, view=view)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(name="solorpg", description="Commence une histoire Solo RPG.")
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_solorpg(self, interaction: discord.Interaction):
        # Sélecteur d'histoire
        select = discord.ui.Select(
            placeholder="Choisis ton histoire...",
            options=[discord.SelectOption(label=titre) for titre in self.histoires.keys()]
        )
        async def select_callback(select_interaction: discord.Interaction):
            titre = select_interaction.data["values"][0]
            histoire = self.histoires[titre]
            await self.afficher_etape(select_interaction, histoire, 0)
        select.callback = select_callback

        view = discord.ui.View()
        view.add_item(select)
        await safe_respond(interaction, "📖 Choisis une histoire :", view=view)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="solorpg")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_solorpg(self, ctx: commands.Context):
        description = "Choisis une histoire disponible :\n" + "\n".join(f"- {titre}" for titre in self.histoires.keys())
        await safe_send(ctx.channel, description)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = SoloRPG(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Autre"
    await bot.add_cog(cog)
