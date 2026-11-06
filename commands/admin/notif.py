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

    @staticmethod
    def _exists(guild_id: int, platform: str, handle: str) -> bool:
        return bool(query(
            "SELECT id FROM notif_follows WHERE guild_id = ? AND platform = ? AND handle = ?",
            (guild_id, platform, handle),
        ))

    @staticmethod
    def _count(guild_id: int) -> int:
        return query("SELECT COUNT(*) AS c FROM notif_follows WHERE guild_id = ?", (guild_id,))[0]["c"]

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
                  "`!!notif remove <plateforme> <handle>` → Supprime un abonnement.\n"
                  "`!!notif test` → Force une vérification maintenant.\n"
                  "*Pour modifier le salon ou le rôle : refais simplement la commande d'ajout.*\n"
                  "*Si tu mets un rôle, mets aussi le salon avant.*",
            inline=False,
        )
        await safe_send(channel, embed=embed)

    async def _add_twitch(self, ctx: commands.Context, login: str, salon: discord.TextChannel, role: discord.Role):
        if not login:
            return await safe_send(ctx.channel, "❌ Précise le pseudo Twitch. Ex: `!!notif twitch shroud`")

        # Accepte "pseudo", "@pseudo", "twitch.tv/pseudo", "https://twitch.tv/pseudo?sr=a"...
        login = login.strip().split("?")[0].split("#")[0].rstrip("/").split("/")[-1].lstrip("@").lower()
        if not TWITCH_LOGIN_RE.match(login):
            return await safe_send(ctx.channel, "❌ Pseudo Twitch invalide (alphanumérique uniquement, max 25 caractères).")

        exists = self._exists(ctx.guild.id, "twitch", login)
        if not exists and self._count(ctx.guild.id) >= MAX_FOLLOWS_PER_GUILD:
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

        query(
            """
            INSERT INTO notif_follows (guild_id, platform, handle, display, channel_id, role_id)
            VALUES (?, 'twitch', ?, ?, ?, ?)
            ON CONFLICT (guild_id, platform, handle) DO UPDATE SET
                display = excluded.display,
                channel_id = excluded.channel_id,
                role_id = excluded.role_id,
                fail_count = 0
            """,
            (ctx.guild.id, login, display_name, channel_id, role_id),
        )

        verbe = "mis à jour" if exists else "ajouté"
        msg = f"✅ **{display_name}** {verbe} (Twitch) → <#{channel_id}>."
        if role:
            msg += f" (mention : {role.mention})"
        await safe_send(ctx.channel, msg)

    async def _add_youtube(self, ctx: commands.Context, cible: str, salon: discord.TextChannel, role: discord.Role):
        if not cible:
            return await safe_send(ctx.channel, "❌ Précise un lien, un @handle ou un ID de chaîne YouTube.")

        await self._ensure_client()
        try:
            resolved = await self.client.resolve_youtube(cible)
        except Exception as e:
            log.warning(f"[notif] Erreur de résolution YouTube pour {cible}: {e}")
            return await safe_send(ctx.channel, "⚠️ Impossible d'analyser ce lien YouTube. Vérifie qu'il est valide.")

        if not resolved:
            return await safe_send(ctx.channel, f"❌ Chaîne YouTube introuvable pour `{cible}`.")

        cid, name, entries = resolved

        exists = self._exists(ctx.guild.id, "youtube", cid)
        if not exists and self._count(ctx.guild.id) >= MAX_FOLLOWS_PER_GUILD:
            return await safe_send(ctx.channel, f"❌ Limite atteinte ({MAX_FOLLOWS_PER_GUILD} abonnements par serveur).")

        channel_id = salon.id if salon else ctx.channel.id
        role_id = role.id if role else None
        # On "amorce" avec la dernière vidéo pour ne pas annoncer l'ancien contenu
        last_id = entries[0]["id"] if entries else None
        last_published = entries[0]["published"].isoformat() if entries else None

        # En cas de mise à jour, last_id / last_published ne sont PAS modifiés
        query(
            """
            INSERT INTO notif_follows
                (guild_id, platform, handle, display, channel_id, role_id, last_id, last_published)
            VALUES (?, 'youtube', ?, ?, ?, ?, ?, ?)
            ON CONFLICT (guild_id, platform, handle) DO UPDATE SET
                display = excluded.display,
                channel_id = excluded.channel_id,
                role_id = excluded.role_id,
                fail_count = 0
            """,
            (ctx.guild.id, cid, name, channel_id, role_id, last_id, last_published),
        )

        verbe = "mise à jour" if exists else "ajoutée"
        msg = f"✅ **{name}** {verbe} (YouTube) → <#{channel_id}>."
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

        def line(r: dict, show_handle: bool = False) -> str:
            handle = f" (`{r['handle']}`)" if show_handle else ""
            role = f" | <@&{r['role_id']}>" if r["role_id"] else ""
            warn = " ⚠️" if r.get("fail_count") else ""
            return f"• **{r['display']}**{handle} → <#{r['channel_id']}>{role}{warn}"

        twitchs = [r for r in rows if r["platform"] == "twitch"]
        youtubes = [r for r in rows if r["platform"] == "youtube"]

        if twitchs:
            txt = "\n".join(line(r, show_handle=True) for r in twitchs)
            embed.add_field(name=f"🎮 Twitch ({len(twitchs)})", value=txt[:1024], inline=False)

        if youtubes:
            txt = "\n".join(line(r) for r in youtubes)
            embed.add_field(name=f"📺 YouTube ({len(youtubes)})", value=txt[:1024], inline=False)

        if any(r.get("fail_count") for r in rows):
            embed.set_footer(text="⚠️ = le bot n'arrive pas à écrire dans ce salon (permissions ?)")

        await safe_send(ctx.channel, embed=embed)

    async def _remove(self, ctx: commands.Context, platform: str, handle: str):
        if not platform or not handle:
            return await safe_send(ctx.channel, "❌ Syntaxe : `!!notif remove <twitch|youtube> <handle>`")

        platform = platform.lower()
        if platform == "yt":
            platform = "youtube"
        if platform not in ("twitch", "youtube"):
            return await safe_send(ctx.channel, "❌ La plateforme doit être `twitch` ou `youtube`.")

        if platform == "twitch":
            handle = handle.strip().split("?")[0].rstrip("/").split("/")[-1].lstrip("@").lower()
            rows = query(
                "SELECT id FROM notif_follows WHERE guild_id = ? AND platform = ? AND handle = ?",
                (ctx.guild.id, platform, handle),
            )
        else:
            m = UC_RE.search(handle)
            if m:
                handle = m.group(0)
                rows = query(
                    "SELECT id FROM notif_follows WHERE guild_id = ? AND platform = ? AND handle = ?",
                    (ctx.guild.id, platform, handle),
                )
            else:
                # Correspondance EXACTE sur le nom affiché (sans le @ éventuel)
                name = handle.lstrip("@")
                rows = query(
                    "SELECT id FROM notif_follows WHERE guild_id = ? AND platform = ? "
                    "AND (handle = ? OR LOWER(display) = LOWER(?))",
                    (ctx.guild.id, platform, handle, name),
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
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_notif(self, ctx: commands.Context):
        await self._send_help(ctx.channel)

    @prefix_notif.command(name="twitch")
    async def prefix_notif_twitch(
        self,
        ctx: commands.Context,
        login: str = None,
        salon: discord.TextChannel = None,
        role: discord.Role = None,
    ):
        await self._add_twitch(ctx, login, salon, role)

    @prefix_notif.command(name="youtube", aliases=["yt"])
    async def prefix_notif_youtube(
        self,
        ctx: commands.Context,
        cible: str = None,
        salon: discord.TextChannel = None,
        role: discord.Role = None,
    ):
        await self._add_youtube(ctx, cible, salon, role)

    @prefix_notif.command(name="list", aliases=["liste"])
    async def prefix_notif_list(self, ctx: commands.Context):
        await self._list(ctx)

    @prefix_notif.command(name="remove", aliases=["rm", "del"])
    async def prefix_notif_remove(self, ctx: commands.Context, platform: str = None, handle: str = None):
        await self._remove(ctx, platform, handle)

    @prefix_notif.command(name="test")
    async def prefix_notif_test(self, ctx: commands.Context):
        """Force une vérification (⚠️ envoie de vraies annonces)."""
        task_cog = self.bot.get_cog("StreamAlertTask")
        if not task_cog:
            return await safe_send(ctx.channel, "❌ Le cog `StreamAlertTask` n'est pas chargé.")

        await safe_send(ctx.channel, "🔄 Vérification manuelle en cours...")
        try:
            if task_cog.client.twitch_ok:
                await task_cog._check_twitch()
            await task_cog._check_youtube()
            await safe_send(ctx.channel, "✅ Vérification terminée.")
        except Exception as e:
            log.exception("[notif] Erreur pendant le test")
            await safe_send(ctx.channel, f"⚠️ Erreur pendant le test : `{e}`")


# ================================================================================
# 🔌 Setup du Cog
# ================================================================================
async def setup(bot: commands.Bot):
    cog = Notif(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Admin"
    await bot.add_cog(cog)
