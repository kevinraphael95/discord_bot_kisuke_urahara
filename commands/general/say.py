# ────────────────────────────────────────────────────────────────────────────────
# 📌 say.py — Commande interactive /say et !say
# Objectif : Faire répéter un message par le bot, avec options combinables (*embed, *as_me, *chuchotte, ...)
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

# ──────────────────────────────────────────────────────────────
# 🔹 Vue pour les messages secrets
# ──────────────────────────────────────────────────────────────
class SecretMessageView(discord.ui.View):
    def __init__(self, target_user: discord.User, secret_message: str):
        super().__init__(timeout=1920)  # 32 minutes
        self.target_user = target_user
        self.secret_message = secret_message

    @discord.ui.button(label="🔒 Voir le message", style=discord.ButtonStyle.blurple)
    async def reveal(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.target_user.id:
            await interaction.response.send_message("❌ Ce message ne t’est pas destiné !", ephemeral=True)
            return
        await interaction.response.send_message(f"💌 **Message secret :** {self.secret_message}", ephemeral=True)

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        self.stop()

# ──────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ──────────────────────────────────────────────────────────────
class Say(commands.Cog):
    """Commande /say et !say — Faire répéter un message par le bot, avec options modulables."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ──────────────────────────────────────────────────────────────
    # 🔧 Parsing des options
    # ──────────────────────────────────────────────────────────────
    def parse_options(self, raw_message: str):
        options = {"embed": False, "as_user": False, "chuchotte": False}
        opts_pattern = r"^(?:\*(embed|e|as_me|am|me|chuchotte|ch)\s*)+"
        match = re.match(opts_pattern, raw_message, re.IGNORECASE)
        if match:
            opts_part = match.group()
            if re.search(r"\*(embed|e)\b", opts_part, re.IGNORECASE):
                options["embed"] = True
            if re.search(r"\*(as_me|am|me)\b", opts_part, re.IGNORECASE):
                options["as_user"] = True
            if re.search(r"\*(chuchotte|ch)\b", opts_part, re.IGNORECASE):
                options["chuchotte"] = True
            raw_message = raw_message[len(opts_part):]
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
    # 🔹 Remplacement emojis custom (avec affichage correct)
    # ──────────────────────────────────────────────────────────────
    def _replace_custom_emojis(self, channel, message: str) -> str:
        # Supprime l'affichage en texte brut des emojis non animés (<:nom:id>)
        message = re.sub(r"<:([a-zA-Z0-9_]+):\d+>", r":\1:", message)
        # Supprime aussi les emojis animés (<a:nom:id>)
        message = re.sub(r"<a:([a-zA-Z0-9_]+):\d+>", r":\1:", message)

        # Remplace par des emojis valides si trouvés dans les serveurs du bot
        all_emojis = {}
        if hasattr(channel, "guild"):
            all_emojis.update({e.name.lower(): str(e) for e in channel.guild.emojis})
            for g in self.bot.guilds:
                if g.id != channel.guild.id:
                    all_emojis.update({e.name.lower(): str(e) for e in g.emojis})

        return re.sub(
            r":([a-zA-Z0-9_]+):",
            lambda m: all_emojis.get(m.group(1).lower(), m.group(0)),
            message,
            flags=re.IGNORECASE
        )

    # ────────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="say",
        description="Fait répéter un message par le bot, avec options combinables (*embed, *as_me, *chuchotte, ...)."
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
            options, clean_message = self.parse_options(message)
            if options["chuchotte"]:
                mention = next((m for m in interaction.message.mentions), None)
                if not mention:
                    await safe_respond(interaction, "❌ Tu dois mentionner une personne pour *chuchotte.", ephemeral=True)
                    return
                secret_text = clean_message.replace(mention.mention, "").strip()
                view = SecretMessageView(mention, secret_text)
                await interaction.channel.send(f"🔒 Message secret pour {mention.mention}", view=view)
                return
            if as_user:
                await self._say_as_user(interaction.channel, interaction.user, clean_message, embed)
            else:
                await self._say_message(interaction.channel, clean_message, embed)
        except Exception as e:
            print(f"[ERREUR /say] {e}")
            await safe_respond(interaction, "❌ Impossible d’envoyer le message.", ephemeral=True)

    # ────────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────────
    @commands.command(
        name="say",
        help="Fait répéter un message par le bot. Options : *embed / *e, *as_me / *am, *chuchotte / *ch. Ex: !say *e *am Bonjour !"
    )
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_say(self, ctx: commands.Context, *, message: str):
        try:
            options, clean_message = self.parse_options(message)
            if options["chuchotte"]:
                mention = next((m for m in ctx.message.mentions), None)
                if not mention:
                    await safe_send(ctx.channel, "❌ Tu dois mentionner une personne pour *chuchotte.")
                    return
                secret_text = clean_message.replace(mention.mention, "").strip()
                view = SecretMessageView(mention, secret_text)
                await ctx.channel.send(f"🔒 Message secret pour {mention.mention}", view=view)
                return
            if options["as_user"]:
                await self._say_as_user(ctx.channel, ctx.author, clean_message, options["embed"])
            else:
                await self._say_message(ctx.channel, clean_message, options["embed"])
        except Exception as e:
            print(f"[ERREUR !say] {e}")
            await safe_send(ctx.channel, "❌ Impossible d’envoyer le message.")
        finally:
            await safe_delete(ctx.message)


# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Say(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Général"
    await bot.add_cog(cog)
