# ────────────────────────────────────────────────────────────────────────────────
# 📌 choisir_classe.py — Commande interactive !classe /classe
# Objectif : Permet aux joueurs de choisir leur classe Reiatsu via des boutons et pagination
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
from datetime import datetime, timedelta, timezone
from dateutil import parser
import json
import os

from utils.supabase_client import supabase
from utils.discord_utils import safe_send, safe_respond, safe_edit
from utils.reiatsu_utils import ensure_profile

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
# 🎛️ UI — Pagination + Choix de classe
# ────────────────────────────────────────────────────────────────────────────────
class ClassePageView(View):
    def __init__(self, user_id: int, index: int = 0):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.index = index
        self.total = len(CLASSES)
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()

        # Boutons de navigation
        prev_btn = Button(label="⬅️ Précédent", style=discord.ButtonStyle.secondary)
        prev_btn.callback = self.prev_page
        self.add_item(prev_btn)

        next_btn = Button(label="➡️ Suivant", style=discord.ButtonStyle.secondary)
        next_btn.callback = self.next_page
        self.add_item(next_btn)

        # Bouton choisir
        choose_btn = Button(label="✅ Choisir cette classe", style=discord.ButtonStyle.success)
        choose_btn.callback = self.choose_class
        self.add_item(choose_btn)

    async def on_timeout(self):
        """Désactive automatiquement les boutons après le temps limite."""
        for item in self.children:
            item.disabled = True
        if hasattr(self, "message"):
            try:
                await safe_edit(self.message, view=self)
            except:
                pass

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await safe_respond(interaction, "❌ Tu ne peux pas interagir avec le menu d’un autre joueur.", ephemeral=True)
            return False
        return True

    # ──────────────────────────────
    # Callbacks
    # ──────────────────────────────
    async def prev_page(self, interaction: discord.Interaction):
        self.index = (self.index - 1) % self.total
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    async def next_page(self, interaction: discord.Interaction):
        self.index = (self.index + 1) % self.total
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    async def choose_class(self, interaction: discord.Interaction):
        nom, data = CLASSES[self.index]
        try:
            nouveau_cd = 19 if nom == "Voleur" else 24
            supabase.table("reiatsu").update({
                "classe": nom,
                "steal_cd": nouveau_cd
            }).eq("user_id", str(self.user_id)).execute()

            symbole = data.get("Symbole", "🌀")
            embed = discord.Embed(
                title=f"✅ Classe choisie : {symbole} {nom}",
                description=f"**Passive** : {data['Passive']}\n**Active** : {data['Active']}",
                color=discord.Color.green()
            )
            await interaction.response.edit_message(embed=embed, view=None)

        except Exception as e:
            await safe_respond(interaction, f"❌ Erreur lors de l'enregistrement : {e}", ephemeral=True)

    def get_embed(self):
        nom, data = CLASSES[self.index]
        symbole = data.get("Symbole", "🌀")
        embed = discord.Embed(
            title=f"🎭 Classe {self.index + 1}/{self.total} — {symbole} {nom}",
            description=f"**Passif** : {data['Passive']}\n**Skill** : {data['Active']}",
            color=discord.Color.purple()
        )
        embed.set_footer(text="Utilise les flèches pour naviguer et ✅ pour choisir cette classe")
        return embed

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class ChoisirClasse(commands.Cog):
    """Commande !classe ou /classe — Choisir sa classe Reiatsu via pagination et boutons"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config = config


    # ────────────────────────────────────────────────────────────────────────
    # 🔹 Envoi du menu interactif
    # ────────────────────────────────────────────────────────────────────────
    async def _send_menu(self, channel: discord.abc.Messageable, user_id: int):
        view = ClassePageView(user_id)
        embed = view.get_embed()
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


