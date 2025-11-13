# ────────────────────────────────────────────────────────────────────────────────
# 📌 memory_formes.py — Commande Memory : retenir et choisir les formes
# Objectif : Jouer à un mini jeu mémoire avec une gridview de boutons
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
import random
from utils.discord_utils import safe_send, safe_respond

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class MemoryFormes(commands.Cog):
    """
    Commande /memory_formes et !memory_formes — Jouez au mini-jeu mémoire
    """
    FORMS = [
        ("❤️", "rouge"), ("💙", "bleu"), ("🤍", "blanc"),
        ("🟥", "rouge"), ("🟦", "bleu"), ("⬜", "blanc"),
        ("🔴", "rouge"), ("🔵", "bleu"), ("⚪", "blanc")
    ]

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="formes",
        description="Jouez au mini-jeu mémoire avec des formes et couleurs."
    )
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_memory_formes(self, interaction: discord.Interaction):
        await self.start_game(interaction)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="formes")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_memory_formes(self, ctx: commands.Context):
        await self.start_game(ctx)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction principale du jeu
    # ────────────────────────────────────────────────────────────────────────────
    async def start_game(self, ctx_or_interaction):
        user_id = ctx_or_interaction.user.id if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author.id

        # Choix aléatoire de 4 à 6 formes
        sequence = random.sample(self.FORMS, random.randint(4,6))
        sequence_str = " ".join([f"{s[0]}" for s in sequence])
        # Affiche la série à mémoriser
        msg = await safe_send(ctx_or_interaction.channel if hasattr(ctx_or_interaction, "channel") else ctx_or_interaction, f"🔹 Retenez cette série :\n{sequence_str}")
        await discord.utils.sleep_until(discord.utils.utcnow() + discord.utils.timedelta(seconds=5))  # pause 5s

        # Supprime la série
        try:
            await msg.delete()
        except:
            pass

        # ── Création de la gridView
        view = discord.ui.View(timeout=30)

        # On garde l'ordre des boutons mélangé
        buttons = random.sample(self.FORMS, len(self.FORMS))
        for symbol, color in buttons:
            view.add_item(MemoryButton(symbol, color, sequence, user_id))

        # Message final avec les boutons
        await safe_send(ctx_or_interaction.channel if hasattr(ctx_or_interaction, "channel") else ctx_or_interaction, 
                        "🔹 Sélectionnez les formes dans le bon ordre !", view=view)

# ────────────────────────────────────────────────────────────────
# 🔹 Bouton mémoire
# ────────────────────────────────────────────────────────────────
class MemoryButton(discord.ui.Button):
    def __init__(self, symbol, color, sequence, user_id):
        super().__init__(label=symbol, style=discord.ButtonStyle.secondary)
        self.symbol = symbol
        self.color = color
        self.sequence = sequence
        self.user_id = user_id
        self.user_sequence = []

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Ce n'est pas votre partie !", ephemeral=True)
            return

        self.user_sequence.append((self.symbol, self.color))
        await interaction.response.defer()

        # Vérifie si l'utilisateur a terminé la série
        if len(self.user_sequence) == len(self.sequence):
            correct = self.user_sequence == self.sequence
            msg = "✅ Correct !" if correct else f"❌ Incorrect ! La bonne série était : {' '.join([s[0] for s in self.sequence])}"
            # Désactive tous les boutons
            for item in self.view.children:
                item.disabled = True
            await interaction.message.edit(content=msg, view=self.view)
            self.view.stop()

# ────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = MemoryFormes(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Jeux"
    await bot.add_cog(cog)
