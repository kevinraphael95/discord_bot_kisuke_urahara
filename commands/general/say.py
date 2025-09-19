# ────────────────────────────────────────────────────────────────────────────────
# 📌 say.py — Commande interactive /say et !say
# Objectif : Faire répéter un message par le bot, avec options combinables (embed, as_user, etc.)
# Catégorie : Général
# Accès : Public
# Cooldown : 1 utilisation / 5 sec / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
import re
from discord import app_commands
from discord.ext import commands
from utils.discord_utils import safe_send, safe_delete, safe_respond  

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class Say(commands.Cog):
    """Commande /say et !say — Faire répéter un message par le bot, avec options modulables."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ──────────────────────────────────────────────────────────────
    # 🔧 Parsing des options
    # ──────────────────────────────────────────────────────────────
    def parse_options(self, raw_message: str):
        """
        Analyse le début du message et active les options.
        Retourne: (options: dict, message_sans_options: str)
        """
        options = {"embed": False, "as_user": False}
        words = raw_message.split()
        remaining = []

        for w in words:
            lw = w.lower()
            if lw in ("embed", "e"):
                options["embed"] = True
            elif lw in ("as", "me", "myself", "user"):
                options["as_user"] = True
            else:
                remaining.append(w)

        return options, " ".join(remaining)

    # ──────────────────────────────────────────────────────────────
    # 🔹 Fonction interne : envoi classique
    # ──────────────────────────────────────────────────────────────
    async def _say_message(self, channel: discord.abc.Messageable, message: str, embed: bool = False):
        """Envoie un message normal (bot) avec remplacement des emojis custom."""
        message = (message or "").strip()
        if not message:
            return await safe_send(channel, "⚠️ Message vide.")

        # 🔹 Remplacement des emojis custom
        if hasattr(channel, "guild"):
            guild_emojis = {e.name.lower(): str(e) for e in channel.guild.emojis}
            message = re.sub(
                r":([a-zA-Z0-9_]+):",
                lambda m: guild_emojis.get(m.group(1).lower(), m.group(0)),
                message,
                flags=re.IGNORECASE
            )

        # 🔹 Limite Discord
        if len(message) > 2000:
            message = message[:1997] + "..."

        # 🔹 Envoi final
        if embed:
            embed_obj = discord.Embed(description=message, color=discord.Color.blurple())
            await safe_send(channel, embed=embed_obj, allowed_mentions=discord.AllowedMentions.none())
        else:
            await safe_send(channel, message, allowed_mentions=discord.AllowedMentions.none())

    # ──────────────────────────────────────────────────────────────
    # 🔹 Fonction interne : envoi "as user"
    # ──────────────────────────────────────────────────────────────
    async def _say_as_user(self, channel: discord.TextChannel, user: discord.User, message: str):
        """Envoie un message via webhook avec pseudo et avatar de l'utilisateur."""
        message = (message or "").strip()
        if not message:
            return await safe_send(channel, "⚠️ Message vide.")

        # 🔹 Remplacement emojis custom
        if hasattr(channel, "guild"):
            guild_emojis = {e.name.lower(): str(e) for e in channel.guild.emojis}
            message = re.sub(
                r":([a-zA-Z0-9_]+):",
                lambda m: guild_emojis.get(m.group(1).lower(), m.group(0)),
                message,
                flags=re.IGNORECASE
            )

        # 🔹 Limite Discord
        if len(message) > 2000:
            message = message[:1997] + "..."

        # 🔹 Création d'un webhook temporaire
        webhook = await channel.create_webhook(name=f"tmp-{user.name}")
        try:
            await webhook.send(content=message, username=user.display_name, avatar_url=user.display_avatar.url)
        finally:
            await webhook.delete()

    # ──────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ──────────────────────────────────────────────────────────────
    @app_commands.command(
        name="say",
        description="Fait répéter un message par le bot, avec options (embed, as_user, ...)."
    )
    @app_commands.describe(
        message="Message à répéter",
        embed="Envoyer dans un embed",
        as_user="Parler comme vous"
    )
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_say(self, interaction: discord.Interaction, message: str, embed: bool = False, as_user: bool = False):
        try:
            await interaction.response.defer()
            if as_user:
                await self._say_as_user(interaction.channel, interaction.user, message)
            else:
                await self._say_message(interaction.channel, message, embed)
            await safe_respond(interaction, "✅ Message envoyé !", ephemeral=True)
        except Exception as e:
            print(f"[ERREUR /say] {e}")
            await safe_respond(interaction, "❌ Impossible d’envoyer le message.", ephemeral=True)

    # ──────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ──────────────────────────────────────────────────────────────
    @commands.command(
        name="say",
        help="Fait répéter un message par le bot. Options : 'embed', 'as'. Ex: !say embed as Bonjour !"
    )
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_say(self, ctx: commands.Context, *, message: str):
        try:
            options, clean_message = self.parse_options(message)
            if options["as_user"]:
                await self._say_as_user(ctx.channel, ctx.author, clean_message)
            else:
                await self._say_message(ctx.channel, clean_message, options["embed"])
        except Exception as e:
            print(f"[ERREUR !say] {e}")
            await safe_send(ctx.channel, "❌ Impossible d’envoyer le message.")
        finally:
            await safe_delete(ctx.message)

# ──────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ──────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Say(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Général"
    await bot.add_cog(cog)
