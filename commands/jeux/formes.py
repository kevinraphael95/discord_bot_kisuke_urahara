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
import asyncio
from utils.discord_utils import safe_send

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class MemoryFormes(commands.Cog):
    """
    Commande /formes et !formes — Jouez au mini-jeu mémoire
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
        is_interaction = isinstance(ctx_or_interaction, discord.Interaction)
        user = ctx_or_interaction.user if is_interaction else ctx_or_interaction.author
        channel = ctx_or_interaction.channel

        # Choix aléatoire de 4 à 6 formes
        sequence = random.sample(self.FORMS, random.randint(4, 6))

        # ── Embed d'intro
        embed = discord.Embed(
            title="🧠 Memory — Jeu de mémoire",
            description="Retenez bien la suite de formes qui va s'afficher !\nChaque symbole apparaît pendant **3 secondes**.",
            color=discord.Color.orange()
        )
        embed.set_footer(text=f"Partie de {user.display_name} • {len(sequence)} formes à retenir")

        if is_interaction:
            await ctx_or_interaction.response.send_message(embed=embed)
            msg = await ctx_or_interaction.original_response()
        else:
            msg = await channel.send(embed=embed)

        await asyncio.sleep(2)

        # ── Affichage symbole par symbole (3s chacun)
        revealed = []
        for i, (symbol, color) in enumerate(sequence):
            revealed.append(symbol)

            embed_reveal = discord.Embed(
                title=f"👁️ Symbole {i + 1}/{len(sequence)}",
                description=f"## {symbol}",
                color=discord.Color.blurple()
            )
            embed_reveal.add_field(
                name="Séquence vue jusqu'ici",
                value=" ".join(revealed) if revealed else "—",
                inline=False
            )
            embed_reveal.set_footer(text=f"Partie de {user.display_name} • Prochain dans 3s...")

            try:
                await msg.edit(embed=embed_reveal, content=None)
            except discord.NotFound:
                return

            await asyncio.sleep(3)

        # ── Embed transition vers le jeu
        progress_bar = "⬛" * len(sequence)
        embed_game = discord.Embed(
            title="🎮 À vous de jouer !",
            description=(
                "Reproduisez la suite dans le bon ordre en cliquant sur les boutons.\n\n"
                f"**Progression :** {progress_bar} (0/{len(sequence)})"
            ),
            color=discord.Color.green()
        )
        embed_game.set_footer(text=f"Partie de {user.display_name} • ⏰ 45s pour répondre")

        view = MemoryView(self.FORMS, sequence, user.id)

        try:
            await msg.edit(embed=embed_game, view=view, content=None)
            view.game_message = msg
        except discord.NotFound:
            msg = await channel.send(embed=embed_game, view=view)
            view.game_message = msg


# ────────────────────────────────────────────────────────────────
# 🔹 View personnalisée
# ────────────────────────────────────────────────────────────────
class MemoryView(discord.ui.View):
    def __init__(self, forms, sequence, user_id):
        super().__init__(timeout=45)
        self.sequence = sequence
        self.user_id = user_id
        self.user_sequence = []
        self.game_message: discord.Message | None = None

        # Mélange des formes pour les boutons
        shuffled = random.sample(forms, len(forms))
        for symbol, color in shuffled:
            self.add_item(MemoryButton(symbol, color))

        self.add_item(DeleteLastButton())

    def build_progress(self) -> str:
        """Construit l'affichage de progression avec les formes choisies."""
        filled = [s[0] for s in self.user_sequence]
        empty = ["⬛"] * (len(self.sequence) - len(filled))
        bar = " ".join(filled + empty)
        return f"**Progression :** {bar} ({len(self.user_sequence)}/{len(self.sequence)})"

    async def refresh_message(self, interaction: discord.Interaction):
        """Met à jour l'embed avec la progression actuelle."""
        embed = discord.Embed(
            title="🎮 À vous de jouer !",
            description=(
                "Reproduisez la suite dans le bon ordre en cliquant sur les boutons.\n\n"
                + self.build_progress()
            ),
            color=discord.Color.green()
        )
        embed.set_footer(text="⏰ 45s pour répondre")
        await interaction.message.edit(embed=embed, view=self)

    async def check_win(self, interaction: discord.Interaction):
        """Vérifie si la séquence est complète et détermine victoire/défaite."""
        if len(self.user_sequence) < len(self.sequence):
            return

        correct = self.user_sequence == self.sequence
        good = " ".join([s[0] for s in self.sequence])
        given = " ".join([s[0] for s in self.user_sequence])

        if correct:
            embed = discord.Embed(
                title="✅ Bravo !",
                description=f"Vous avez reproduit la bonne suite !\n\n**Suite :** {good}",
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="❌ Raté !",
                description=(
                    f"Ce n'était pas la bonne suite.\n\n"
                    f"**Votre réponse :** {given}\n"
                    f"**Bonne suite :** {good}"
                ),
                color=discord.Color.red()
            )

        for item in self.children:
            item.disabled = True

        await interaction.message.edit(embed=embed, view=self)
        self.stop()

    async def on_timeout(self):
        """Désactive les boutons si le temps est écoulé."""
        if self.game_message:
            for item in self.children:
                item.disabled = True
            good = " ".join([s[0] for s in self.sequence])
            embed = discord.Embed(
                title="⏰ Temps écoulé !",
                description=f"**La bonne suite était :** {good}",
                color=discord.Color.red()
            )
            try:
                await self.game_message.edit(embed=embed, view=self)
            except discord.NotFound:
                pass


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

        if len(view.user_sequence) >= len(view.sequence):
            return await interaction.response.send_message("⚠️ Vous avez déjà rempli toute la suite !", ephemeral=True)

        view.user_sequence.append((self.symbol, self.color))

        await interaction.response.defer()
        await view.refresh_message(interaction)
        await view.check_win(interaction)


# ────────────────────────────────────────────────────────────────
# 🔹 Bouton supprimer la dernière forme
# ────────────────────────────────────────────────────────────────
class DeleteLastButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="⬅️ Supprimer", style=discord.ButtonStyle.danger, row=4)

    async def callback(self, interaction: discord.Interaction):
        view: MemoryView = self.view

        if interaction.user.id != view.user_id:
            return await interaction.response.send_message("❌ Ce n'est pas votre partie !", ephemeral=True)

        if view.user_sequence:
            view.user_sequence.pop()

        await interaction.response.defer()
        await view.refresh_message(interaction)


# ────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = MemoryFormes(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Jeux"
    await bot.add_cog(cog)
