# ================================================================================
# 📌 notif.py
# Objectif : Gérer les abonnements de notifications Twitch et YouTube
# Catégorie : Fun / Utils
# Accès : Admin
# Cooldown : 1 utilisation / 5 sec par utilisateur
# ================================================================================

# ================================================================================
# 📦 Imports nécessaires
# ================================================================================
import discord
from discord import app_commands
from discord.ext import commands
import logging

from utils.discord_utils import safe_send
from utils.stream_notif import (
    MAX_FOLLOWS_PER_GUILD,
    TWITCH_LOGIN_RE,
    UC_RE,
    all_follows,
    delete_follow,
    init_table,
    query,
    StreamClient,
)

log = logging.getLogger(__name__)


# ================================================================================
# 🧠 Cog principal avec cooldowns centralisés
# ================================================================================
class Notif(commands.Cog):
    """
    Commande /notif et !notif — Gestion des abonnements Twitch / YouTube
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.client = StreamClient()
        self._client_started = False

    async def cog_load(self):
        init_table()

    async def cog_unload(self):
        if self._client_started:
            await self.client.close()

    # ============================================================================
    # 🔹 Fonctions internes communes
    # ============================================================================
    async def _ensure_client(self):
        """Démarre la session HTTP du client uniquement si nécessaire (lazy load)."""
        if not self._client_started:
            await self.client.start()
            self._client_started = True

    async def _send_help(self, channel: discord.abc.Messageable):
        embed = discord.Embed(
            title="📡 Notifications de chaînes",
            color=discord.Color.green(),
            description="Utilise une sous-commande pour gérer les notifications.",
        )
        embed.add_field(
            name="Twitch",
            value="`!!notif twitch <pseudo> [#salon] [@rôle]`\n"
                  "Exemple : `!!notif twitch kevinraphael95 #général @Stream`",
            inline=False,
        )
        embed.add_field(
            name="YouTube",
            value="`!!notif youtube <lien|@handle|ID> [#salon] [@rôle]`\n"
                  "Exemple : `!!notif youtube @LofiGirl #musique`",
            inline=False,
        )
        embed.add_field(
            name="Gestion",
            value="`!!notif list` → Affiche les abonnements du serveur.\n"
                  "`!!notif remove <plateforme> <handle>` → Supprime un abonnement.",
            inline=False,
        )
        await safe_send(channel, embed=embed)

    async def _add_twitch(self, ctx: commands.Context, login: str, salon: discord.TextChannel, role: discord.Role):
        if not login:
            return await safe_send(ctx.channel, "❌ Précise le pseudo Twitch. Ex: `!!notif twitch shroud`")

        login = login.lower()
        if not TWITCH_LOGIN_RE.match(login):
            return await safe_send(ctx.channel, "❌ Pseudo Twitch invalide (alphanumérique uniquement, max 25 caractères).")

        count = query("SELECT COUNT(*) as c FROM notif_follows WHERE guild_id = ?", (ctx.guild.id,))[0]["c"]
        if count >= MAX_FOLLOWS_PER_GUILD:
            return await safe_send(ctx.channel, f"❌ Limite atteinte ({MAX_FOLLOWS_PER_GUILD} abonnements par serveur).")

        await self._ensure_client()
        if self.client.twitch_ok:
            try:
                user = await self.client.twitch_user(login)
            except Exception as e:
                log.warning(f"[notif] Erreur de vérification Twitch pour {login}: {e}")
                return await safe_send(ctx.channel, "⚠️ Impossible de vérifier le compte Twitch pour le moment. Réessaie plus tard.")
            
            if not user:
                return await safe_send(ctx.channel, f"❌ Le compte Twitch `{login}` n'existe pas.")
            display_name = user["display_name"]
        else:
            display_name = login
            await safe_send(ctx.channel, "⚠️ Clés Twitch absentes : la vérification du compte est ignorée.")

        channel_id = salon.id if salon else ctx.channel.id
        role_id = role.id if role else None

        try:
            query(
                """
                INSERT INTO notif_follows (guild_id, platform, handle, display, channel_id, role_id)
                VALUES (?, 'twitch', ?, ?, ?, ?)
                """,
                (ctx.guild.id, login, display_name, channel_id, role_id),
            )
        except Exception as e:
            if "UNIQUE constraint failed" in str(e):
                return await safe_send(ctx.channel, f"ℹ️ `{login}` est déjà suivi sur ce serveur.")
            raise

        msg = f"✅ **{display_name}** ajouté aux notifications Twitch dans <#{channel_id}>."
        if role:
            msg += f" (mention : {role.mention})"
        await safe_send(ctx.channel, msg)

    async def _add_youtube(self, ctx: commands.Context, cible: str, salon: discord.TextChannel, role: discord.Role):
        if not cible:
            return await safe_send(ctx.channel, "❌ Précise un lien, un @handle ou un ID de chaîne YouTube.")

        count = query("SELECT COUNT(*) as c FROM notif_follows WHERE guild_id = ?", (ctx.guild.id,))[0]["c"]
        if count >= MAX_FOLLOWS_PER_GUILD:
            return await safe_send(ctx.channel, f"❌ Limite atteinte ({MAX_FOLLOWS_PER_GUILD} abonnements par serveur).")

        await self._ensure_client()
        try:
            resolved = await self.client.resolve_youtube(cible)
        except Exception as e:
            log.warning(f"[notif] Erreur de résolution YouTube pour {cible}: {e}")
            return await safe_send(ctx.channel, "⚠️ Impossible d'analyser ce lien YouTube. Vérifie qu'il est valide.")

        if not resolved:
            return await safe_send(ctx.channel, f"❌ Chaîne YouTube introuvable pour `{cible}`.")

        cid, name, entries = resolved
        channel_id = salon.id if salon else ctx.channel.id
        role_id = role.id if role else None
        last_id = entries[0]["id"] if entries else None
        last_published = entries[0]["published"].isoformat() if entries else None

        try:
            query(
                """
                INSERT INTO notif_follows (guild_id, platform, handle, display, channel_id, role_id, last_id, last_published)
                VALUES (?, 'youtube', ?, ?, ?, ?, ?, ?)
                """,
                (ctx.guild.id, cid, name, channel_id, role_id, last_id, last_published),
            )
        except Exception as e:
            if "UNIQUE constraint failed" in str(e):
                return await safe_send(ctx.channel, f"ℹ️ La chaîne `{name}` est déjà suivie sur ce serveur.")
            raise

        msg = f"✅ **{name}** ajoutée aux notifications YouTube dans <#{channel_id}>."
        if role:
            msg += f" (mention : {role.mention})"
        await safe_send(ctx.channel, msg)

    async def _list(self, ctx: commands.Context):
        rows = query("SELECT * FROM notif_follows WHERE guild_id = ? ORDER BY platform, handle", (ctx.guild.id,))
        if not rows:
            return await safe_send(ctx.channel, "📭 Aucun abonnement de notification configuré sur ce serveur.")

        embed = discord.Embed(
            title="📋 Abonnements de notifications",
            color=discord.Color.blue(),
            description=f"{len(rows)} abonnement(s) configuré(s).",
        )

        twitchs = [r for r in rows if r["platform"] == "twitch"]
        youtubes = [r for r in rows if r["platform"] == "youtube"]

        if twitchs:
            txt = "\n".join(
                f"• **{r['display']}** (`{r['handle']}`) → <#{r['channel_id']}>"
                + (f" | <@&{r['role_id']}>" if r["role_id"] else "")
                for r in twitchs
            )
            embed.add_field(name=f"🎮 Twitch ({len(twitchs)})", value=txt[:1024], inline=False)

        if youtubes:
            txt = "\n".join(
                f"• **{r['display']}** → <#{r['channel_id']}>"
                + (f" | <@&{r['role_id']}>" if r["role_id"] else "")
                for r in youtubes
            )
            embed.add_field(name=f"📺 YouTube ({len(youtubes)})", value=txt[:1024], inline=False)

        await safe_send(ctx.channel, embed=embed)

    async def _remove(self, ctx: commands.Context, platform: str, handle: str):
        if not platform or not handle:
            return await safe_send(ctx.channel, "❌ Syntaxe : `!!notif remove <twitch|youtube> <handle>`")

        platform = platform.lower()
        if platform not in ("twitch", "youtube"):
            return await safe_send(ctx.channel, "❌ La plateforme doit être `twitch` ou `youtube`.")

        if platform == "twitch":
            handle = handle.lower().lstrip("@")
            rows = query(
                "SELECT id FROM notif_follows WHERE guild_id = ? AND platform = ? AND handle = ?",
                (ctx.guild.id, platform, handle),
            )
        else:
            if UC_RE.search(handle):
                handle = UC_RE.search(handle).group(0)
                rows = query(
                    "SELECT id FROM notif_follows WHERE guild_id = ? AND platform = ? AND handle = ?",
                    (ctx.guild.id, platform, handle),
                )
            else:
                rows = query(
                    "SELECT id FROM notif_follows WHERE guild_id = ? AND platform = ? AND (handle = ? OR display LIKE ?)",
                    (ctx.guild.id, platform, handle, f"%{handle}%"),
                )

        if not rows:
            return await safe_send(ctx.channel, f"❌ Aucun abonnement `{handle}` trouvé pour {platform}.")

        for r in rows:
            delete_follow(r["id"])

        await safe_send(ctx.channel, f"✅ Abonnement(s) `{handle}` ({platform}) supprimé(s).")

    # ============================================================================
    # 🔹 Commande SLASH
    # ============================================================================
    @app_commands.command(name="notif", description="Gère les notifications de live Twitch et de vidéos YouTube.")
    @app_commands.checks.cooldown(rate=1, per=5.0, key=lambda i: i.user.id)
    @app_commands.checks.has_permissions(administrator=True)
    async def slash_notif(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self._send_help(interaction.channel)
        await interaction.delete_original_response()

    # ============================================================================
    # 🔹 Commande PREFIX
    # ============================================================================
    @commands.group(name="notif", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_notif(self, ctx: commands.Context):
        await self._send_help(ctx.channel)

    @prefix_notif.command(name="twitch")
    @commands.has_permissions(administrator=True)
    async def prefix_notif_twitch(
        self,
        ctx: commands.Context,
        login: str = None,
        salon: discord.TextChannel = None,
        role: discord.Role = None,
    ):
        await self._add_twitch(ctx, login, salon, role)

    @prefix_notif.command(name="youtube")
    @commands.has_permissions(administrator=True)
    async def prefix_notif_youtube(
        self,
        ctx: commands.Context,
        cible: str = None,
        salon: discord.TextChannel = None,
        role: discord.Role = None,
    ):
        await self._add_youtube(ctx, cible, salon, role)

    @prefix_notif.command(name="list")
    @commands.has_permissions(administrator=True)
    async def prefix_notif_list(self, ctx: commands.Context):
        await self._list(ctx)

    @prefix_notif.command(name="remove", aliases=["rm", "del"])
    @commands.has_permissions(administrator=True)
    async def prefix_notif_remove(self, ctx: commands.Context, platform: str = None, handle: str = None):
        await self._remove(ctx, platform, handle)


# ================================================================================
# 🔌 Setup du Cog
# ================================================================================
async def setup(bot: commands.Bot):
    cog = Notif(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Admin"
    await bot.add_cog(cog)
