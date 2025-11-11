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
class AutoSay(commands.Cog):
    """Reposte automatiquement les messages contenant des emojis non affichables"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.webhooks_cache = {}  # cache des webhooks par channel

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not hasattr(message.channel, "guild"):
            return

        content = message.content
        if not content:
            return

        # Cherche tous les emojis custom du message (animés ou non)
        emojis_in_message = re.findall(r"<a?:[a-zA-Z0-9_]+:\d+>", content)
        if not emojis_in_message:
            return  # pas d'emoji, on ignore

        # Récupère ou crée un webhook pour ce canal
        webhook = self.webhooks_cache.get(message.channel.id)
        if webhook is None:
            webhooks = await message.channel.webhooks()
            webhook = discord.utils.get(webhooks, name="AutoSayWebhook")
            if webhook is None:
                webhook = await message.channel.create_webhook(name="AutoSayWebhook")
            self.webhooks_cache[message.channel.id] = webhook

        # Reposte le message via webhook
        await webhook.send(
            content=content,
            username=message.author.display_name,
            avatar_url=message.author.display_avatar.url,
            allowed_mentions=discord.AllowedMentions.all()
        )

        # Supprime le message original
        await message.delete()

        # Permettre aux autres cogs/commands de traiter le message
        await self.bot.process_commands(message)

# ──────────────────────────────────────────────────────────────
# 🔌 Setup
# ──────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    await bot.add_cog(AutoSay(bot))
