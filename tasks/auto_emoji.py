# ────────────────────────────────────────────────────────────────────────────────
# 📌 auto_say.py — Reposter automatiquement les messages avec emojis non accessibles
# Objectif : Simuler un "say *me" automatique pour les emojis non affichables
# Catégorie : Fun
# Accès : Tous
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands
import re

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class AutoEmoji(commands.Cog):
    """Reposte automatiquement les messages contenant des emojis non accessibles"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ──────────────────────────────────────────────────────────
    # 🔹 Fonction pour remplacer les emojis custom (identique à say.py)
    # ──────────────────────────────────────────────────────────
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

    # ──────────────────────────────────────────────────────────
    # 🔹 Listener sur tous les messages
    # ──────────────────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not hasattr(message.channel, "guild"):
            return

        content = message.content
        if not content:
            return

        # Ignore les commandes (messages commençant par le préfixe du bot)
        prefix = self.bot.command_prefix
        if callable(prefix):
            prefixes = await prefix(self.bot, message)
            prefixes = [prefixes] if isinstance(prefixes, str) else list(prefixes)
        else:
            prefixes = [prefix] if isinstance(prefix, str) else list(prefix)

        if any(content.startswith(p) for p in prefixes):
            return

        # Remplacement des emojis custom
        new_content = self._replace_custom_emojis(message.channel, content)

        # Si rien n'a changé, aucun emoji à corriger → on ne repost pas
        if new_content == content:
            return

        # Identique à _say_as_user dans say.py : webhook temporaire créé puis supprimé
        webhook = await message.channel.create_webhook(name=f"tmp-{message.author.name}")
        try:
            await webhook.send(
                content=new_content,
                username=message.author.display_name,
                avatar_url=message.author.display_avatar.url,
                allowed_mentions=discord.AllowedMentions.all()
            )
        finally:
            await webhook.delete()

        # Supprime le message original
        await message.delete()

        # Permettre aux autres cogs/commands de traiter le message
        await self.bot.process_commands(message)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    await bot.add_cog(AutoEmoji(bot))
