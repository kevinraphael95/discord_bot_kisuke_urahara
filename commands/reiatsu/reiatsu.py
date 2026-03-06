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
from datetime import datetime, timedelta, timezone

import discord
from dateutil import parser
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View

from utils.discord_utils import safe_respond, safe_send
from utils.init_db import get_conn

# ────────────────────────────────────────────────────────────────────────────────
# 📂 Constantes
# ────────────────────────────────────────────────────────────────────────────────
SPAWN_SPEED_INTERVALS = {
    "Ultra_Rapide": "1-5 minutes",
    "Rapide": "5-20 minutes",
    "Normal": "30-60 minutes",
    "Lent": "5-10 heures",
}

# ────────────────────────────────────────────────────────────────────────────────
# 🗄️ Helpers DB
# ────────────────────────────────────────────────────────────────────────────────
def get_server_config(guild_id: int):
    conn = get_conn()
    conn.row_factory = __import__("sqlite3").Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM reiatsu_config WHERE guild_id = ?", (guild_id,))
    row = cursor.fetchone()
    conn.close()
    return row

def get_classement():
    conn = get_conn()
    conn.row_factory = __import__("sqlite3").Row
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, points FROM reiatsu ORDER BY points DESC LIMIT 10")
    rows = cursor.fetchall()
    conn.close()
    return rows

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ UI — Vue Reiatsu (bouton persistant + lien spawn)
# ────────────────────────────────────────────────────────────────────────────────
class ReiatsuView(View):
    def __init__(self, author: discord.Member = None, spawn_link: str = None):
        super().__init__(timeout=None)
        self.author = author

        if spawn_link:
            self.add_item(
                Button(
                    label="💠 Aller au spawn",
                    style=discord.ButtonStyle.link,
                    url=spawn_link,
                )
            )

    @discord.ui.button(label="📊 Classement", style=discord.ButtonStyle.primary, custom_id="reiatsu:classement")
    async def classement_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.author and interaction.user != self.author:
            return await safe_respond(interaction, "❌ Tu ne peux pas utiliser ce bouton.", ephemeral=True)

        classement = get_classement()

        if not classement:
            return await safe_respond(interaction, "⚠️ Aucun classement disponible pour le moment.", ephemeral=True)

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
            color=discord.Color.purple(),
        )
        await safe_respond(interaction, embed=embed)

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class ReiatsuCommand(commands.Cog):
    """Commande /reiatsu et !reiatsu — Affiche les infos de spawn du serveur et le classement"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.add_view(ReiatsuView())  # enregistrement du bouton persistant

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction interne commune
    # ────────────────────────────────────────────────────────────────────────────
    async def _send_server_info(self, channel, author: discord.Member, guild: discord.Guild):
        config = get_server_config(guild.id)

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
                    f"{guild.id}/{config['channel_id']}/{config['message_id']}"
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
                            (last_spawn_dt + timedelta(seconds=delay) - datetime.now(timezone.utc)).total_seconds()
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
            color=discord.Color.purple(),
        )
        embed.set_footer(text="💠 Utilise `!!tutoreiatsu` ou `!!tutorts` pour en savoir plus sur le Reiatsu.")

        view = ReiatsuView(author, spawn_link=spawn_link)
        await safe_send(channel, embed=embed, view=view)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="reiatsu",
        description="💠 Affiche les informations de spawn Reiatsu du serveur et le classement global.",
    )
    @app_commands.checks.cooldown(rate=1, per=3.0, key=lambda i: i.user.id)
    async def slash_reiatsu(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await self._send_server_info(interaction.channel, interaction.user, interaction.guild)
        await interaction.delete_original_response()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(
        name="reiatsu",
        aliases=["rts"],
        help="💠 Affiche les informations de spawn Reiatsu du serveur et le classement global.",
    )
    @commands.cooldown(1, 3.0, commands.BucketType.user)
    async def prefix_reiatsu(self, ctx: commands.Context):
        await self._send_server_info(ctx.channel, ctx.author, ctx.guild)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = ReiatsuCommand(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Reiatsu"
    await bot.add_cog(cog)
