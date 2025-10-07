# ────────────────────────────────────────────────────────────────────────────────
# 📌 say.py — Commande interactive /say et !say
# Objectif : Faire répéter un message par le bot, avec options combinables (*embed, *as_me, ...)
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
        Analyse les options au début du message (*embed, *as_me, etc.) et retourne
        le message restant **tel quel**, sans modifier les retours à la ligne ni les espaces.
        """
        options = {"embed": False, "as_user": False}

        # Détecte les options au début
        opts_pattern = r"^(?:\*(embed|e|as_me|am|me)\s*)+"
        match = re.match(opts_pattern, raw_message, re.IGNORECASE)
        if match:
            opts_part = match.group()
            if re.search(r"\*(embed|e)\b", opts_part, re.IGNORECASE):
                options["embed"] = True
            if re.search(r"\*(as_me|am|me)\b", opts_part, re.IGNORECASE):
                options["as_user"] = True
            raw_message = raw_message[len(opts_part):]  # garde le texte exact après les options

        return options, raw_message

    # ──────────────────────────────────────────────────────────────
    # 🔹 Envoi normal
    # ──────────────────────────────────────────────────────────────
    async def _say_message(self, channel: discord.abc.Messageable, message: str, embed: bool = False):
        if not message:
            return
        message = self._replace_custom_emojis(channel, message)
        if len(message) > 2000:
            message = message[:1997] + "..."
        if embed:
            embed_obj = discord.Embed(description=message, color=discord.Color.blurple())
            await safe_send(channel, embed=embed_obj, allowed_mentions=discord.AllowedMentions.none())
        else:
            await safe_send(channel, message, allowed_mentions=discord.AllowedMentions.none())

    # ──────────────────────────────────────────────────────────────
    # 🔹 Envoi "as user"
    # ──────────────────────────────────────────────────────────────
    async def _say_as_user(self, channel: discord.TextChannel, user: discord.User, message: str, embed: bool = False):
        if not message:
            return
        message = self._replace_custom_emojis(channel, message)
        if len(message) > 2000:
            message = message[:1997] + "..."
        webhook = await channel.create_webhook(name=f"tmp-{user.name}")
        try:
            if embed:
                embed_obj = discord.Embed(description=message, color=discord.Color.blurple())
                await webhook.send(username=user.display_name, avatar_url=user.display_avatar.url, embed=embed_obj)
            else:
                await webhook.send(username=user.display_name, avatar_url=user.display_avatar.url, content=message)
        finally:
            await webhook.delete()

    # ──────────────────────────────────────────────────────────────
    # 🔹 Remplacement emojis custom
    # ──────────────────────────────────────────────────────────────
    def _replace_custom_emojis(self, channel, message: str) -> str:
        if hasattr(channel, "guild"):
            guild_emojis = {e.name.lower(): str(e) for e in channel.guild.emojis}
            return re.sub(
                r":([a-zA-Z0-9_]+):",
                lambda m: guild_emojis.get(m.group(1).lower(), m.group(0)),
                message,
                flags=re.IGNORECASE
            )
        return message

    # ──────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ──────────────────────────────────────────────────────────────
    @app_commands.command(
        name="say",
        description="Fait répéter un message par le bot, avec options combinables (*embed, *as_me, ...)."
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
                await self._say_as_user(interaction.channel, interaction.user, message, embed)
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
        help="Fait répéter un message par le bot. Options : *embed / *e, *as_me / *am. Ex: !say *e *am Bonjour !"
    )
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_say(self, ctx: commands.Context, *, message: str):
        try:
            options, clean_message = self.parse_options(message)
            if options["as_user"]:
                await self._say_as_user(ctx.channel, ctx.author, clean_message, options["embed"])
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


