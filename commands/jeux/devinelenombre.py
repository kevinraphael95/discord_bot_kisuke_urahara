# ────────────────────────────────────────────────────────────────────────────────
# 📌 devinelenombre.py — Commande interactive /devinelenombre et !devinelenombre
# Objectif : Deviner un nombre entre 0 et 100 avec embed interactif, mode solo/multi et timer
# Catégorie : Jeux
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord, random, asyncio
from discord import app_commands
from discord.ext import commands
from utils.discord_utils import safe_send, safe_edit, safe_respond

# ────────────────────────────────────────────────────────────────────────────────
# 🎮 Classe principale du jeu
# ────────────────────────────────────────────────────────────────────────────────
class DevinelenombreView:
    """Classe représentant une partie de Devinelenombre"""

    SOLO_TIME = 120
    MULTI_TIME = 120

    def __init__(self, author_id: int | None = None, multi: bool = False):
        self.author_id = author_id
        self.multi = multi
        self.target = random.randint(0, 100)
        self.finished = False
        self.start_time = asyncio.get_event_loop().time()
        self.message: discord.Message | None = None
        self.attempts: list[dict] = []

    def build_embed(self) -> discord.Embed:
        mode_text = "Solo 🧍‍♂️" if not self.multi else "Multi 🌍"
        embed = discord.Embed(
            title=f"🎯 Devinelenombre - {mode_text}",
            description="💡 **Instructions :** Devine le nombre entre 0 et 100\nFais ton essai avec `.` ou `*` suivi de ton nombre",
            color=discord.Color.orange()
        )
        if self.attempts:
            lines = []
            for idx, entry in enumerate(self.attempts, 1):
                val, user = entry["guess"], entry["user"]
                if val < self.target:
                    symbol = "⬆️ Trop bas"
                elif val > self.target:
                    symbol = "⬇️ Trop haut"
                else:
                    symbol = "✅ Exact !"
                lines.append(f"{idx}. {val} → {symbol} ({user})")
            embed.add_field(name=f"Essais ({len(self.attempts)})", value="\n".join(lines), inline=False)
        else:
            embed.add_field(name="Essais", value="*(Aucun essai pour l’instant)*", inline=False)

        if self.finished:
            last_guess = self.attempts[-1]["guess"] if self.attempts else None
            if last_guess == self.target:
                embed.color = discord.Color.green()
                embed.set_footer(text=f"🎉 Partie terminée ! {self.attempts[-1]['user']} a trouvé {self.target}.")
            else:
                embed.color = discord.Color.red()
                embed.set_footer(text=f"💀 Partie terminée. Le nombre était {self.target}.")
        else:
            elapsed = int(asyncio.get_event_loop().time() - self.start_time)
            remaining = max(0, (self.MULTI_TIME if self.multi else self.SOLO_TIME) - elapsed)
            embed.set_footer(text=f"⏳ Temps restant : {remaining} secondes")
        return embed

    async def process_guess(self, channel: discord.abc.Messageable, guess: int, author_name: str, author_id: int):
        if self.finished:
            return await safe_send(channel, "⚠️ La partie est terminée.")
        if not (0 <= guess <= 100):
            return await safe_send(channel, "⚠️ Le nombre doit être entre 0 et 100.")
        if not self.multi and self.author_id and author_id != self.author_id:
            return
        self.attempts.append({"guess": guess, "user": author_name})
        if self.message:
            await safe_edit(self.message, embed=self.build_embed())
        if guess == self.target:
            self.finished = True

    async def check_timeout(self):
        while not self.finished:
            await asyncio.sleep(5)
            elapsed = asyncio.get_event_loop().time() - self.start_time
            if elapsed >= (self.MULTI_TIME if self.multi else self.SOLO_TIME):
                self.finished = True
                if self.message:
                    await safe_edit(self.message, embed=self.build_embed())
                break

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class Devinelenombre(commands.Cog):
    """Commande /devinelenombre et !devinelenombre — Deviner un nombre entre 0 et 100"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active_games: dict[int, DevinelenombreView] = {}  # guild_id -> vue active

    async def _start_game(self, channel: discord.abc.Messageable, author_id: int, guild_id: int, mode: str = "solo"):
        if guild_id in self.active_games and not self.active_games[guild_id].finished:
            return await safe_respond(channel, "⚠️ Une partie est déjà en cours sur ce serveur !", ephemeral=True)
        multi = mode.lower() in ("multi", "m")
        view = DevinelenombreView(author_id=None if multi else author_id, multi=multi)
        view.message = await safe_send(channel, embed=view.build_embed())
        self.active_games[guild_id] = view
        asyncio.create_task(view.check_timeout())

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        guild_id = message.guild.id if message.guild else None
        if guild_id not in self.active_games:
            return
        content = message.content.strip()
        if content.startswith((".", "*")):
            view = self.active_games[guild_id]
            try:
                guess = int(content[1:].strip())
            except:
                return
            await view.process_guess(message.channel, guess, message.author.display_name, message.author.id)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(name="devinelenombre", description="Devine un nombre entre 0 et 100 (solo ou multi)")
    @app_commands.describe(nombre="Le nombre à proposer (0-100)", mode="Mode solo ou multi (m)")
    async def slash_devinelenombre(self, interaction: discord.Interaction, nombre: int, mode: str = "solo"):
        await interaction.response.defer()
        if interaction.guild.id not in self.active_games:
            await self._start_game(interaction.channel, author_id=interaction.user.id, guild_id=interaction.guild.id, mode=mode)
        view = self.active_games[interaction.guild.id]
        await view.process_guess(interaction.channel, nombre, interaction.user.display_name, interaction.user.id)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="devinelenombre", aliases=["dln"], help="Devine un nombre entre 0 et 100. Utilisez 'multi' ou 'm' pour jouer à plusieurs.")
    async def prefix_devinelenombre(self, ctx: commands.Context, nombre: int, mode: str = "solo"):
        if ctx.guild.id not in self.active_games:
            await self._start_game(ctx.channel, author_id=ctx.author.id, guild_id=ctx.guild.id, mode=mode)
        view = self.active_games[ctx.guild.id]
        await view.process_guess(ctx.channel, nombre, ctx.author.display_name, ctx.author.id)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Devinelenombre(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Jeux"
    await bot.add_cog(cog)
