# ================================================================================
# 📌 auto_emoji.py — Reposter automatiquement les messages avec emojis non accessibles
# Objectif : Simuler un "say *me" automatique pour les emojis non affichables
# ================================================================================

# ================================================================================
# 📦 Modules standards
# ================================================================================
import asyncio
import re
import time

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
# ⚙️ Paramètres globaux
# ================================================================================
WEBHOOK_NAME = "auto-emoji"
COOLDOWN_SECONDS = 900   # pause de 15 min après un échec de création
SPAM_LIMIT = 5           # max de messages avec emoji par utilisateur...
SPAM_WINDOW = 10         # ...sur cette fenêtre (secondes)

RE_STATIC = re.compile(r"<:([a-zA-Z0-9_]+):\d+>")
RE_ANIMATED = re.compile(r"<a:([a-zA-Z0-9_]+):\d+>")
RE_SHORTCODE = re.compile(r":([a-zA-Z0-9_]+):")

# ================================================================================
# 🧠 Cog principal
# ================================================================================
class AutoEmoji(commands.Cog):
    """Reposte automatiquement les messages contenant des emojis non accessibles"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._webhooks: dict[int, discord.Webhook] = {}   # channel_id -> webhook
        self._locks: dict[int, asyncio.Lock] = {}
        self._cooldown: dict[int, float] = {}             # channel_id -> fin de la pause
        self._history: dict[int, list[float]] = {}        # user_id -> horodatages récents
        self._emoji_by_guild: dict[int, dict[str, str]] = {}  # guild_id -> {nom: emoji}
        self._emoji_global: dict[str, str] = {}               # nom -> emoji (tous serveurs)

    # ==========================================================
    # 🔹 Index des emojis (construit une fois, mis à jour si besoin)
    # ==========================================================
    def _build_emoji_index(self):
        by_guild = {}
        global_idx = {}
        for g in self.bot.guilds:
            names = {e.name.lower(): str(e) for e in g.emojis}
            by_guild[g.id] = names
            for name, emoji in names.items():
                global_idx.setdefault(name, emoji)
        self._emoji_by_guild = by_guild
        self._emoji_global = global_idx

    async def cog_load(self):
        # Utile quand le cog est rechargé alors que le bot est déjà connecté
        self._build_emoji_index()

    @commands.Cog.listener()
    async def on_ready(self):
        self._build_emoji_index()

    @commands.Cog.listener()
    async def on_guild_emojis_update(self, guild, before, after):
        self._build_emoji_index()

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        self._build_emoji_index()

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        self._build_emoji_index()

    # ==========================================================
    # 🔹 Récupère (ou crée UNE seule fois) le webhook du salon
    # ==========================================================
    async def _get_webhook(self, channel) -> discord.Webhook | None:
        wh = self._webhooks.get(channel.id)
        if wh:
            return wh
        if time.monotonic() < self._cooldown.get(channel.id, 0):
            return None

        lock = self._locks.setdefault(channel.id, asyncio.Lock())
        async with lock:
            wh = self._webhooks.get(channel.id)
            if wh:
                return wh
            if time.monotonic() < self._cooldown.get(channel.id, 0):
                return None

            # 1) Cherche un webhook existant (simple lecture, pas de limite de création)
            try:
                for existing in await channel.webhooks():
                    if existing.name == WEBHOOK_NAME:
                        self._webhooks[channel.id] = existing
                        return existing
            except discord.Forbidden:
                self._cooldown[channel.id] = time.monotonic() + COOLDOWN_SECONDS
                return None

            # 2) Sinon, UNE seule tentative de création, abandon rapide si rate limit
            try:
                wh = await asyncio.wait_for(
                    safe_create_webhook(channel, name=WEBHOOK_NAME, retry=0),
                    timeout=10
                )
            except (asyncio.TimeoutError, discord.HTTPException):
                wh = None

            if wh is None:
                self._cooldown[channel.id] = time.monotonic() + COOLDOWN_SECONDS
                return None

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
        message = RE_STATIC.sub(r":\1:", message)
        message = RE_ANIMATED.sub(r":\1:", message)

        if ":" not in message:
            return message

        local = self._emoji_by_guild.get(channel.guild.id, {})

        def repl(m):
            name = m.group(1).lower()
            # Serveur du salon d'abord, puis les autres serveurs
            return local.get(name) or self._emoji_global.get(name) or m.group(0)

        return RE_SHORTCODE.sub(repl, message)

    # ==========================================================
    # 🔹 Anti-spam par utilisateur
    # ==========================================================
    def _is_spam(self, user_id: int) -> bool:
        now = time.monotonic()
        recent = [t for t in self._history.get(user_id, []) if now - t < SPAM_WINDOW]
        if len(recent) >= SPAM_LIMIT:
            self._history[user_id] = recent
            return True
        recent.append(now)
        self._history[user_id] = recent
        return False

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

        if self._is_spam(message.author.id):
            return  # trop de messages : on laisse le texte brut

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
            # Webhook supprimé à la main : on vide le cache, il sera retrouvé/recréé au prochain message
            self._webhooks.pop(message.channel.id, None)
            return
        except discord.HTTPException:
            # Envoi impossible : on laisse le message original intact
            return

        # ✅ Gère le cas où le message a déjà été supprimé (404)
        try:
            await message.delete()
        except (discord.NotFound, discord.Forbidden):
            pass

# ================================================================================
# 🔌 Setup
# ================================================================================
async def setup(bot: commands.Bot):
    await bot.add_cog(AutoEmoji(bot))
