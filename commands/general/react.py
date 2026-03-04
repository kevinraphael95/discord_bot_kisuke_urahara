# ────────────────────────────────────────────────────────────────────────────────
# 📌 react.py — Commande interactive /react et !react
# Objectif : Réagit à un message avec un ou plusieurs emojis (custom animés ou standards)
# Catégorie : Général
# Accès : Public
# Cooldown : 1 utilisation / 3 sec / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
from utils.discord_utils import safe_send, safe_delete
import random

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class ReactCommand(commands.Cog):
    """Commande interactive /react et !react — Réagit à un message avec des emojis."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction interne pour ajouter des réactions
    # ────────────────────────────────────────────────────────────────────────────
    async def _react_to_message(
        self,
        channel: discord.abc.Messageable,
        guild: discord.Guild,
        emoji_names: list[str],
        reference_message_id: int = None,
        before_time=None,
    ):
        target_message = None

        if reference_message_id:
            target_message = await channel.fetch_message(reference_message_id)
        else:
            async for msg in channel.history(limit=20, before=before_time):
                target_message = msg
                break

        if not target_message:
            await safe_send(channel, "❌ Aucun message valide à réagir.", delete_after=5)
            return

        for emoji_name in emoji_names:
            emoji_name_cleaned = emoji_name.strip()
            emoji_lookup = emoji_name_cleaned.strip(":").lower()

            emoji = next((e for e in guild.emojis if e.name.lower() == emoji_lookup), None)

            if not emoji:
                other_guilds = [g for g in self.bot.guilds if g.id != guild.id]
                for g in random.sample(other_guilds, len(other_guilds)):
                    emoji = next((e for e in g.emojis if e.name.lower() == emoji_lookup and e.available), None)
                    if emoji:
                        break

            try:
                if emoji:
                    await target_message.add_reaction(emoji)
                else:
                    await target_message.add_reaction(emoji_name_cleaned)
            except discord.HTTPException:
                await safe_send(channel, f"❌ Impossible d'ajouter `{emoji_name_cleaned}`.", delete_after=5)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="react",
        description="Réagit avec un ou plusieurs emojis à un message (réponse ou dernier du salon)."
    )
    @app_commands.describe(emojis="Liste d'emojis séparés par des espaces (custom ou standards)")
    @app_commands.checks.cooldown(1, 3.0, key=lambda i: i.user.id)
    async def slash_react(self, interaction: discord.Interaction, emojis: str):
        await interaction.response.defer(ephemeral=True)

        message = None
        if interaction.message and interaction.message.reference:
            message = await interaction.channel.fetch_message(interaction.message.reference.message_id)

        if not message:
            async for msg in interaction.channel.history(limit=5):
                if msg.author != self.bot.user:
                    message = msg
                    break

        if not message:
            await interaction.followup.send("❌ Aucun message trouvé.", ephemeral=True)
            return

        await self._react_to_message(
            channel=message.channel,
            guild=interaction.guild,
            emoji_names=emojis.split(),
            reference_message_id=message.id,
        )

        await interaction.delete_original_response()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(
        name="react",
        aliases=["r"],
        help="Réagit à un message avec un ou plusieurs emojis."
    )
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.user)
    async def prefix_react(self, ctx: commands.Context, *emoji_names: str):
        await safe_delete(ctx.message)
        await self._react_to_message(
            channel=ctx.channel,
            guild=ctx.guild,
            emoji_names=list(emoji_names),
            reference_message_id=ctx.message.reference.message_id if ctx.message.reference else None,
            before_time=ctx.message.created_at,
        )

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = ReactCommand(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Général"
    await bot.add_cog(cog)
