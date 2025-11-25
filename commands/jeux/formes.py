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
        user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
        channel = ctx_or_interaction.channel if hasattr(ctx_or_interaction, "channel") else ctx_or_interaction

        user_id = user.id

        # Choix aléatoire de 4 à 6 formes
        sequence = random.sample(self.FORMS, random.randint(4, 6))
        sequence_str = " ".join([f"{s[0]}" for s in sequence])

        # Message d’apprentissage
        msg = await safe_send(channel, f"🔹 Retenez cette série et rien d'autre :\n{sequence_str}")

        # Attente 5 secondes
        await discord.utils.sleep_until(discord.utils.utcnow() + discord.utils.timedelta(seconds=5))

        # Suppression du message
        try:
            await msg.delete()
        except:
            pass

        # ── Création de la gridView
        view = MemoryView(self.FORMS, sequence, user_id)

        # Message final
        await safe_send(channel, "🔹 Sélectionnez les formes dans le bon ordre !", view=view)


# ────────────────────────────────────────────────────────────────
# 🔹 View personnalisée avec bouton “supprimer”
# ────────────────────────────────────────────────────────────────
class MemoryView(discord.ui.View):
    def __init__(self, forms, sequence, user_id):
        super().__init__(timeout=30)
        self.sequence = sequence
        self.user_id = user_id
        self.user_sequence = []

        # Mélange des formes
        shuffled = random.sample(forms, len(forms))

        # Ajout des boutons des formes
        for symbol, color in shuffled:
            self.add_item(MemoryButton(symbol, color))

        # Ajout du bouton supprimer
        self.add_item(DeleteLastButton())

    async def update_state(self, interaction: discord.Interaction):
        # Vérification de longueur
        if len(self.user_sequence) == len(self.sequence):

            correct = self.user_sequence == self.sequence
            good = " ".join([s[0] for s in self.sequence])

            msg = (
                f"✅ Correct ! La série était : {good}"
                if correct else
                f"❌ Incorrect ! La bonne série était : {good}"
            )

            # Désactiver tous les boutons
            for item in self.children:
                item.disabled = True

            await interaction.message.edit(content=msg, view=self)
            self.stop()


# ────────────────────────────────────────────────────────────────
# 🔹 Bouton mémoire — ajouter une forme
# ────────────────────────────────────────────────────────────────
class MemoryButton(discord.ui.Button):
    def __init__(self, symbol, color):
        super().__init__(label=symbol, style=discord.ButtonStyle.secondary)
        self.symbol = symbol
        self.color = color

    async def callback(self, interaction: discord.Interaction):
        view: MemoryView = self.view

        if interaction.user.id != view.user_id:
            return await interaction.response.send_message("❌ Ce n'est pas votre partie !", ephemeral=True)

        view.user_sequence.append((self.symbol, self.color))
        await interaction.response.defer()

        await view.update_state(interaction)


# ────────────────────────────────────────────────────────────────
# 🔹 Bouton supprimer la dernière forme
# ────────────────────────────────────────────────────────────────
class DeleteLastButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="⬅️ Supprimer", style=discord.ButtonStyle.danger)

    async def callback(self, interaction: discord.Interaction):
        view: MemoryView = self.view

        if interaction.user.id != view.user_id:
            return await interaction.response.send_message("❌ Ce n'est pas votre partie !", ephemeral=True)

        if view.user_sequence:
            view.user_sequence.pop()

        await interaction.response.defer()


# ────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = MemoryFormes(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Jeux"
    await bot.add_cog(cog)
