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
    def _replace_custom_emojis(self, channel, message: str) -> tuple[str, bool]:
        """
        Retourne (nouveau_contenu, a_été_modifié).
        Gère deux formats :
          - <a:nom:id> / <:nom:id>  → emoji déjà résolu par Discord (utilisateurs Nitro)
          - :nom:                   → texte brut envoyé par les non-Nitro (Discord ne le convertit PAS)
        """
        # Construit le dictionnaire de tous les emojis accessibles
        all_emojis = {}
        guild_emoji_ids = set()

        if hasattr(channel, "guild"):
            for e in channel.guild.emojis:
                all_emojis[e.name.lower()] = str(e)
                # Seuls les emojis STATIQUES du serveur courant sont déjà affichables par tous
                # Les animés nécessitent Nitro → on les traite aussi
                if not e.animated:
                    guild_emoji_ids.add(e.id)

            for g in self.bot.guilds:
                if g.id != channel.guild.id:
                    for e in g.emojis:
                        all_emojis.setdefault(e.name.lower(), str(e))

        modified = False

        # ── Format 1 : <a:nom:id> ou <:nom:id> (envoyé par les utilisateurs Nitro) ──
        def replace_full(match):
            nonlocal modified
            emoji_id = int(match.group(3))
            name = match.group(2)

            # Emoji statique du serveur courant → tout le monde peut le voir, on ne touche pas
            if emoji_id in guild_emoji_ids:
                return match.group(0)

            # Emoji animé du serveur courant ou emoji d'un autre serveur → on remplace
            replacement = all_emojis.get(name.lower())
            if replacement:
                modified = True
                return replacement

            return match.group(0)

        new_content = re.sub(r"<(a?):([a-zA-Z0-9_]+):(\d+)>", replace_full, message)

        # ── Format 2 : :nom: (envoyé par les non-Nitro, Discord NE convertit PAS ce texte) ──
        def replace_short(match):
            nonlocal modified
            name = match.group(1)
            replacement = all_emojis.get(name.lower())
            if replacement:
                modified = True
                return replacement
            return match.group(0)

        new_content = re.sub(r":([a-zA-Z0-9_]+):", replace_short, new_content)

        return new_content, modified

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

        new_content, was_modified = self._replace_custom_emojis(message.channel, content)

        # On reposte UNIQUEMENT si un emoji a réellement été remplacé
        if not was_modified:
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
