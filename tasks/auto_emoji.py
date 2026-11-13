# ================================================================================
# 📌 auto_emoji.py — Reposter automatiquement les messages avec emojis non accessibles
# Objectif : Simuler un "say *me" automatique pour les emojis non affichables
# ================================================================================

# ================================================================================
# 📦 Modules standards
# ================================================================================
import asyncio
import re

# ================================================================================
# 📦  Modules tiers
# ================================================================================
import discord
from discord.ext import commands

# ================================================================================
# 📦 Modules internes
# ================================================================================
from utils.discord_anti429 import safe_create_webhook

WEBHOOK_NAME = "auto-emoji"

# ================================================================================
# 🧠 Cog principal
# ================================================================================
class AutoEmoji(commands.Cog):
    """Reposte automatiquement les messages contenant des emojis non accessibles"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._webhooks: dict[int, discord.Webhook] = {}  # channel_id -> webhook
        self._locks: dict[int, asyncio.Lock] = {}

    # ==========================================================
    # 🔹 Récupère (ou crée UNE seule fois) le webhook du salon
    # ==========================================================
    async def _get_webhook(self, channel) -> discord.Webhook | None:
        wh = self._webhooks.get(channel.id)
        if wh:
            return wh

        lock = self._locks.setdefault(channel.id, asyncio.Lock())
        async with lock:
            wh = self._webhooks.get(channel.id)
            if wh:
                return wh

            try:
                for existing in await channel.webhooks():
                    if existing.name == WEBHOOK_NAME and existing.user and existing.user.id == self.bot.user.id:
                        self._webhooks[channel.id] = existing
                        return existing
            except discord.Forbidden:
                return None

            wh = await safe_create_webhook(channel, name=WEBHOOK_NAME)
            if wh:
                self._webhooks[channel.id] = wh
            return wh

    # ==========================================================
    # 🔹 Vérifie si le message est une commande bot
    # ==========================================================
    async def _is_command(self, message: discord.Message) -> bool:
        ctx = await self.bot.get_context(message)
        return ctx.valid

    # ==========================================================
    # 🔹 Remplace les emojis custom
    # ==========================================================
    def _replace_custom_emojis(self, channel, message: str) -> str:
        message = re.sub(r"<:([a-zA-Z0-9_]+):\d+>", r":\1:", message)
        message = re.sub(r"<a:([a-zA-Z0-9_]+):\d+>", r":\1:", message)

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

    # ==========================================================
    # 🔹 Listener sur tous les messages
    # ==========================================================
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # ✅ Ignore les bots ET les webhooks (anti-boucle infinie)
        if message.author.bot or message.webhook_id is not None:
            return
        if not hasattr(message.channel, "guild"):
            return

        content = message.content
        if not content:
            return

        if await self._is_command(message):
            return

        new_content = self._replace_custom_emojis(message.channel, content)

        if new_content == content:
            return

        webhook = await self._get_webhook(message.channel)
        if webhook is None:
            return

        try:
            await webhook.send(
                content=new_content,
                username=message.author.display_name,
                avatar_url=message.author.display_avatar.url,
                allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False)
            )
        except discord.NotFound:
            # Webhook supprimé à la main : on vide le cache, il sera recréé au prochain message
            self._webhooks.pop(message.channel.id, None)
            return

        try:
            await message.delete()
        except discord.NotFound:
            pass

# ================================================================================
# 🔌 Setup
# ================================================================================
async def setup(bot: commands.Bot):
    await bot.add_cog(AutoEmoji(bot))
