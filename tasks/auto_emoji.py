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
        self.webhooks_cache = {}  # cache des webhooks par channel

    # ──────────────────────────────────────────────────────────
    # 🔹 Fonction pour remplacer les emojis custom
    # ──────────────────────────────────────────────────────────
    def _replace_custom_emojis(self, channel, message: str) -> str:
        """
        Cherche les :nom: dans le message et les remplace par le vrai emoji
        (<a:nom:id> ou <:nom:id>) s'il existe sur le serveur.
        """
        # Index des emojis du serveur courant : nom (lowercase) -> objet emoji
        emoji_map = {}
        if hasattr(channel, "guild"):
            emoji_map = {e.name.lower(): e for e in channel.guild.emojis}

        return re.sub(
            r":([a-zA-Z0-9_]+):",
            lambda m: str(emoji_map[m.group(1).lower()])
                      if m.group(1).lower() in emoji_map
                      else m.group(0),
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

        # Remplacement des :nom: par les vrais emojis du serveur
        new_content = self._replace_custom_emojis(message.channel, content)

        # Si rien n'a changé, aucun emoji à corriger → on ne repost pas
        if new_content == content:
            return

        # Récupère ou crée un webhook pour ce canal
        webhook = self.webhooks_cache.get(message.channel.id)
        if webhook is None:
            webhooks = await message.channel.webhooks()
            webhook = discord.utils.get(webhooks, name="AutoEmojiWebhook")
            if webhook is None:
                webhook = await message.channel.create_webhook(name="AutoEmojiWebhook")
            self.webhooks_cache[message.channel.id] = webhook

        # Reposte le message via webhook
        await webhook.send(
            content=new_content,
            username=message.author.display_name,
            avatar_url=message.author.display_avatar.url,
            allowed_mentions=discord.AllowedMentions.all()
        )

        # Supprime le message original
        await message.delete()

        # Permettre aux autres cogs/commands de traiter le message
        await self.bot.process_commands(message)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    await bot.add_cog(AutoEmoji(bot))
