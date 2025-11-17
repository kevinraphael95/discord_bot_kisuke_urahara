# ────────────────────────────────────────────────────────────────────────────────
# 📌 devinelenombre.py — Commande interactive /devinelenombre et !devinelenombre
# Objectif : Deviner un nombre entre 0 et 100
# Modes : Solo (1 joueur) et Multi (plusieurs joueurs)
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
# 🎛️ Vue principale
# ────────────────────────────────────────────────────────────────────────────────
class DevinelenombreView:
    SOLO_TIME = 120
    MULTI_TIME = 120

    def __init__(self, target: int, multi: bool = False, author_id: int | None = None, channel: discord.TextChannel | None = None):
        self.target = target
        self.multi = multi
        self.author_id = author_id
        self.channel = channel
        self.attempts: list[dict] = []
        self.message: discord.Message | None = None
        self.finished = False
        self.start_time = asyncio.get_event_loop().time()

    def build_embed(self) -> discord.Embed:
        mode_text = "Multi 🌍" if self.multi else "Solo 🧍‍♂️"
        embed = discord.Embed(
            title=f"🎯 Devinelenombre - {mode_text}",
            description="Devine le nombre entre 0 et 100\nPropose ton nombre avec `/devinelenombre <nombre>` ou `!devinelenombre <nombre>`",
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
                embed.set_footer(text=f"🎉 Bravo ! {self.attempts[-1]['user']} a trouvé le nombre {self.target}.")
            else:
                embed.color = discord.Color.red()
                embed.set_footer(text=f"💀 Partie terminée. Le nombre était {self.target}.")
        else:
            elapsed = int(asyncio.get_event_loop().time() - self.start_time)
            remaining = max(0, (self.MULTI_TIME if self.multi else self.SOLO_TIME) - elapsed)
            embed.set_footer(text=f"⏳ Temps restant : {remaining} secondes")

        return embed

    async def process_guess(self, user: discord.User, guess: int):
        if self.finished:
            return False, "⚠️ La partie est terminée."
        if not (0 <= guess <= 100):
            return False, "⚠️ Le nombre doit être entre 0 et 100."
        if not self.multi and self.author_id and user.id != self.author_id:
            return False, "❌ Seul le lanceur peut proposer un nombre en solo."

        self.attempts.append({"guess": guess, "user": user.display_name})
        if self.message:
            await safe_edit(self.message, embed=self.build_embed())

        if guess == self.target:
            self.finished = True
            return True, f"🎉 Bravo ! {user.mention} a trouvé le nombre **{self.target}** !"

        return True, f"{user.display_name} a proposé **{guess}**. Écart : {abs(self.target - guess)}"

    async def start_timer(self):
        await asyncio.sleep(self.MULTI_TIME if self.multi else self.SOLO_TIME)
        if not self.finished:
            self.finished = True
            embed = self.build_embed()
            embed.color = discord.Color.red()
            embed.set_footer(text=f"⏳ Temps écoulé ! Le nombre était {self.target}.")
            if self.message:
                await safe_edit(self.message, embed=embed)

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class Devinelenombre(commands.Cog):
    """Commande /devinelenombre et !devinelenombre — Deviner un nombre entre 0 et 100"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active_games: dict[int, DevinelenombreView] = {}

    async def _start_game(self, channel: discord.TextChannel, user_id: int, multi: bool = False):
        if channel.id in self.active_games:
            return
        target = random.randint(0, 100)
        author_filter = None if multi else user_id
        view = DevinelenombreView(target, multi=multi, author_id=author_filter, channel=channel)
        view.message = await safe_send(channel, embed=view.build_embed())
        self.active_games[channel.id] = view
        asyncio.create_task(view.start_timer())

    async def guess_number(self, ctx_or_interaction, guess: int):
        channel_id = ctx_or_interaction.channel.id
        if channel_id not in self.active_games:
            return await safe_respond(ctx_or_interaction, "⚠️ Aucune partie en cours dans ce salon.", ephemeral=True)
        view = self.active_games[channel_id]
        user = ctx_or_interaction.user if hasattr(ctx_or_interaction, "user") else ctx_or_interaction.author
        ok, msg = await view.process_guess(user, guess)
        if isinstance(ctx_or_interaction, commands.Context):
            try: await ctx_or_interaction.message.delete()
            except: pass
        return await safe_respond(ctx_or_interaction, msg, ephemeral=not view.finished)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(name="devinelenombre", description="Devine un nombre entre 0 et 100")
    @app_commands.describe(nombre="Le nombre à proposer (0-100)", mode="Tapez 'm' ou 'multi' pour le mode multijoueur")
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_devinelenombre(self, interaction: discord.Interaction, nombre: int, mode: str = None):
        multi = bool(mode and mode.lower() in ("m", "multi"))
        if interaction.channel.id not in self.active_games:
            await self._start_game(interaction.channel, user_id=interaction.user.id, multi=multi)
        await self.guess_number(interaction, nombre)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="devinelenombre", aliases=["dln"], help="Devine un nombre entre 0 et 100 (multi = plusieurs joueurs)")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_devinelenombre(self, ctx: commands.Context, nombre: int, mode: str = None):
        multi = bool(mode and mode.lower() in ("m", "multi"))
        if ctx.channel.id not in self.active_games:
            await self._start_game(ctx.channel, user_id=ctx.author.id, multi=multi)
        await self.guess_number(ctx, nombre)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Devinelenombre(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Jeux"
    await bot.add_cog(cog)
