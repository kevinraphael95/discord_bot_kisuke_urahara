# ────────────────────────────────────────────────────────────────────────────────
# 📌 mastermind.py — Commande interactive !mastermind /mastermind
# Objectif : Jeu de logique Mastermind via boutons Discord avec mode solo/multi
# Catégorie : Jeux
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
import random
from utils.discord_utils import safe_send, safe_edit, safe_respond

# ────────────────────────────────────────────────────────────────────────────────
# 🎨 Liste des couleurs utilisables
# ────────────────────────────────────────────────────────────────────────────────
COLORS = ["🟥", "🟦", "🟩", "🟨", "🟪", "🟧"]

# ────────────────────────────────────────────────────────────────────────────────
# 🟢 Liste des difficultés
# code_length = None → tirage aléatoire au moment du lancement (Cauchemar)
# ────────────────────────────────────────────────────────────────────────────────
DIFFICULTIES = [
    {"label": "Facile",    "code_length": 3,    "corruption": False},
    {"label": "Normal",    "code_length": 4,    "corruption": False},
    {"label": "Difficile", "code_length": 5,    "corruption": False},
    {"label": "Cauchemar", "code_length": None, "corruption": True},
]

# ────────────────────────────────────────────────────────────────────────────────
# 🧩 Vue principale du jeu Mastermind
# ────────────────────────────────────────────────────────────────────────────────
class MastermindView(View):
    def __init__(self, author: discord.User | None, code_length: int, corruption: bool):
        """
        author = None → mode multi (tout le monde peut jouer)
        author = discord.User → mode solo (seul le lanceur peut jouer)
        """
        super().__init__(timeout=180)
        self.author = author
        self.code_length = code_length
        self.corruption = corruption
        self.max_attempts = code_length + 2
        self.code = [random.choice(COLORS) for _ in range(code_length)]
        self.attempts: list[tuple[list[str], list[str]]] = []
        self.current_guess: list[str] = []
        self.message = None
        self.result_shown = False

        for color in COLORS:
            self.add_item(ColorButton(color, self))
        self.add_item(ValidateButton(self))
        self.add_item(ClearButton(self))

    # ── Génération de l'embed ──────────────────────────────────────────────────
    def build_embed(self) -> discord.Embed:
        mode_text = "Multi" if self.author is None else "Solo"
        filled = len(self.current_guess)

        # Barre visuelle de la série en cours : couleurs sélectionnées + cases vides
        serie_bar = "".join(
            self.current_guess[i] if i < filled else "⬛"
            for i in range(self.code_length)
        )

        embed = discord.Embed(
            title=f"🎯 Mastermind — mode {mode_text}",
            description=(
                "🔴 bonne couleur · bonne position\n"
                "⚪ bonne couleur · mauvaise position\n"
                "❌ couleur absente"
                + ("\n💀 indice corrompu *(mode Cauchemar)*" if self.corruption else "")
            ),
            color=discord.Color.blue()
        )
        embed.add_field(
            name=f"🧪 Tentatives ({len(self.attempts)} / {self.max_attempts})",
            value="\n".join(self.format_attempts()) or "Aucune tentative.",
            inline=False
        )
        embed.add_field(
            name=f"🧵 Proposition en cours — {filled} / {self.code_length}",
            value=serie_bar,
            inline=False
        )
        embed.set_footer(text=f"Essais restants : {self.max_attempts - len(self.attempts)}")
        return embed

    # ── Formatage de l'historique ──────────────────────────────────────────────
    def format_attempts(self) -> list[str]:
        return [
            f"{''.join(guess)} → {''.join(feedback)}"
            for guess, feedback in self.attempts
        ]

    # ── Calcul du feedback ─────────────────────────────────────────────────────
    def generate_feedback(self, guess: list[str]) -> list[str]:
        matched_code  = [False] * self.code_length
        matched_guess = [False] * self.code_length
        feedback: list[str | None] = [None] * self.code_length

        # Passe 1 : bonne position
        for i in range(self.code_length):
            if guess[i] == self.code[i]:
                feedback[i]      = "🔴"
                matched_code[i]  = True
                matched_guess[i] = True

        # Passe 2 : bonne couleur, mauvaise position
        for i in range(self.code_length):
            if feedback[i] is not None:
                continue
            for j in range(self.code_length):
                if not matched_code[j] and not matched_guess[i] and guess[i] == self.code[j]:
                    feedback[i]      = "⚪"
                    matched_code[j]  = True
                    matched_guess[i] = True
                    break

        # Passe 3 : absent + corruption éventuelle
        final = [f if f is not None else "❌" for f in feedback]
        if self.corruption:
            final = [f if random.random() > 0.20 else "💀" for f in final]

        return final

    # ── Mise à jour du message ─────────────────────────────────────────────────
    async def update_message(self):
        if self.message and not self.result_shown:
            await safe_edit(self.message, embed=self.build_embed(), view=self)

    # ── Traitement d'une tentative ─────────────────────────────────────────────
    async def make_attempt(self, interaction: discord.Interaction):
        guess    = self.current_guess[:]
        feedback = self.generate_feedback(guess)
        self.attempts.append((guess, feedback))
        self.current_guess.clear()

        if guess == self.code:
            self.result_shown = True
            await self.show_result(interaction, win=True)
            return
        if len(self.attempts) >= self.max_attempts:
            self.result_shown = True
            await self.show_result(interaction, win=False)
            return

        await self.update_message()
        try:
            await interaction.response.defer()
        except discord.InteractionResponded:
            pass

    # ── Affichage du résultat final ────────────────────────────────────────────
    async def show_result(self, interaction: discord.Interaction, win: bool):
        self.stop()
        for item in self.children:
            item.disabled = True

        embed = self.build_embed()
        embed.add_field(
            name="🏁 Résultat",
            value=(
                f"**{'Gagné ! 🎉' if win else 'Perdu ! 💀'}**\n"
                f"La combinaison était : {' '.join(self.code)}"
            ),
            inline=False
        )
        embed.color = discord.Color.green() if win else discord.Color.red()

        try:
            await interaction.response.edit_message(embed=embed, view=self)
        except discord.InteractionResponded:
            await interaction.edit_original_response(embed=embed, view=self)

# ────────────────────────────────────────────────────────────────────────────────
# 🔵 Boutons interactifs
# ────────────────────────────────────────────────────────────────────────────────
class ColorButton(Button):
    def __init__(self, color: str, view_ref: MastermindView):
        super().__init__(style=discord.ButtonStyle.secondary, emoji=color)
        self.color    = color
        self.view_ref = view_ref

    async def callback(self, interaction: discord.Interaction):
        v = self.view_ref
        if v.author and interaction.user != v.author:
            return await safe_respond(interaction, "⛔ Ce jeu ne t'appartient pas.", ephemeral=True)
        if len(v.current_guess) >= v.code_length:
            return await safe_respond(interaction, "❗ Série déjà complète.", ephemeral=True)
        v.current_guess.append(self.color)
        await v.update_message()
        try:
            await interaction.response.defer()
        except discord.InteractionResponded:
            pass


class ClearButton(Button):
    def __init__(self, view_ref: MastermindView):
        super().__init__(emoji="🗑️", style=discord.ButtonStyle.danger, label="Effacer")
        self.view_ref = view_ref

    async def callback(self, interaction: discord.Interaction):
        v = self.view_ref
        if v.author and interaction.user != v.author:
            return await safe_respond(interaction, "⛔ Ce jeu ne t'appartient pas.", ephemeral=True)
        v.current_guess.clear()
        await v.update_message()
        try:
            await interaction.response.defer()
        except discord.InteractionResponded:
            pass


class ValidateButton(Button):
    def __init__(self, view_ref: MastermindView):
        super().__init__(emoji="✅", style=discord.ButtonStyle.success, label="Valider")
        self.view_ref = view_ref

    async def callback(self, interaction: discord.Interaction):
        v = self.view_ref
        if v.author and interaction.user != v.author:
            return await safe_respond(interaction, "⛔ Ce jeu ne t'appartient pas.", ephemeral=True)
        if len(v.current_guess) != v.code_length:
            return await safe_respond(
                interaction,
                f"⚠️ Série incomplète ({len(v.current_guess)} / {v.code_length}).",
                ephemeral=True
            )
        await v.make_attempt(interaction)

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ Menu de sélection de difficulté
# ────────────────────────────────────────────────────────────────────────────────
class DifficultyView(View):
    def __init__(self, author: discord.User | None, mode: str = "solo"):
        """
        author = utilisateur qui lance le jeu
        mode   = "solo" ou "multi"
        """
        super().__init__(timeout=60)
        effective_author = author if mode.lower() == "solo" else None
        for diff in DIFFICULTIES:
            self.add_item(DifficultyButton(
                label       = diff["label"],
                code_length = diff["code_length"],
                corruption  = diff["corruption"],
                author      = effective_author,
            ))


class DifficultyButton(Button):
    def __init__(self, label: str, code_length: int | None, corruption: bool, author):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self._code_length = code_length   # None = aléatoire à chaque partie (Cauchemar)
        self.corruption   = corruption
        self.author       = author

    async def callback(self, interaction: discord.Interaction):
        # Résolution de la longueur : Cauchemar tire un nouveau nombre à chaque partie
        code_length = self._code_length if self._code_length is not None else random.randint(8, 10)

        view = MastermindView(self.author, code_length, self.corruption)
        embed = view.build_embed()
        await interaction.response.edit_message(embed=embed, view=view)
        view.message = interaction.message

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class Mastermind(commands.Cog):
    """Mastermind interactif avec commandes prefix et slash."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="mastermind", aliases=["mm"], help="Jouer au Mastermind interactif.")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def prefix_mastermind(self, ctx: commands.Context, mode: str = "solo"):
        """
        mode = "solo"  → seul le lanceur peut jouer
        mode = "multi" → tout le monde peut jouer
        """
        mode_label = "Multi" if mode.lower() != "solo" else "Solo"
        view  = DifficultyView(ctx.author, mode)
        embed = discord.Embed(
            title=f"🎮 Choisis la difficulté — mode {mode_label}",
            description="Clique sur un bouton ci-dessous :",
            color=discord.Color.orange()
        )
        await safe_send(ctx.channel, embed=embed, view=view)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(name="mastermind", description="Jouer au Mastermind interactif.")
    @app_commands.describe(mode="Mode de jeu : solo ou multi")
    @app_commands.checks.cooldown(1, 10.0, key=lambda i: i.user.id)
    async def slash_mastermind(self, interaction: discord.Interaction, mode: str = "solo"):
        mode_label = "Multi" if mode.lower() != "solo" else "Solo"
        view  = DifficultyView(interaction.user, mode)
        embed = discord.Embed(
            title=f"🎮 Choisis la difficulté — mode {mode_label}",
            description="Clique sur un bouton ci-dessous :",
            color=discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed, view=view)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Mastermind(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Jeux"
    await bot.add_cog(cog)
