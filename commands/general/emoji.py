# ────────────────────────────────────────────────────────────────────────────────
# 📌 emoji_command.py — Commande interactive !emoji / !e et /emoji
# Objectif : Afficher un ou plusieurs emojis du serveur via une commande
# Catégorie : 🎉 Fun
# Accès : Public
# Cooldown : Paramétrable par commande
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button
import random
import re
from utils.discord_utils import safe_send, safe_respond  

# ────────────────────────────────────────────────────────────────────────────────
# 🎮 View pour la pagination
# ────────────────────────────────────────────────────────────────────────────────
class EmojiPaginator(View):
    def __init__(self, pages: list[discord.Embed], timeout: int = 90):
        super().__init__(timeout=timeout)
        self.pages = pages
        self.index = 0

    async def update(self, interaction: discord.Interaction):
        await interaction.response.edit_message(embed=self.pages[self.index], view=self)

    @discord.ui.button(label="⬅️", style=discord.ButtonStyle.secondary)
    async def previous(self, interaction: discord.Interaction, button: Button):
        self.index = (self.index - 1) % len(self.pages)
        await self.update(interaction)

    @discord.ui.button(label="➡️", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, button: Button):
        self.index = (self.index + 1) % len(self.pages)
        await self.update(interaction)

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal avec centralisation erreurs et cooldowns
# ────────────────────────────────────────────────────────────────────────────────
class EmojiCommand(commands.Cog):
    """Commande !emoji / !e et /emoji — Affiche un ou plusieurs emojis du serveur."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonctions internes
    # ────────────────────────────────────────────────────────────────────────────
    def _parse_emoji_input(self, raw_input: tuple[str]) -> list[str]:
        joined = "".join(raw_input)
        return re.findall(r":([a-zA-Z0-9_]+):", joined)

    def _find_emojis(self, emoji_inputs: list[str], current_guild: discord.Guild):
        found, not_found = [], []
        for name in emoji_inputs:
            name_lower = name.lower()
            match = discord.utils.find(lambda e: e.name.lower() == name_lower and e.available, current_guild.emojis)
            if not match:
                other_guilds = [g for g in self.bot.guilds if g.id != current_guild.id]
                for g in random.sample(other_guilds, len(other_guilds)):
                    match = discord.utils.find(lambda e: e.name.lower() == name_lower and e.available, g.emojis)
                    if match:
                        break
            if match:
                found.append(str(match))
            else:
                not_found.append(f":{name}:")
        return found, not_found

    def _build_pages(self, guilds: list[discord.Guild]) -> list[discord.Embed]:
        pages = []
        for g in guilds:
            animated = [str(e) for e in g.emojis if e.animated and e.available]
            if not animated:
                continue
            chunks = [animated[i:i+40] for i in range(0, len(animated), 40)]
            for i, chunk in enumerate(chunks, start=1):
                embed = discord.Embed(
                    title=f"🎭 Emojis animés — {g.name}",
                    description=" ".join(chunk),
                    color=discord.Color.orange()
                )
                if len(chunks) > 1:
                    embed.set_footer(text=f"Page {i}/{len(chunks)} pour {g.name}")
                pages.append(embed)
        return pages

    async def _send_emojis_safe(self, channel: discord.abc.Messageable, guild: discord.Guild, emoji_names: tuple[str]):
        """Envoie les emojis de manière centralisée."""
        if emoji_names:
            emoji_inputs = self._parse_emoji_input(emoji_names)
            found, not_found = self._find_emojis(emoji_inputs, guild)
            if found:
                await safe_send(channel, " ".join(found))
            if not_found:
                await safe_send(channel, f"❌ Emojis introuvables : {', '.join(not_found)}")
        else:
            guilds = [guild] + [g for g in self.bot.guilds if g.id != guild.id]
            pages = self._build_pages(guilds)
            if not pages:
                await safe_send(channel, "❌ Aucun emoji animé trouvé sur les serveurs.")
                return
            view = EmojiPaginator(pages)
            await safe_send(channel, embed=pages[0], view=view)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(
        name="emoji",
        aliases=["e"],
        help="😄 Affiche un ou plusieurs emojis du serveur."
    )
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def prefix_emoji(self, ctx: commands.Context, *emoji_names):
        if ctx.message:
            try:
                await ctx.message.delete()
            except (discord.Forbidden, discord.HTTPException):
                pass
        await self._send_emojis_safe(ctx.channel, ctx.guild, emoji_names)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="emoji",
        description="Affiche un ou plusieurs emojis du serveur ou tous les animés des serveurs."
    )
    @app_commands.describe(emojis="Noms des emojis à afficher, séparés par des espaces ou répétés (ex: :woah::woah:)")
    @app_commands.checks.cooldown(1, 3.0, key=lambda i: i.user.id)
    async def slash_emoji(self, interaction: discord.Interaction, *, emojis: str = ""):
        await interaction.response.defer()
        emoji_inputs = self._parse_emoji_input((emojis,))
        await self._send_emojis_safe(interaction.channel, interaction.guild, emoji_inputs)
        try:
            await interaction.delete_original_response()
        except Exception:
            pass

    @slash_emoji.autocomplete("emojis")
    async def autocomplete_emojis(self, interaction: discord.Interaction, current: str):
        suggestions = [e.name for e in interaction.guild.emojis if e.available]
        return [app_commands.Choice(name=s, value=s) for s in suggestions if current.lower() in s.lower()][:25]

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = EmojiCommand(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Fun"
    await bot.add_cog(cog)
