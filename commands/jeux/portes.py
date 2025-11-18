# ────────────────────────────────────────────────────────────────────────────────
# 📌 portes.py — Jeu des Portes interactif
# Objectif : Un mini-jeu avec 100 portes, énigmes, réponses modales et progression.
# Catégorie : Mini-jeux
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────


# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord, json, unicodedata
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput
from pathlib import Path

from utils.discord_utils import safe_send, safe_respond
from utils.supabase_client import supabase


# ────────────────────────────────────────────────────────────────────────────────
# 🔧 Utilitaire : normalisation (sans accents, minuscule)
# ────────────────────────────────────────────────────────────────────────────────
def normalize(text: str) -> str:
    text = text.strip().lower()
    text = ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    )
    return text


# ────────────────────────────────────────────────────────────────────────────────
# 📄 Chargement des énigmes
# ────────────────────────────────────────────────────────────────────────────────
ENIGMES_PATH = Path("data/enigmes_portes.json")
with ENIGMES_PATH.open("r", encoding="utf-8") as f:
    ENIGMES = json.load(f)


# ────────────────────────────────────────────────────────────────────────────────
# 📝 Modal de réponse
# ────────────────────────────────────────────────────────────────────────────────
class ReponseModal(Modal):
    def __init__(self, parent_view):
        super().__init__(title="🔑 Répondre à l'énigme")
        self.parent_view = parent_view

        self.answer = TextInput(
            label="Ta réponse",
            placeholder="Entre ta réponse ici...",
            required=True
        )
        self.add_item(self.answer)

    async def on_submit(self, interaction: discord.Interaction):
        await self.parent_view.process_answer(interaction, self.answer.value)


# ────────────────────────────────────────────────────────────────────────────────
# 👁 Vue principale
# ────────────────────────────────────────────────────────────────────────────────
class PortesView(View):
    def __init__(self, enigme, user_id):
        super().__init__(timeout=None)
        self.enigme = enigme
        self.user_id = user_id

        # Ajout du bouton
        self.add_item(RepondreButton(self))

    def build_embed(self):
        embed = discord.Embed(
            title=f"🚪 Porte {self.enigme['id']} — {self.enigme['titre']}",
            description=f"**Énigme :**\n{self.enigme['enigme']}",
            color=discord.Color.blurple()
        )
        embed.set_footer(text="Clique sur 💬 Répondre pour proposer une réponse.")
        return embed

    # ────────────────────────────────────────────────────────────────────────────
    # 🔍 Traitement de la réponse
    # ────────────────────────────────────────────────────────────────────────────
    async def process_answer(self, interaction: discord.Interaction, answer: str):

        # Protection : seul le joueur peut répondre
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message(
                "⛔ Ce n’est pas ton jeu.", ephemeral=True
            )

        normalized = normalize(answer)
        valid = self.enigme["reponse"]

        if isinstance(valid, str):
            valid = [valid]

        valid = [normalize(v) for v in valid]

        # Mauvaise réponse
        if normalized not in valid:
            return await interaction.response.send_message(
                "❌ Mauvaise réponse !", ephemeral=True
            )

        # Bonne réponse → progression + récompenses
        data = supabase.table("reiatsu_portes").select("*").eq("user_id", interaction.user.id).execute()
        user_data = data.data[0] if data.data else None

        current = user_data["current_door"] if user_data else 1
        points = user_data["points"] if user_data else 0

        next_door = current + 1
        reward_msg = ""

        # Si dernière porte
        if current == 100:
            points += 500
            reward_msg = "\n🎉 Tu as terminé les 100 portes ! +500 Reiatsu !"

        # Mise à jour Supabase
        if user_data:
            supabase.table("reiatsu_portes").update({
                "current_door": next_door,
                "points": points
            }).eq("user_id", interaction.user.id).execute()

        else:
            supabase.table("reiatsu_portes").insert({
                "user_id": interaction.user.id,
                "username": interaction.user.name,
                "current_door": next_door,
                "points": points
            }).execute()

        await interaction.response.send_message(
            f"✅ Bonne réponse ! Tu passes à la porte **{next_door}**.{reward_msg}",
            ephemeral=True
        )

        # Charge l'énigme suivante si elle existe
        next_enigme = next((e for e in ENIGMES if e["id"] == next_door), None)

        if next_enigme:
            new_view = PortesView(next_enigme, interaction.user.id)
            await interaction.message.edit(
                embed=new_view.build_embed(),
                view=new_view
            )


# ────────────────────────────────────────────────────────────────────────────────
# 🔘 Bouton "Répondre"
# ────────────────────────────────────────────────────────────────────────────────
class RepondreButton(Button):
    def __init__(self, parent_view):
        super().__init__(label="💬 Répondre", style=discord.ButtonStyle.primary)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.parent_view.user_id:
            return await interaction.response.send_message(
                "⛔ Pas ton jeu.", ephemeral=True
            )

        await interaction.response.send_modal(ReponseModal(self.parent_view))


# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class Portes(commands.Cog):
    """
    Commande /portes et !portes — Jeu des 100 Portes
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def get_enigme(self, door_id: int):
        return next((e for e in ENIGMES if e["id"] == door_id), None)

    async def start_game(self, channel, user):

        # Récupération ou création du profil joueur
        data = supabase.table("reiatsu_portes").select("*").eq("user_id", user.id).execute()
        current_door = data.data[0]["current_door"] if data.data else 1

        enigme = self.get_enigme(current_door)
        if not enigme:
            return await safe_send(channel, "❌ Impossible de charger l’énigme.")

        view = PortesView(enigme, user.id)

        await safe_send(
            channel,
            f"🚪 {user.mention} entre dans le **Jeu des Portes** !",
            embed=view.build_embed(),
            view=view
        )

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="portes",
        description="Commencer ou continuer le Jeu des 100 Portes."
    )
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_portes(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self.start_game(interaction.channel, interaction.user)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="portes")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_portes(self, ctx: commands.Context):
        await self.start_game(ctx.channel, ctx.author)


# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Portes(bot)
    # Ajout de la catégorie
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Mini-jeux"

    await bot.add_cog(cog)
