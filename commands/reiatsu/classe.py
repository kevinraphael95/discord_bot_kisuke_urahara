# ────────────────────────────────────────────────────────────────────────────────
# 📌 choisir_classe.py — Commande interactive !classe /classe
# Objectif : Afficher toutes les classes Reiatsu sur une seule page
#             et permettre au joueur d’en choisir une via un bouton
# Catégorie : Reiatsu
# Accès : Public
# Cooldown : 1 utilisation / 10 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button
import json
import os

from utils.supabase_client import supabase
from utils.discord_utils import safe_send, safe_respond, safe_edit

# ────────────────────────────────────────────────────────────────────────────────
# 📂 Chargement de la configuration Reiatsu
# ────────────────────────────────────────────────────────────────────────────────
REIATSU_CONFIG_PATH = os.path.join("data", "reiatsu_config.json")

def load_reiatsu_config():
    """Charge la configuration Reiatsu depuis le fichier JSON."""
    try:
        with open(REIATSU_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERREUR JSON] Impossible de charger {REIATSU_CONFIG_PATH} : {e}")
        return {}

config = load_reiatsu_config()
CLASSES = list(config.get("CLASSES", {}).items())

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ UI — Liste complète des classes avec boutons
# ────────────────────────────────────────────────────────────────────────────────
class ClasseSelectView(View):
    def __init__(self, user_id: int):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.create_buttons()

    def create_buttons(self):
        """Crée un bouton pour chaque classe définie dans la config Reiatsu."""
        for nom, data in CLASSES:
            symbole = data.get("Symbole", "🌀")
            btn = Button(label=f"{symbole} {nom}", style=discord.ButtonStyle.primary)
            btn.callback = self._generate_callback(nom, data)
            self.add_item(btn)

    def _generate_callback(self, nom, data):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user_id:
                await safe_respond(interaction, "❌ Tu ne peux pas choisir pour un autre joueur.", ephemeral=True)
                return

            try:
                nouveau_cd = 19 if nom == "Voleur" else 24
                supabase.table("reiatsu").update({
                    "classe": nom,
                    "steal_cd": nouveau_cd
                }).eq("user_id", str(self.user_id)).execute()

                symbole = data.get("Symbole", "🌀")
                embed = discord.Embed(
                    title=f"✅ Classe choisie : {symbole} {nom}",
                    description=f"**Passive :** {data['Passive']}\n**Active :** {data['Active']}",
                    color=discord.Color.green()
                )
                await interaction.response.edit_message(embed=embed, view=None)

            except Exception as e:
                await safe_respond(interaction, f"❌ Erreur lors de l'enregistrement : {e}", ephemeral=True)
        return callback

    async def on_timeout(self):
        """Désactive les boutons après expiration."""
        for item in self.children:
            item.disabled = True
        if hasattr(self, "message"):
            try:
                await safe_edit(self.message, view=self)
            except:
                pass

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class ChoisirClasse(commands.Cog):
    """Commande !classe ou /classe — Choisir sa classe Reiatsu via une vue complète"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config = config

    # ────────────────────────────────────────────────────────────────────────
    # 🔹 Envoi du menu interactif
    # ────────────────────────────────────────────────────────────────────────
    async def _send_menu(self, channel: discord.abc.Messageable, user_id: int):
        view = ClasseSelectView(user_id)
        description = "\n\n".join(
            [
                f"{data.get('Symbole', '🌀')} **{nom}**\n"
                f"> 🧩 **Passive :** {data['Passive']}\n"
                f"> ⚡ **Active :** {data['Active']}"
                for nom, data in CLASSES
            ]
        )

        embed = discord.Embed(
            title="🎭 Choisis ta classe Reiatsu",
            description=description,
            color=discord.Color.purple()
        )
        embed.set_footer(text="Clique sur le bouton correspondant à la classe que tu veux choisir.")

        message = await safe_send(channel, embed=embed, view=view)
        view.message = message

    # ────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────
    @commands.command(name="classe", help="Choisir sa classe Reiatsu")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def classe_prefix(self, ctx: commands.Context):
        await self._send_menu(ctx.channel, ctx.author.id)

    # ────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────
    @app_commands.command(name="classe", description="Choisir sa classe Reiatsu")
    async def classe_slash(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self._send_menu(interaction.channel, interaction.user.id)
        try:
            await interaction.delete_original_response()
        except discord.Forbidden:
            pass

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = ChoisirClasse(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Reiatsu"
    await bot.add_cog(cog)
