# ────────────────────────────────────────────────────────────────────────────────
# 📌 solorpg.py — Commande Solo RPG / Livres dont vous êtes le héros
# Objectif : Permet de choisir une histoire et de progresser dedans
# Catégorie : Jeux
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
import json
import os
from utils.discord_utils import safe_send, safe_respond

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class SoloRPG(commands.Cog):
    """
    Commande /solorpg et !solorpg — Choisis une histoire et progresse dedans
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.histoires_path = "data/solorpg"
        self.histoires = self.load_histoires()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Chargement des histoires
    # ────────────────────────────────────────────────────────────────────────────
    def load_histoires(self):
        histoires = {}
        for fichier in os.listdir(self.histoires_path):
            if fichier.endswith(".json"):
                chemin = os.path.join(self.histoires_path, fichier)
                with open(chemin, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    histoires[data["titre"]] = data
        return histoires

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Affichage d'une étape
    # ────────────────────────────────────────────────────────────────────────────
    async def afficher_etape(self, ctx_or_interaction, histoire, index, historique=None):
        """Affiche une étape et ses options dans un seul embed avec boutons."""
        contenu = histoire["contenu"]
        if historique is None:
            historique = []
    
        # Si on dépasse la fin de l'histoire
        if index >= len(contenu):
            embed = discord.Embed(
                title=histoire["titre"],
                description="🏁 Fin de l'histoire !",
                color=discord.Color.green()
            )
            if isinstance(ctx_or_interaction, commands.Context):
                await safe_send(ctx_or_interaction.channel, embed=embed)
            else:
                await safe_respond(ctx_or_interaction, embed=embed)
            return
    
        etape = contenu[index]
        description = etape["texte"]
        options = etape.get("options", [])
    
        # Texte des choix (dans l'embed)
        texte_choix = ""
        for i, option in enumerate(options, start=1):
            texte_choix += f"\n`{i}` — {option['texte']} *(→ {option.get('suivant', index + 1)})*"
    
        embed = discord.Embed(
            title=f"{histoire['titre']} — Étape {index + 1}",
            description=f"{description}\n\n**Choix :**{texte_choix if texte_choix else '\nAucun choix disponible.'}",
            color=discord.Color.blurple()
        )
    
        view = discord.ui.View(timeout=None)
    
        # Ajout des boutons pour les choix
        if options:
            for i, option in enumerate(options):
                label = f"Aller à {option.get('suivant', index + 1)}"
                bouton = discord.ui.Button(label=label, style=discord.ButtonStyle.primary)
    
                async def callback(interaction: discord.Interaction, i=i):
                    prochain_index = options[i].get("suivant", index + 1)
                    # Ajoute l'étape actuelle à l'historique
                    new_historique = historique + [index]
                    await self.afficher_etape(interaction, histoire, prochain_index, historique=new_historique)
    
                bouton.callback = callback
                view.add_item(bouton)
        else:
            bouton = discord.ui.Button(label="Fin de l'histoire", style=discord.ButtonStyle.secondary, disabled=True)
            view.add_item(bouton)
    
        # Bouton retour si possible
        if historique:
            bouton_retour = discord.ui.Button(label="⬅️ Retour", style=discord.ButtonStyle.secondary)
    
            async def retour_callback(interaction: discord.Interaction):
                dernier_index = historique[-1]
                await self.afficher_etape(interaction, histoire, dernier_index, historique=historique[:-1])
    
            bouton_retour.callback = retour_callback
            view.add_item(bouton_retour)
    
        # Envoie ou met à jour le message selon le type d’interaction
        if isinstance(ctx_or_interaction, commands.Context):
            await safe_send(ctx_or_interaction.channel, embed=embed, view=view)
        else:
            try:
                await ctx_or_interaction.response.edit_message(embed=embed, view=view)
            except discord.errors.InteractionResponded:
                await ctx_or_interaction.edit_original_response(embed=embed, view=view)


    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(name="solorpg", description="Commence une histoire Solo RPG.")
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_solorpg(self, interaction: discord.Interaction):
        """Commande slash avec menu déroulant"""
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
        """Commande préfixe avec menu déroulant identique au slash"""
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
        await safe_send(ctx.channel, "📖 Choisis une histoire :", view=view)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = SoloRPG(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Jeux"
    await bot.add_cog(cog)
