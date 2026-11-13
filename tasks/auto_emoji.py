# ================================================================================
# 📌 auto_say.py — Reposter automatiquement les messages avec emojis non accessibles
# Objectif : Simuler un "say *me" automatique pour les emojis non affichables
# ================================================================================

# ================================================================================
# 📦 Modules standards
# ================================================================================
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

# ================================================================================
# 🧠 Cog principal
# ================================================================================
class AutoEmoji(commands.Cog):
    """Reposte automatiquement les messages contenant des emojis non accessibles"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

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

        webhook = await safe_create_webhook(message.channel, name=f"tmp-{message.author.name}")
        if webhook is None:
            return

        try:
            await webhook.send(
                content=new_content,
                username=message.author.display_name,
                avatar_url=message.author.display_avatar.url,
                allowed_mentions=discord.AllowedMentions.all()
            )
        finally:
            await webhook.delete()

        # ✅ Gère le cas où le message a déjà été supprimé (404)
        try:
            await message.delete()
        except discord.NotFound:
            pass  # Le message est déjà supprimé, pas grave

        await self.bot.process_commands(message)

# ================================================================================
# 🔌 Setup
# ================================================================================
async def setup(bot: commands.Bot):
    await bot.add_cog(AutoEmoji(bot))
