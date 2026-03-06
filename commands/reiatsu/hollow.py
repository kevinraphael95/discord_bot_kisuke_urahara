# ────────────────────────────────────────────────────────────────────────────────
# 📌 hollow.py — Commande interactive !hollow / /hollow
# Objectif : Faire apparaître un Hollow, attaquer (1 reiatsu), réussir 3 tâches.
# Catégorie : Reiatsu
# Accès : Public
# Cooldown : 1 utilisation / 10 sec / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import os

import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button

from utils.discord_utils import safe_send, safe_edit, safe_respond
from utils.init_db import get_conn
from utils.taches import lancer_3_taches

# ────────────────────────────────────────────────────────────────────────────────
# 📂 Constantes
# ────────────────────────────────────────────────────────────────────────────────
HOLLOW_IMAGE_PATH = os.path.join("data", "images", "hollows", "hollow0.jpg")
REIATSU_COST = 1

# ────────────────────────────────────────────────────────────────────────────────
# 🗄️ Helpers DB (via get_conn() de init_db)
# ────────────────────────────────────────────────────────────────────────────────
def get_points(user_id: int) -> int:
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT points FROM reiatsu WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else 0

def remove_points(user_id: int, amount: int):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE reiatsu SET points = MAX(points - ?, 0) WHERE user_id = ?",
        (amount, user_id)
    )
    conn.commit()
    conn.close()

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ UI — Bouton d'attaque
# ────────────────────────────────────────────────────────────────────────────────
class HollowView(View):
    def __init__(self, author: discord.Member, embed: discord.Embed):
        super().__init__(timeout=60)
        self.author = author
        self.embed = embed
        self.message = None
        self.add_item(AttackButton(author, embed))

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message:
            await safe_edit(self.message, view=self)


class AttackButton(Button):
    def __init__(self, author: discord.Member, embed: discord.Embed):
        super().__init__(label="⚔️ Attaquer", style=discord.ButtonStyle.danger)
        self.author = author
        self.embed = embed

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            return await safe_respond(interaction, "❌ Ce combat ne t'appartient pas.", ephemeral=True)

        for child in self.view.children:
            child.disabled = True
        await interaction.response.edit_message(view=self.view)

        remove_points(self.author.id, REIATSU_COST)

        self.embed.title = "⚔️ Combat contre le Hollow"
        self.embed.description = (
            f"{self.author.display_name} affronte le Hollow !\n\n"
            f"🌀 Trois épreuves vont être lancées... sois prêt !"
        )
        self.embed.color = discord.Color.orange()
        await interaction.edit_original_response(embed=self.embed, attachments=[], view=None)

        async def update_embed(e: discord.Embed):
            await interaction.edit_original_response(embed=e)

        self.embed.clear_fields()
        self.embed.add_field(name="Préparation...", value="Les épreuves vont commencer...", inline=False)
        await update_embed(self.embed)

        victoire = await lancer_3_taches(interaction, self.embed, update_embed)

        result = discord.Embed(
            title="🎯 Résultat du combat",
            description=(
                f"🎉 Tu as vaincu le Hollow ! Bravo, {self.author.mention} !"
                if victoire else
                f"💀 Le Hollow t'a vaincu... retente ta chance !"
            ),
            color=discord.Color.green() if victoire else discord.Color.red()
        )
        result.set_footer(text=f"Combat terminé pour {self.author.display_name}")
        await interaction.edit_original_response(embed=result, view=None)

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class Hollow(commands.Cog):
    """👹 Combat contre un Hollow — dépense du reiatsu et réussis 3 épreuves !"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction interne commune
    # ────────────────────────────────────────────────────────────────────────────
    async def _start_hollow(self, channel: discord.abc.Messageable, author: discord.Member):
        if not os.path.isfile(HOLLOW_IMAGE_PATH):
            return await safe_send(channel, "❌ Image du Hollow introuvable.")

        reiatsu = get_points(author.id)
        if reiatsu < REIATSU_COST:
            return await safe_send(channel, f"❌ Il te faut au moins {REIATSU_COST} reiatsu pour attaquer un Hollow.")

        file = discord.File(HOLLOW_IMAGE_PATH, filename="hollow.jpg")
        embed = discord.Embed(
            title="👹 Un Hollow est apparu !",
            description=(
                f"{author.mention}, un Hollow approche... ⚠️\n"
                f"Clique sur **Attaquer** pour dépenser {REIATSU_COST} reiatsu et lancer le combat."
            ),
            color=discord.Color.dark_red()
        )
        embed.set_image(url="attachment://hollow.jpg")
        embed.set_footer(text="Tu as 60 secondes pour agir.")

        view = HollowView(author, embed)
        view.message = await safe_send(channel, embed=embed, file=file, view=view)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="hollow",
        description="👹 Fais apparaître un Hollow et tente de le vaincre (1 reiatsu requis)."
    )
    @app_commands.checks.cooldown(rate=1, per=10.0, key=lambda i: i.user.id)
    async def slash_hollow(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await self._start_hollow(interaction.channel, interaction.user)
        await interaction.delete_original_response()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="hollow", help="👹 Fais apparaître un Hollow et tente de le vaincre (1 reiatsu requis).")
    @commands.cooldown(1, 10.0, commands.BucketType.user)
    async def prefix_hollow(self, ctx: commands.Context):
        await self._start_hollow(ctx.channel, ctx.author)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Hollow(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Reiatsu"
    await bot.add_cog(cog)
