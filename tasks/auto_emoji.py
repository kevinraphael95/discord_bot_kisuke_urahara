# ────────────────────────────────────────────────────────────────────────────────
# 📌 auto_emoji.py — Refaire automatiquement les messages avec emojis animés ou d'autres serveurs
# Objectif : Simuler Not Quite Nitro, repost pour que les emojis fonctionnent partout
# Catégorie : Fun
# Accès : Tous
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands

# ──────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ──────────────────────────────────────────────────────────────
class AutoEmoji(commands.Cog):
    """
    Repost les messages contenant des emojis animés ou d'autres serveurs
    pour qu'ils s'affichent correctement, tout en conservant mentions et markdown.
    """
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ──────────────────────────────────────────────────────────────
    # 🔹 Événement : nouveau message
    # ──────────────────────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return  # Ignorer les bots
        if not hasattr(message.channel, "guild"):
            return  # Ignorer les DM

        content = message.content
        if not content:
            return

        # Récupérer tous les emojis animés et emojis d'autres serveurs
        other_emojis = {}
        for g in self.bot.guilds:
            if g.id != message.guild.id:
                for e in g.emojis:
                    other_emojis[e.name.lower()] = f"<{'a' if e.animated else ''}:{e.name}:{e.id}>"

        import re
        found = False
        # Fonction pour remplacer seulement les emojis d'autres serveurs
        def replace_emoji(match):
            nonlocal found
            name = match.group(1).lower()
            if name in other_emojis:
                found = True
                return other_emojis[name]
            return match.group(0)

        new_content = re.sub(r":([a-zA-Z0-9_]+):", replace_emoji, content)

        # Si aucun emoji à remplacer, sortir
        if not found:
            return

        # Refaire le message via webhook
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

        # Supprimer le message original pour un effet transparent
        await message.delete()
