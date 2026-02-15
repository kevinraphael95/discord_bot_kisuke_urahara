# ────────────────────────────────────────────────────────────────────────────────
# 📌 reiatsu.py — Commande interactive /reiatsu et !reiatsu
# Objectif : Affiche les informations de spawn Reiatsu du serveur et le classement global
# Catégorie : Reiatsu
# Accès : Public
# Cooldown : 1 utilisation / 3 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
import sqlite3
import time
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button
from dateutil import parser
from datetime import datetime, timedelta, timezone
from utils.discord_utils import safe_send, safe_respond

# ────────────────────────────────────────────────────────────────────────────────
# 🗄️ Configuration SQLite
# ────────────────────────────────────────────────────────────────────────────────
DB_PATH = "database/reiatsu.db"

# ────────────────────────────────────────────────────────────────────────────────
# Infos intervalles de vitesse de spawn
# ────────────────────────────────────────────────────────────────────────────────
SPAWN_SPEED_INTERVALS = {
    "Ultra_Rapide": "1-5 minutes",
    "Rapide": "5-20 minutes",
    "Normal": "30-60 minutes",
    "Lent": "5-10 heures"
}

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ Vue interactive Reiatsu (Classement + Lien Spawn)
# ────────────────────────────────────────────────────────────────────────────────
class ReiatsuView(View):

    def __init__(self, db_cursor, author: discord.Member = None, spawn_link: str = None):
        super().__init__(timeout=None)
        self.author = author
        self.cursor = db_cursor

        if spawn_link:
            self.add_item(
                Button(
                    label="💠 Aller au spawn",
                    style=discord.ButtonStyle.link,
                    url=spawn_link
                )
            )

    @discord.ui.button(label="📊 Classement", style=discord.ButtonStyle.primary, custom_id="reiatsu:classement")
    async def classement_button(self, interaction: discord.Interaction, button: discord.ui.Button):

        if self.author and interaction.user != self.author:
            return await interaction.response.send_message(
                "❌ Tu ne peux pas utiliser ce bouton.",
                ephemeral=True
            )

        try:
            self.cursor.execute("""
                SELECT user_id, points
                FROM reiatsu
                ORDER BY points DESC
                LIMIT 10
            """)
            classement = self.cursor.fetchall()
        except Exception as e:
            print(f"[ERREUR DB] Impossible de récupérer le classement : {e}")
            return await interaction.response.send_message(
                "❌ Erreur lors du chargement du classement.",
                ephemeral=True
            )

        if not classement:
            return await interaction.response.send_message(
                "⚠️ Aucun classement disponible pour le moment.",
                ephemeral=True
            )

        description = ""
        for i, entry in enumerate(classement, start=1):
            user_id = entry["user_id"]
            points = entry["points"]
            user = interaction.guild.get_member(user_id) if interaction.guild else None
            name = user.display_name if user else f"Utilisateur ({user_id})"
            description += f"**{i}. {name}** — {points} points\n"

        embed = discord.Embed(
            title="📊 Classement Reiatsu",
            description=description,
            color=discord.Color.purple()
        )

        await interaction.response.send_message(embed=embed)

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class ReiatsuCommand(commands.Cog):
    """Commande /reiatsu et !reiatsu — Affiche les informations de spawn du serveur et le classement"""

    COOLDOWN = 3

    # ──────────────────────────────────────────────────────────────
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()

        self.bot.add_view(ReiatsuView(self.cursor))
        self.user_cooldowns = {}

    # ──────────────────────────────────────────────────────────────
    async def _check_cooldown(self, user_id: int):
        now = time.time()
        last = self.user_cooldowns.get(user_id, 0)
        if now - last < self.COOLDOWN:
            return self.COOLDOWN - (now - last)
        self.user_cooldowns[user_id] = now
        return 0

    # ──────────────────────────────────────────────────────────────
    async def _send_server_info(self, channel_or_interaction, author, guild):

        guild_id = int(guild.id)

        self.cursor.execute("""
            SELECT *
            FROM reiatsu_config
            WHERE guild_id = ?
        """, (guild_id,))

        config = self.cursor.fetchone()

        salon_text = "❌"
        spawn_speed_text = "⚠️ Inconnu"
        temps_text = "⚠️ Inconnu"
        spawn_link = None

        if config:
            salon = guild.get_channel(config["channel_id"]) if config["channel_id"] else None
            salon_text = salon.mention if salon else "⚠️ Salon introuvable"

            speed_key = config["spawn_speed"]
            if speed_key:
                spawn_speed_text = f"{SPAWN_SPEED_INTERVALS.get(speed_key, '⚠️ Inconnu')} ({speed_key})"

            if config["is_spawn"] and config["message_id"] and config["channel_id"]:
                temps_text = "💠 Un Reiatsu est **déjà apparu** !"
                spawn_link = (
                    f"https://discord.com/channels/"
                    f"{guild_id}/{config['channel_id']}/{config['message_id']}"
                )
            else:
                last_spawn = config["last_spawn_at"]
                delay = config["spawn_delay"] or 1800

                if last_spawn:
                    try:
                        last_spawn_dt = parser.parse(last_spawn)

                        if not last_spawn_dt.tzinfo:
                            last_spawn_dt = last_spawn_dt.replace(tzinfo=timezone.utc)

                        remaining = int(
                            (last_spawn_dt + timedelta(seconds=delay) -
                             datetime.now(timezone.utc)).total_seconds()
                        )

                        if remaining <= 0:
                            temps_text = "💠 Un Reiatsu peut apparaître **à tout moment** !"
                        else:
                            minutes, seconds = divmod(remaining, 60)
                            temps_text = f"**{minutes}m {seconds}s**"
                    except Exception:
                        temps_text = "💠 Un Reiatsu peut apparaître **à tout moment** !"

        embed = discord.Embed(
            title="__Informations Reiatsu du serveur__",
            description=(
                f"📍 **Salon de spawn** : {salon_text}\n"
                f"⏱️ **Vitesse de spawn** : {spawn_speed_text}\n"
                f"⏳ **Prochain spawn** : {temps_text}"
            ),
            color=discord.Color.purple()
        )

        embed.set_footer(
            text="💠 Utilise `!!tutoreiatsu` ou `!!tutorts` pour en savoir plus sur le Reiatsu."
        )

        view = ReiatsuView(self.cursor, author, spawn_link=spawn_link)

        if isinstance(channel_or_interaction, discord.Interaction):
            await channel_or_interaction.response.send_message(embed=embed, view=view)
        else:
            await safe_send(channel_or_interaction, embed=embed, view=view)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commandes SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="reiatsu",
        description="💠 Affiche les informations de spawn Reiatsu du serveur et le classement global."
    )
    async def slash_reiatsu(self, interaction: discord.Interaction):

        remaining = await self._check_cooldown(interaction.user.id)

        if remaining > 0:
            return await safe_respond(
                interaction,
                f"⏳ Attends encore {remaining:.1f}s.",
                ephemeral=True
            )

        await self._send_server_info(
            interaction,
            interaction.user,
            interaction.guild
        )

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commandes PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(
        name="reiatsu",
        aliases=["rts"],
        help="💠 Affiche les informations de spawn Reiatsu du serveur et le classement global."
    )
    async def prefix_reiatsu(self, ctx: commands.Context):

        remaining = await self._check_cooldown(ctx.author.id)

        if remaining > 0:
            return await safe_send(
                ctx.channel,
                f"⏳ Attends encore {remaining:.1f}s."
            )

        await self._send_server_info(
            ctx.channel,
            ctx.author,
            ctx.guild
        )

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = ReiatsuCommand(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Reiatsu"
    await bot.add_cog(cog)
