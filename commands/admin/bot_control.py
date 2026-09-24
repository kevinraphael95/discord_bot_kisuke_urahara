# ================================================================================
# 📌 bot_control.py — Commande interactive /bot_control et !bot_control
# Objectif : Panneau admin avec 3 boutons : Git Pull, Reload Cogs, Redémarrer le bot
# Catégorie : Admin
# Accès : Admin uniquement
# Cooldown : 1 utilisation / 10 sec / utilisateur
# ================================================================================

# ================================================================================
# 📦 Imports nécessaires
# ================================================================================
import asyncio
import os
import sys

import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button

from utils.discord_utils import safe_send, safe_edit

# ================================================================================
# 🧠 Vue — Panneau de contrôle
# ================================================================================
class ControlView(View):
    def __init__(self, bot: commands.Bot, author_id: int):
        super().__init__(timeout=180)
        self.bot = bot
        self.author_id = author_id
        self.busy = False
        self.message: discord.Message | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Seul l'auteur, s'il est toujours admin, peut utiliser le panneau."""
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "❌ Ce panneau ne t'appartient pas.", ephemeral=True
            )
            return False
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ Tu dois être administrateur.", ephemeral=True
            )
            return False
        if self.busy:
            await interaction.response.send_message(
                "⏳ Une action est déjà en cours, patiente.", ephemeral=True
            )
            return False
        return True

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message:
            await safe_edit(self.message, view=self)

    # ────────────────────────────────────────────────────────────────────────
    # 🔹 Git Pull
    # ────────────────────────────────────────────────────────────────────────
    @discord.ui.button(label="Git Pull", style=discord.ButtonStyle.blurple, emoji="🔄")
    async def git_pull(self, interaction: discord.Interaction, button: Button):
        self.busy = True
        await interaction.response.defer(thinking=True)
        try:
            proc = await asyncio.create_subprocess_exec(
                "git", "pull",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            output = (stdout or b"").decode(errors="ignore").strip()
            errors = (stderr or b"").decode(errors="ignore").strip()

            texte = output or "(aucune sortie)"
            if errors:
                texte += f"\n\n⚠️ stderr:\n{errors}"
            if len(texte) > 1800:
                texte = texte[:1800] + "\n... (tronqué)"

            embed = discord.Embed(
                title="🔄 Git Pull",
                description=f"```\n{texte}\n```",
                color=discord.Color.green() if proc.returncode == 0 else discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Erreur pendant le git pull : `{e}`")
        finally:
            self.busy = False

    # ────────────────────────────────────────────────────────────────────────
    # 🔹 Reload Cogs
    # ────────────────────────────────────────────────────────────────────────
    @discord.ui.button(label="Reload Cogs", style=discord.ButtonStyle.green, emoji="♻️")
    async def reload_cogs(self, interaction: discord.Interaction, button: Button):
        self.busy = True
        await interaction.response.defer(thinking=True)
        try:
            reussis, echoues = [], []
            for ext in list(self.bot.extensions.keys()):
                try:
                    await self.bot.reload_extension(ext)
                    reussis.append(ext)
                except Exception as e:
                    echoues.append(f"{ext} → `{e}`")

            embed = discord.Embed(
                title="♻️ Reload Cogs",
                color=discord.Color.green() if not echoues else discord.Color.orange()
            )
            embed.add_field(
                name=f"✅ Rechargés ({len(reussis)})",
                value="\n".join(reussis) or "Aucun",
                inline=False
            )
            if echoues:
                embed.add_field(
                    name=f"❌ Échecs ({len(echoues)})",
                    value="\n".join(echoues)[:1000],
                    inline=False
                )
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Erreur pendant le reload : `{e}`")
        finally:
            self.busy = False

    # ────────────────────────────────────────────────────────────────────────
    # 🔹 Redémarrer le bot
    # ────────────────────────────────────────────────────────────────────────
    @discord.ui.button(label="Redémarrer", style=discord.ButtonStyle.red, emoji="🔁")
    async def restart_bot(self, interaction: discord.Interaction, button: Button):
        self.busy = True
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)
        await interaction.followup.send("🔁 Redémarrage du bot en cours...")

        await self.bot.close()
        os.execv(sys.executable, [sys.executable] + sys.argv)

# ================================================================================
# 🧠 Cog principal
# ================================================================================
class BotControl(commands.Cog):
    """Commandes /bot_control et !bot_control — Panneau admin (git pull / reload / restart)."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _send_panel(self, channel: discord.abc.Messageable, author: discord.abc.User):
        embed = discord.Embed(
            title="🛠️ Panneau de contrôle du bot",
            description="Choisis une action ci-dessous.",
            color=discord.Color.blurple()
        )
        view = ControlView(self.bot, author.id)
        view.message = await safe_send(channel, embed=embed, view=view)

    # ================================================================================
    # 🔹 Commande SLASH
    # ================================================================================
    @app_commands.command(name="bot_control", description="(Admin) Panneau de contrôle : git pull, reload cogs, redémarrer.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.checks.cooldown(rate=1, per=10.0, key=lambda i: i.user.id)
    async def slash_bot_control(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await self._send_panel(interaction.channel, interaction.user)
        await interaction.delete_original_response()

    # ================================================================================
    # 🔹 Commande PREFIX
    # ================================================================================
    @commands.command(name="bot_control", aliases=["botctl"], help="(Admin) Panneau de contrôle : git pull, reload cogs, redémarrer.")
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 10.0, commands.BucketType.user)
    async def prefix_bot_control(self, ctx: commands.Context):
        await self._send_panel(ctx.channel, ctx.author)

# ================================================================================
# 🔌 Setup du Cog
# ================================================================================
async def setup(bot: commands.Bot):
    cog = BotControl(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Admin"
    await bot.add_cog(cog)
