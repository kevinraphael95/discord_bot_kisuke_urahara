# ────────────────────────────────────────────────────────────────────────────────
# 📌 ReiatsuAdmin.py — Commande interactive /reiatsuadmin et !reiatsuadmin / !rtsa
# Objectif : Gérer les paramètres Reiatsu (définir, supprimer un salon, ou modifier les points d'un membre)
# Catégorie : Admin
# Accès : Administrateur
# Cooldown : 1 utilisation / 5 secondes / utilisateur (sauf spawn : 3s)
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import asyncio
import json
import logging
import os
import random
from datetime import datetime

import discord
from discord import app_commands, ui
from discord.ext import commands

from utils.discord_utils import safe_send, safe_respond, safe_interact, safe_edit
from utils.init_db import get_conn

log = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────────────────────────
# 📂 Chargement du JSON global
# ────────────────────────────────────────────────────────────────────────────────
CONFIG_PATH = os.path.join("data", "reiatsu_config.json")
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

SPAWN_SPEED_RANGES  = CONFIG["SPAWN_SPEED_RANGES"]
DEFAULT_SPAWN_SPEED = CONFIG["DEFAULT_SPAWN_SPEED"]

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ UI — View boutons vitesse (partagée prefix + slash)
# ────────────────────────────────────────────────────────────────────────────────

def build_speed_embed(current_speed_name: str, current_delay: int) -> discord.Embed:
    embed = discord.Embed(
        title="⚡ Vitesse du spawn de Reiatsu",
        description=f"**Vitesse actuelle :** {current_speed_name} ({current_delay} s)",
        color=discord.Color.blurple()
    )
    embed.add_field(
        name="Vitesses possibles",
        value="\n".join([f"{name} → {min_d}-{max_d} s" for name, (min_d, max_d) in SPAWN_SPEED_RANGES.items()]),
        inline=False
    )
    return embed


class SpeedButton(ui.Button):
    def __init__(self, name: str, guild_id: int, author_id: int):
        super().__init__(label=name, style=discord.ButtonStyle.primary, custom_id=f"speed_{name}")
        self.guild_id  = guild_id
        self.author_id = author_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            await safe_interact(interaction, "❌ Ce bouton n'est pas pour vous.", ephemeral=True)
            return

        new_speed_name       = self.label
        min_delay, max_delay = SPAWN_SPEED_RANGES[new_speed_name]
        new_delay            = random.randint(min_delay, max_delay)

        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE reiatsu_config SET spawn_delay = ?, spawn_speed = ? WHERE guild_id = ?",
                (new_delay, new_speed_name, self.guild_id)
            )
            conn.commit()

        await safe_interact(
            interaction,
            embed=discord.Embed(
                title="✅ Vitesse du spawn modifiée",
                description=f"Nouvelle vitesse : **{new_speed_name}** ({new_delay} s)",
                color=discord.Color.green()
            ),
            view=None,
            edit=True
        )


class SpeedView(ui.View):
    def __init__(self, guild_id: int, author_id: int, current_speed_name: str):
        super().__init__(timeout=60)
        self.message = None
        for name in SPAWN_SPEED_RANGES:
            if name != current_speed_name:
                self.add_item(SpeedButton(name, guild_id, author_id))

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await safe_edit(self.message, view=self)
            except Exception:
                pass

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────

class ReiatsuAdmin(commands.Cog):
    """
    Commandes /reiatsuadmin et !reiatsuadmin / !rtsa — Gère Reiatsu : set, unset, change, spawn, speed.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonctions internes communes
    # ────────────────────────────────────────────────────────────────────────────
    async def _set_logic(self, guild_id: int, channel_id: int) -> str:
        now_iso       = datetime.utcnow().isoformat()
        delay         = random.randint(*SPAWN_SPEED_RANGES[DEFAULT_SPAWN_SPEED])
        default_speed = DEFAULT_SPAWN_SPEED
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM reiatsu_config WHERE guild_id = ?", (guild_id,))
            if cur.fetchone():
                cur.execute("""
                    UPDATE reiatsu_config
                    SET channel_id = ?, last_spawn_at = ?, spawn_delay = ?, spawn_speed = ?, is_spawn = 0, message_id = NULL
                    WHERE guild_id = ?
                """, (channel_id, now_iso, delay, default_speed, guild_id))
            else:
                cur.execute("""
                    INSERT INTO reiatsu_config(guild_id, channel_id, last_spawn_at, spawn_delay, spawn_speed, is_spawn)
                    VALUES (?, ?, ?, ?, ?, 0)
                """, (guild_id, channel_id, now_iso, delay, default_speed))
            conn.commit()
        return default_speed

    async def _unset_logic(self, guild_id: int) -> bool:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM reiatsu_config WHERE guild_id = ?", (guild_id,))
            if cur.fetchone():
                cur.execute("DELETE FROM reiatsu_config WHERE guild_id = ?", (guild_id,))
                conn.commit()
                return True
        return False

    async def _change_logic(self, member: discord.Member, points: int) -> str:
        user_id  = member.id
        username = member.display_name
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM reiatsu WHERE user_id = ?", (user_id,))
            if cur.fetchone():
                cur.execute("UPDATE reiatsu SET points = ? WHERE user_id = ?", (points, user_id))
                status = "🔄 Score mis à jour"
            else:
                cur.execute("INSERT INTO reiatsu(user_id, username, points) VALUES (?, ?, ?)", (user_id, username, points))
                status = "🆕 Nouveau score enregistré"
            conn.commit()
        return status

    async def _speed_logic(self, guild_id: int) -> tuple | None:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT spawn_delay, spawn_speed FROM reiatsu_config WHERE guild_id = ?", (guild_id,))
            return cur.fetchone()

    async def _spawn_logic(self, channel: discord.abc.Messageable):
        embed   = discord.Embed(
            title="💠 Un Reiatsu sauvage apparaît !",
            description="Cliquez sur la réaction 💠 pour l'absorber.",
            color=discord.Color.purple()
        )
        message = await safe_send(channel, embed=embed)
        if not message:
            return
        try:
            await message.add_reaction("💠")
        except discord.HTTPException:
            pass

        def check(reaction, user):
            return reaction.message.id == message.id and str(reaction.emoji) == "💠" and not user.bot

        try:
            _, user = await self.bot.wait_for("reaction_add", timeout=40.0, check=check)
            await safe_send(channel, f"💠 {user.mention} a absorbé le Reiatsu !")
        except asyncio.TimeoutError:
            await safe_send(channel, "⏳ Le Reiatsu s'est dissipé dans l'air... personne ne l'a absorbé.")

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Groupe SLASH
    # ────────────────────────────────────────────────────────────────────────────
    rtsa_slash = app_commands.Group(
        name="reiatsuadmin",
        description="(Admin) Gère le Reiatsu : set, unset, change, spawn, speed."
    )

    @rtsa_slash.command(name="set", description="Définit le salon de spawn de Reiatsu.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.checks.cooldown(rate=1, per=5.0, key=lambda i: i.user.id)
    async def slash_set(self, interaction: discord.Interaction):
        default_speed = await self._set_logic(interaction.guild.id, interaction.channel.id)
        await safe_respond(interaction, f"✅ Le salon {interaction.channel.mention} est configuré avec vitesse **{default_speed}**.", ephemeral=True)

    @rtsa_slash.command(name="unset", description="Supprime le salon Reiatsu configuré.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.checks.cooldown(rate=1, per=5.0, key=lambda i: i.user.id)
    async def slash_unset(self, interaction: discord.Interaction):
        removed = await self._unset_logic(interaction.guild.id)
        msg = "🗑️ Le salon Reiatsu a été **supprimé** de la configuration." if removed else "❌ Aucun salon Reiatsu n'était configuré sur ce serveur."
        await safe_respond(interaction, msg, ephemeral=True)

    @rtsa_slash.command(name="change", description="Modifie les points Reiatsu d'un membre.")
    @app_commands.describe(member="Le membre à modifier", points="Nouveau score (positif)")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.checks.cooldown(rate=1, per=5.0, key=lambda i: i.user.id)
    async def slash_change(self, interaction: discord.Interaction, member: discord.Member, points: int):
        if points < 0:
            await safe_respond(interaction, "❌ Le score Reiatsu doit être un nombre **positif**.", ephemeral=True)
            return
        status = await self._change_logic(member, points)
        embed  = discord.Embed(
            title="🌟 Mise à jour du Reiatsu",
            description=f"👤 Membre : {member.mention}\n✨ Nouveau score : `{points}` points\n\n{status}",
            color=discord.Color.blurple()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"Modifié par {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
        await safe_respond(interaction, embed=embed, ephemeral=True)

    @rtsa_slash.command(name="spawn", description="Force le spawn immédiat d'un Reiatsu.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.checks.cooldown(rate=1, per=3.0, key=lambda i: i.user.id)
    async def slash_spawn(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await self._spawn_logic(interaction.channel)
        await interaction.delete_original_response()

    @rtsa_slash.command(name="speed", description="Gère la vitesse du spawn de Reiatsu.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.checks.cooldown(rate=1, per=5.0, key=lambda i: i.user.id)
    async def slash_speed(self, interaction: discord.Interaction):
        row = await self._speed_logic(interaction.guild.id)
        if not row:
            await safe_respond(interaction, "❌ Aucun salon Reiatsu configuré pour ce serveur.", ephemeral=True)
            return
        current_delay, current_speed_name = row[0], row[1] or DEFAULT_SPAWN_SPEED
        embed = build_speed_embed(current_speed_name, current_delay)
        view  = SpeedView(interaction.guild.id, interaction.user.id, current_speed_name)
        await safe_respond(interaction, embed=embed, view=view)
        view.message = await interaction.original_response()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Groupe PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.group(name="reiatsuadmin",aliases=["rtsa"],invoke_without_command=True,help="(Admin) Gère le Reiatsu : set, unset, change, spawn, speed.")
    @commands.has_permissions(administrator=True)
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    async def reiatsuadmin(self, ctx: commands.Context):
        embed = discord.Embed(
            title="🧪 Commande Reiatsu Admin",
            description=(
                "Voici les sous-commandes disponibles :\n\n"
                "`!!rtsa set` — Définit le salon de spawn de Reiatsu\n"
                "`!!rtsa unset` — Supprime le salon configuré\n"
                "`!!rtsa change @membre <points>` — Modifie les points d'un membre\n"
                "`!!rtsa spawn` — Force le spawn immédiat d'un Reiatsu\n"
                "`!!rtsa speed` — Gère la vitesse du spawn"
            ),
            color=discord.Color.blurple()
        )
        embed.set_footer(text="Réservé aux administrateurs")
        await safe_send(ctx, embed=embed)

    @reiatsuadmin.command(name="set")
    @commands.has_permissions(administrator=True)
    async def set_reiatsu(self, ctx: commands.Context):
        default_speed = await self._set_logic(ctx.guild.id, ctx.channel.id)
        await safe_send(ctx, f"✅ Le salon {ctx.channel.mention} est configuré pour le spawn avec vitesse **{default_speed}**.")

    @reiatsuadmin.command(name="unset")
    @commands.has_permissions(administrator=True)
    async def unset_reiatsu(self, ctx: commands.Context):
        removed = await self._unset_logic(ctx.guild.id)
        msg = "🗑️ Le salon Reiatsu a été **supprimé** de la configuration." if removed else "❌ Aucun salon Reiatsu n'était configuré sur ce serveur."
        await safe_send(ctx, msg)

    @reiatsuadmin.command(name="change")
    @commands.has_permissions(administrator=True)
    async def change_reiatsu(self, ctx: commands.Context, member: discord.Member, points: int):
        if points < 0:
            await safe_send(ctx, "❌ Le score Reiatsu doit être un nombre **positif**.")
            return
        status = await self._change_logic(member, points)
        embed  = discord.Embed(
            title="🌟 Mise à jour du Reiatsu",
            description=f"👤 Membre : {member.mention}\n✨ Nouveau score : `{points}` points\n\n{status}",
            color=discord.Color.blurple()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"Modifié par {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
        await safe_send(ctx, embed=embed)

    @reiatsuadmin.command(name="spawn")
    @commands.has_permissions(administrator=True)
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.user)
    async def spawn_reiatsu(self, ctx: commands.Context):
        await self._spawn_logic(ctx.channel)

    @reiatsuadmin.command(name="speed")
    @commands.has_permissions(administrator=True)
    async def speed_reiatsu(self, ctx: commands.Context):
        row = await self._speed_logic(ctx.guild.id)
        if not row:
            await safe_send(ctx, "❌ Aucun salon Reiatsu configuré pour ce serveur.")
            return
        current_delay, current_speed_name = row[0], row[1] or DEFAULT_SPAWN_SPEED
        embed        = build_speed_embed(current_speed_name, current_delay)
        view         = SpeedView(ctx.guild.id, ctx.author.id, current_speed_name)
        message      = await safe_send(ctx, embed=embed, view=view)
        view.message = message

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = ReiatsuAdmin(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Admin"
    await bot.add_cog(cog)
