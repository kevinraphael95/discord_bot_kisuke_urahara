# ================================================================================
# 📌 memory_formes.py — Commande Memory : retenir et choisir les formes
# Objectif : Jouer à un mini jeu mémoire avec une gridview de boutons
# Catégorie : Jeux
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ================================================================================

# ================================================================================
# 📦 Imports nécessaires
# ================================================================================
import discord
from discord import app_commands
from discord.ext import commands
import random
import asyncio

from utils.discord_utils import safe_send, safe_edit

# ================================================================================
# 🧠 Cog principal
# ================================================================================
class MemoryFormes(commands.Cog):
    """
    Commande /formes et !formes — Jouez au mini-jeu mémoire
    """
    FORMS = ["❤️", "💙", "🤍", "🟥", "🟦", "⬜", "🔴", "🔵", "⚪"]

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ============================================================================
    # 🔹 Commande SLASH
    # ============================================================================
    @app_commands.command(
        name="formes",
        description="Jouez au mini-jeu mémoire avec des formes et couleurs."
    )
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_memory_formes(self, interaction: discord.Interaction):
        await self.start_game(interaction)

    # ============================================================================
    # 🔹 Commande PREFIX
    # ============================================================================
    @commands.command(name="formes", help="Jouez au mini-jeu mémoire avec des formes et couleurs.")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_memory_formes(self, ctx: commands.Context):
        await self.start_game(ctx)

    # ============================================================================
    # 🔹 Fonction principale du jeu
    # ============================================================================
    async def start_game(self, ctx_or_interaction):
        is_interaction = isinstance(ctx_or_interaction, discord.Interaction)
        user    = ctx_or_interaction.user if is_interaction else ctx_or_interaction.author
        channel = ctx_or_interaction.channel
    
        sequence = random.sample(self.FORMS, random.randint(4, 6))
        sequence_str = " ".join(sequence)
    
        embed = discord.Embed(
            title="🧠 Test de mémoire",
            description=f"Retenez bien cette suite !\n\n# {sequence_str}\n\nDisparition dans **5**s...",
            color=discord.Color.blurple()
        )
        embed.set_footer(text=f"Joueur : {user.display_name}")
    
        if is_interaction:
            await ctx_or_interaction.response.send_message(embed=embed)
            msg = await ctx_or_interaction.original_response()
        else:
            msg = await channel.send(embed=embed)
    
        for i in range(4, 0, -1):
            await asyncio.sleep(1)
            embed.description = f"Retenez bien cette suite !\n\n# {sequence_str}\n\nDisparition dans **{i}**s..."
            try:
                await safe_edit(msg, embed=embed)
            except discord.NotFound:
                return
    
        await asyncio.sleep(1)
    
        # 👇 Passe TOUTES les formes à la View
        view       = MemoryView(sequence, self.FORMS, user.id)
        game_embed = view.build_embed()
    
        try:
            await safe_edit(msg, embed=game_embed, view=view)
            view.game_message = msg
        except discord.NotFound:
            msg = await safe_send(channel, embed=game_embed, view=view)
            view.game_message = msg


# ================================================================
# 🔹 View personnalisée
# ================================================================
class MemoryView(discord.ui.View):
    def __init__(self, sequence, all_forms, user_id):
        super().__init__(timeout=45)
        self.sequence      = sequence
        self.user_id       = user_id
        self.user_sequence = []
        self.game_message: discord.Message | None = None

        # 👇 Boutons = TOUTES les formes, mélangées
        shuffled = random.sample(all_forms, len(all_forms))
        for symbol in shuffled:
            self.add_item(MemoryButton(symbol))

        self.add_item(DeleteLastButton())

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Ce n'est pas votre partie !", ephemeral=True)
            return False
        return True

    def build_embed(self) -> discord.Embed:
        """Construit l'embed principal du jeu avec la progression."""
        progress_bar = self._build_progress_bar()

        embed = discord.Embed(
            title="🧠 Reproduisez la suite !",
            description=(
                f"Clique sur les formes **dans le bon ordre**.\n\n"
                f"**Progression :**\n{progress_bar}\n\n"
                f"**{len(self.user_sequence)} / {len(self.sequence)}**"
            ),
            color=discord.Color.orange()
        )
        return embed

    def _build_progress_bar(self) -> str:
        """Construit la barre de progression avec les formes choisies + les cases vides."""
        filled = [s for s in self.user_sequence]
        empty  = ["⬛"] * (len(self.sequence) - len(filled))
        return " ".join(filled + empty)

    async def refresh(self, interaction: discord.Interaction):
        """Met à jour l'embed + désactive les boutons si terminé."""
        finished = len(self.user_sequence) >= len(self.sequence)

        if finished:
            for item in self.children:
                item.disabled = True

            correct = self.user_sequence == self.sequence
            given   = " ".join(self.user_sequence)
            good    = " ".join(self.sequence)

            if correct:
                embed = discord.Embed(
                    title="✅ Bravo !",
                    description=f"Tu as reproduit la bonne suite !\n\n**Suite :** {good}",
                    color=discord.Color.green()
                )
            else:
                embed = discord.Embed(
                    title="❌ Raté !",
                    description=(
                        f"**Ta réponse :** {given}\n"
                        f"**Bonne suite :** {good}"
                    ),
                    color=discord.Color.red()
                )
            embed.set_footer(text=f"Joueur : {interaction.user.display_name}")
            self.stop()
        else:
            embed = self.build_embed()

        try:
            await safe_edit(interaction.message, embed=embed, view=self)
        except discord.NotFound:
            pass

    async def on_timeout(self):
        """Désactive les boutons si le temps est écoulé."""
        if self.game_message:
            for item in self.children:
                item.disabled = True
            good = " ".join(self.sequence)
            embed = discord.Embed(
                title="⏰ Temps écoulé !",
                description=f"**La bonne suite était :** {good}",
                color=discord.Color.dark_gray()
            )
            try:
                await safe_edit(self.game_message, embed=embed, view=self)
            except discord.NotFound:
                pass


# ================================================================
# 🔹 Bouton mémoire — ajouter une forme
# ================================================================
class MemoryButton(discord.ui.Button):
    def __init__(self, symbol: str):
        super().__init__(label=symbol, style=discord.ButtonStyle.secondary)
        self.symbol = symbol

    async def callback(self, interaction: discord.Interaction):
        view: MemoryView = self.view

        if len(view.user_sequence) >= len(view.sequence):
            return

        view.user_sequence.append(self.symbol)

        await interaction.response.defer()
        await view.refresh(interaction)


# ================================================================
# 🔹 Bouton supprimer la dernière forme
# ================================================================
class DeleteLastButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="⬅️ Supprimer", style=discord.ButtonStyle.danger)

    async def callback(self, interaction: discord.Interaction):
        view: MemoryView = self.view

        if view.user_sequence:
            view.user_sequence.pop()

        await interaction.response.defer()
        await view.refresh(interaction)


# ================================================================
# 🔌 Setup du Cog
# ================================================================
async def setup(bot: commands.Bot):
    cog = MemoryFormes(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Jeux"
    await bot.add_cog(cog)
