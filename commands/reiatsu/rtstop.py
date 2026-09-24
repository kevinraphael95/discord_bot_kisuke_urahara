# ================================================================================
# 📌 reiatsutop.py — Commande interactive /reiatsutop et !reiatsutop
# Objectif : Affiche le classement global Reiatsu (Top 20) + position de l'utilisateur
# Catégorie : Reiatsu
# Accès : Public
# Cooldown : 1 utilisation / 3 secondes / utilisateur
# ================================================================================

# ================================================================================
# 📦 Imports nécessaires
# ================================================================================
import discord
import sqlite3
import time
from discord import app_commands
from discord.ext import commands
from utils.discord_utils import safe_send, safe_respond

# ================================================================================
# 🗄️ Configuration SQLite
# ================================================================================
DB_PATH = "database/reiatsu.db"

# ================================================================================
# 🏅 Médailles pour le podium
# ================================================================================
MEDALS = {1: "🥇", 2: "🥈", 3: "🥉"}

# ================================================================================
# 🧠 Cog principal
# ================================================================================
class ReiatsuTopCommand(commands.Cog):
    """Commande /reiatsutop et !reiatsutop — Affiche le Top 20 Reiatsu et la position de l'utilisateur"""

    COOLDOWN = 3

    # ==============================================================
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()

        self.user_cooldowns = {}

    # ==============================================================
    async def _check_cooldown(self, user_id: int):
        now = time.time()
        last = self.user_cooldowns.get(user_id, 0)
        if now - last < self.COOLDOWN:
            return self.COOLDOWN - (now - last)
        self.user_cooldowns[user_id] = now
        return 0

    # ==============================================================
    async def _send_top(self, channel_or_interaction, author: discord.Member, guild: discord.Guild):

        user_id = author.id

        # == Récupération du Top 20 ==
        try:
            self.cursor.execute("""
                SELECT user_id, points
                FROM reiatsu
                ORDER BY points DESC
                LIMIT 20
            """)
            top20 = self.cursor.fetchall()
        except Exception as e:
            print(f"[ERREUR DB] Impossible de récupérer le classement : {e}")
            msg = "❌ Erreur lors du chargement du classement."
            if isinstance(channel_or_interaction, discord.Interaction):
                return await channel_or_interaction.response.send_message(msg, ephemeral=True)
            return await safe_send(channel_or_interaction, msg)

        if not top20:
            msg = "⚠️ Aucun classement disponible pour le moment."
            if isinstance(channel_or_interaction, discord.Interaction):
                return await channel_or_interaction.response.send_message(msg, ephemeral=True)
            return await safe_send(channel_or_interaction, msg)

        # == Construction du classement ==
        description = ""
        user_in_top = False

        for i, entry in enumerate(top20, start=1):
            uid = entry["user_id"]
            points = entry["points"]
            member = guild.get_member(uid) if guild else None
            name = member.display_name if member else f"Utilisateur ({uid})"
            medal = MEDALS.get(i, f"**#{i}**")
            highlight = " ◀" if uid == user_id else ""
            description += f"{medal} **{name}** — {points} pts{highlight}\n"

            if uid == user_id:
                user_in_top = True

        # == Position de l'utilisateur s'il n'est pas dans le Top 20 ==
        footer_extra = ""
        if not user_in_top:
            try:
                self.cursor.execute("""
                    SELECT COUNT(*) as rank
                    FROM reiatsu
                    WHERE points > (
                        SELECT points FROM reiatsu WHERE user_id = ?
                    )
                """, (user_id,))
                row = self.cursor.fetchone()

                self.cursor.execute("""
                    SELECT points FROM reiatsu WHERE user_id = ?
                """, (user_id,))
                user_row = self.cursor.fetchone()

                if user_row:
                    rank = (row["rank"] if row else 0) + 1
                    points = user_row["points"]
                    description += f"\n{'=' * 30}\n"
                    description += f"📍 **Ta position** : #{rank} — {points} pts\n"
                else:
                    description += f"\n{'=' * 30}\n"
                    description += "📍 **Ta position** : Non classé (0 pts)\n"

            except Exception as e:
                print(f"[ERREUR DB] Impossible de récupérer la position de l'utilisateur : {e}")

        embed = discord.Embed(
            title="📊 Classement Reiatsu — Top 20",
            description=description,
            color=discord.Color.purple()
        )

        embed.set_footer(
            text="💠 Utilise `!!tutoreiatsu` ou `!!tutorts` pour en savoir plus sur le Reiatsu."
        )

        if isinstance(channel_or_interaction, discord.Interaction):
            await channel_or_interaction.response.send_message(embed=embed)
        else:
            await safe_send(channel_or_interaction, embed=embed)

    # ============================================================================
    # 🔹 Commandes SLASH
    # ============================================================================
    @app_commands.command(
        name="reiatsutop",
        description="📊 Affiche le Top 20 Reiatsu et ta position dans le classement global."
    )
    async def slash_reiatsutop(self, interaction: discord.Interaction):

        remaining = await self._check_cooldown(interaction.user.id)

        if remaining > 0:
            return await safe_respond(
                interaction,
                f"⏳ Attends encore {remaining:.1f}s.",
                ephemeral=True
            )

        await self._send_top(
            interaction,
            interaction.user,
            interaction.guild
        )

    # ============================================================================
    # 🔹 Commandes PREFIX
    # ============================================================================
    @commands.command(
        name="reiatsutop",
        aliases=["rtst"],
        help="📊 Affiche le Top 20 Reiatsu et ta position dans le classement global."
    )
    async def prefix_reiatsutop(self, ctx: commands.Context):

        remaining = await self._check_cooldown(ctx.author.id)

        if remaining > 0:
            return await safe_send(
                ctx.channel,
                f"⏳ Attends encore {remaining:.1f}s."
            )

        await self._send_top(
            ctx.channel,
            ctx.author,
            ctx.guild
        )

# ================================================================================
# 🔌 Setup du Cog
# ================================================================================
async def setup(bot: commands.Bot):
    cog = ReiatsuTopCommand(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Reiatsu"
    await bot.add_cog(cog)
