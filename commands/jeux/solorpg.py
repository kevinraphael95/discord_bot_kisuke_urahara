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
# 🧠 Cog principal : SoloRPG
# ────────────────────────────────────────────────────────────────────────────────
class SoloRPG(commands.Cog):
    """
    Commande /solorpg et !solorpg — Choisis une histoire et progresse dedans.
    Compatible avec le format JSON { "titre": ..., "contenu": [ { "page": ..., "texte": ..., "options": [...] } ] }
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.histoires_path = "data/solorpg"
        self.histoires = self.load_histoires()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Chargement des histoires
    # ────────────────────────────────────────────────────────────────────────────
    def load_histoires(self):
        """Charge tous les fichiers JSON depuis data/solorpg"""
        histoires = {}
        if not os.path.exists(self.histoires_path):
            os.makedirs(self.histoires_path)

        for fichier in os.listdir(self.histoires_path):
            if fichier.endswith(".json"):
                chemin = os.path.join(self.histoires_path, fichier)
                try:
                    with open(chemin, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if "titre" in data:
                            histoires[data["titre"]] = data
                except Exception as e:
                    print(f"⚠️ Erreur lors du chargement de {fichier} : {e}")

        return histoires

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Affichage d'une étape
    # ────────────────────────────────────────────────────────────────────────────
    async def afficher_etape(self, ctx_or_interaction, histoire, page, historique=None):
        """Affiche une page avec ses choix et gère les boutons de navigation."""
        contenu = histoire.get("contenu", [])
        if historique is None:
            historique = []

        # ── Fin de l'histoire ──
        if page > len(contenu) or page <= 0:
            embed = discord.Embed(
                title=histoire.get("titre", "Histoire inconnue"),
                description="🏁 **Fin de l'histoire !** Merci d'avoir joué 🎉",
                color=discord.Color.green()
            )
            if isinstance(ctx_or_interaction, commands.Context):
                await safe_send(ctx_or_interaction.channel, embed=embed)
            else:
                await safe_respond(ctx_or_interaction, embed=embed)
            return

        etape = contenu[page - 1]
        texte = etape.get("texte", "...")
        options = etape.get("options", [])

        # ── Création de l'embed ──
        embed = discord.Embed(
            title=f"{histoire['titre']} — Page {page}",
            description=texte,
            color=discord.Color.blurple()
        )

        # ── Ajout des choix dans l'embed ──
        if options:
            desc_choix = "\n".join(
                [f"`{i+1}` — {opt['texte']} *(→ Page {opt.get('suivant', page+1)})*"
                 for i, opt in enumerate(options)]
            )
            embed.add_field(name="Choix disponibles :", value=desc_choix, inline=False)
        else:
            embed.add_field(name="Aucun choix disponible", value="Fin de cette branche.", inline=False)

        # ── Vue (boutons interactifs) ──
        view = discord.ui.View(timeout=None)

        # Boutons de choix
        if options:
            for i, option in enumerate(options):
                label = option.get("texte", f"Choix {i+1}")
                style = discord.ButtonStyle.primary
                bouton = discord.ui.Button(label=label, style=style)

                async def callback(interaction: discord.Interaction, i=i):
                    prochain_page = options[i].get("suivant", page+1)
                    new_historique = historique + [page]
                    await self.afficher_etape(interaction, histoire, prochain_page, historique=new_historique)

                bouton.callback = callback
                view.add_item(bouton)
        else:
            bouton = discord.ui.Button(label="Fin", style=discord.ButtonStyle.secondary, disabled=True)
            view.add_item(bouton)

        # Bouton retour
        if historique:
            bouton_retour = discord.ui.Button(label="⬅️ Retour", style=discord.ButtonStyle.secondary)

            async def retour_callback(interaction: discord.Interaction):
                dernier_page = historique[-1]
                await self.afficher_etape(interaction, histoire, dernier_page, historique=historique[:-1])

            bouton_retour.callback = retour_callback
            view.add_item(bouton_retour)

        # Envoi du message
        if isinstance(ctx_or_interaction, commands.Context):
            await safe_send(ctx_or_interaction.channel, embed=embed, view=view)
        else:
            try:
                await ctx_or_interaction.response.edit_message(embed=embed, view=view)
            except discord.errors.InteractionResponded:
                await ctx_or_interaction.edit_original_response(embed=embed, view=view)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Menu de sélection d'histoire (Slash)
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(name="solorpg", description="Commence une histoire Solo RPG interactive.")
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_solorpg(self, interaction: discord.Interaction):
        """Commande /solorpg — avec menu déroulant pour choisir une histoire"""
        if not self.histoires:
            return await safe_respond(interaction, "⚠️ Aucune histoire trouvée dans `data/solorpg/`.")

        select = discord.ui.Select(
            placeholder="📖 Choisis ton histoire...",
            options=[
                discord.SelectOption(label=titre, description=f"Histoire interactive : {titre}")
                for titre in self.histoires.keys()
            ]
        )

        async def select_callback(select_interaction: discord.Interaction):
            titre = select_interaction.data["values"][0]
            histoire = self.histoires[titre]
            await self.afficher_etape(select_interaction, histoire, 1)

        select.callback = select_callback
        view = discord.ui.View()
        view.add_item(select)
        await safe_respond(interaction, "✨ Choisis une histoire à explorer :", view=view)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande préfixe (!solorpg)
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="solorpg")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_solorpg(self, ctx: commands.Context):
        """Commande préfixe identique à la slash, avec menu déroulant"""
        if not self.histoires:
            return await safe_send(ctx.channel, "⚠️ Aucune histoire trouvée dans `data/solorpg/`.")

        select = discord.ui.Select(
            placeholder="📖 Choisis ton histoire...",
            options=[
                discord.SelectOption(label=titre, description=f"Histoire interactive : {titre}")
                for titre in self.histoires.keys()
            ]
        )

        async def select_callback(select_interaction: discord.Interaction):
            titre = select_interaction.data["values"][0]
            histoire = self.histoires[titre]
            await self.afficher_etape(select_interaction, histoire, 1)

        select.callback = select_callback
        view = discord.ui.View()
        view.add_item(select)
        await safe_send(ctx.channel, "✨ Choisis une histoire à explorer :", view=view)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = SoloRPG(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Jeux"
    await bot.add_cog(cog)
