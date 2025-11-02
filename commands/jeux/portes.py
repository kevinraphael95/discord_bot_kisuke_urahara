# ────────────────────────────────────────────────────────────────────────────────
# 📌 portes.py — Jeu des Portes interactif
# Objectif : Résoudre des énigmes et progresser à travers les portes
# Catégorie : Jeux / Fun
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord, json, unicodedata
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Modal, TextInput, Button
from pathlib import Path
from utils.discord_utils import safe_send, safe_interact
from utils.supabase_client import supabase

# ────────────────────────────────────────────────────────────────────────────────
# 📂 Chargement des énigmes
# ────────────────────────────────────────────────────────────────────────────────
ENIGMES_PATH = Path("data/enigmes_portes.json")
with ENIGMES_PATH.open("r", encoding="utf-8") as f:
    ENIGMES = json.load(f)

# ────────────────────────────────────────────────────────────────────────────────
# 🧩 Fonction utilitaire
# ────────────────────────────────────────────────────────────────────────────────
def normalize(text: str) -> str:
    text = text.strip().lower()
    text = ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    )
    return text

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Modal de réponse
# ────────────────────────────────────────────────────────────────────────────────
class ReponseModal(Modal):
    def __init__(self, parent_view):
        super().__init__(title=f"🔑 Réponse — {parent_view.enigme['titre']}")
        self.parent_view = parent_view
        self.answer_input = TextInput(
            label="Ta réponse",
            placeholder="Entre ta réponse ici...",
            required=True
        )
        self.add_item(self.answer_input)

    async def on_submit(self, interaction: discord.Interaction):
        await self.parent_view.check_answer(interaction, self.answer_input.value)

# ────────────────────────────────────────────────────────────────────────────────
# 🎮 Boutons et vue principale
# ────────────────────────────────────────────────────────────────────────────────
class RepondreButton(Button):
    def __init__(self, parent_view):
        super().__init__(label="💬 Répondre", style=discord.ButtonStyle.primary)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.parent_view.user_id:
            return await safe_interact(interaction, content="⛔ Ce n’est pas ton tour.", ephemeral=True)
        await interaction.response.send_modal(ReponseModal(self.parent_view))


class ContinuerButton(Button):
    def __init__(self, parent_view, next_enigme):
        super().__init__(label="▶ Continuer", style=discord.ButtonStyle.success)
        self.parent_view = parent_view
        self.next_enigme = next_enigme

    async def callback(self, interaction: discord.Interaction):
        new_view = PortesView(self.next_enigme, self.parent_view.user_id)
        await safe_interact(interaction, content=None, edit=True, embed=new_view.build_embed(), view=new_view)


class PortesView(View):
    def __init__(self, enigme, user_id):
        super().__init__(timeout=None)
        self.enigme = enigme
        self.user_id = user_id
        self.add_item(RepondreButton(self))

    def build_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=f"🚪 Porte {self.enigme['id']} — {self.enigme['titre']}",
            description=f"**Énigme :**\n{self.enigme['enigme']}",
            color=discord.Color.blurple()
        )
        embed.set_footer(text="Clique sur le bouton pour répondre.")
        return embed

    async def check_answer(self, interaction: discord.Interaction, answer: str):
        if interaction.user.id != self.user_id:
            return await safe_interact(interaction, content="⛔ Ce n’est pas ton tour.", ephemeral=True)

        normalized = normalize(answer)
        valid_answers = self.enigme["reponse"]
        if isinstance(valid_answers, str):
            valid_answers = [valid_answers]
        valid_answers = [normalize(r) for r in valid_answers]

        if normalized in valid_answers:
            # Récupération Supabase
            data = supabase.table("reiatsu_portes").select("*").eq("user_id", interaction.user.id).execute()
            user_data = data.data[0] if data.data else None
            current_door = user_data["current_door"] if user_data else 1
            points = user_data["points"] if user_data else 0

            next_door = current_door + 1
            reward_message = ""
            if current_door == 100:
                points += 500
                reward_message = "🎉 Félicitations ! Tu as terminé toutes les portes et gagné **500 Reiatsu** !"

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

            # Message réponse
            await safe_interact(interaction,
                content=f"✅ Bonne réponse ! Tu passes à la porte {next_door} 🚪\n{reward_message}",
                ephemeral=True
            )

            # Préparer la prochaine énigme
            next_enigme = next((e for e in ENIGMES if e["id"] == next_door), None)
            if next_enigme and next_door <= 100:
                self.clear_items()
                self.add_item(ContinuerButton(self, next_enigme))
                await safe_interact(interaction, content=None, edit=True, embed=self.build_embed(), view=self)

        else:
            await safe_interact(interaction, content="❌ Mauvaise réponse... Essaie encore !", ephemeral=True)

# ────────────────────────────────────────────────────────────────────────────────
# 🧩 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class Portes(commands.Cog):
    """Jeu des Portes — version interactive"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def get_enigme(self, door_id: int):
        return next((e for e in ENIGMES if e["id"] == door_id), None)

    async def _start_portes(self, channel, user):
        data = supabase.table("reiatsu_portes").select("*").eq("user_id", user.id).execute()
        current_door = data.data[0]["current_door"] if data.data else 1
        enigme = self.get_enigme(current_door)
        if not enigme:
            return await safe_send(channel, "❌ Aucune énigme trouvée.")

        view = PortesView(enigme, user.id)
        embed = view.build_embed()

        await safe_send(channel,
            f"🚪 {user.mention} commence ou reprend le Jeu des Portes !\nClique sur **💬 Répondre** pour commencer.",
            embed=embed,
            view=view
        )

    # ────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────
    @app_commands.command(
        name="portes",
        description="Joue au Jeu des Portes et résous les énigmes pour avancer."
    )
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_portes(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self._start_portes(interaction.channel, interaction.user)

    # ────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────
    @commands.command(name="portes", help="Joue au Jeu des Portes et résous les énigmes.")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_portes(self, ctx: commands.Context):
        await self._start_portes(ctx.channel, ctx.author)


# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Portes(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Jeux"
    await bot.add_cog(cog)
