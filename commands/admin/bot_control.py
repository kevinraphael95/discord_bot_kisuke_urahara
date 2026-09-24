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
import subprocess
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
    # 🔹 Base de l'embed du panneau (titre + description fixes)
    # ────────────────────────────────────────────────────────────────────────
    def _base_embed(self, color: discord.Color = discord.Color.blurple()) -> discord.Embed:
        return discord.Embed(
            title="🛠️ Panneau de contrôle du bot",
            description="Choisis une action ci-dessous.",
            color=color
        )

    # ────────────────────────────────────────────────────────────────────────
    # 🔹 Git Pull
    # ────────────────────────────────────────────────────────────────────────
    @discord.ui.button(label="Git Pull", style=discord.ButtonStyle.blurple, emoji="🔄")
    async def git_pull(self, interaction: discord.Interaction, button: Button):
        self.busy = True
        await interaction.response.defer()
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
            if errors and proc.returncode != 0:
                texte += f"\n\n⚠️ stderr:\n{errors}"
            if len(texte) > 1000:
                texte = texte[:1000] + "\n... (tronqué)"

            embed = self._base_embed(
                discord.Color.green() if proc.returncode == 0 else discord.Color.red()
            )
            embed.add_field(name="🔄 Git Pull", value=f"```\n{texte}\n```", inline=False)
            await safe_edit(self.message, embed=embed, view=self)
        except Exception as e:
            embed = self._base_embed(discord.Color.red())
            embed.add_field(name="🔄 Git Pull", value=f"❌ Erreur : `{e}`", inline=False)
            await safe_edit(self.message, embed=embed, view=self)
        finally:
            self.busy = False

    # ────────────────────────────────────────────────────────────────────────
    # 🔹 Reload Cogs
    # ────────────────────────────────────────────────────────────────────────
    @discord.ui.button(label="Reload Cogs", style=discord.ButtonStyle.green, emoji="♻️")
    async def reload_cogs(self, interaction: discord.Interaction, button: Button):
        self.busy = True
        await interaction.response.defer()
        try:
            reussis, echoues = [], []
            for ext in list(self.bot.extensions.keys()):
                try:
                    await self.bot.reload_extension(ext)
                    reussis.append(ext)
                except Exception as e:
                    echoues.append(f"{ext} → `{e}`")

            embed = self._base_embed(
                discord.Color.green() if not echoues else discord.Color.orange()
            )
            embed.add_field(
                name="♻️ Reload Cogs",
                value=f"✅ {len(reussis)} rechargé(s) — ❌ {len(echoues)} échec(s)",
                inline=False
            )
            if echoues:
                embed.add_field(
                    name=f"❌ Échecs ({len(echoues)})",
                    value="\n".join(echoues)[:1000],
                    inline=False
                )
            await safe_edit(self.message, embed=embed, view=self)
        except Exception as e:
            embed = self._base_embed(discord.Color.red())
            embed.add_field(name="♻️ Reload Cogs", value=f"❌ Erreur : `{e}`", inline=False)
            await safe_edit(self.message, embed=embed, view=self)
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

        embed = self._base_embed(discord.Color.orange())
        embed.add_field(name="🔁 Redémarrage", value="En cours...", inline=False)
        await interaction.response.edit_message(embed=embed, view=self)

        try:
            # ⚠️ On NE fait PAS os.execv() ici.
            # execv() remplace l'image du process en place mais n'importe
            # quel socket déjà ouvert (ex: celui de l'admin panel Flask sur
            # le port 5050) reste ouvert et lié au port dans le nouveau
            # process — le nouveau bot.py qui tente de re-binder le même
            # port échoue alors silencieusement, et l'admin panel devient
            # inaccessible après ce type de redémarrage.
            #
            # À la place, on relance start.sh (qui gère lui-même le
            # détachement du bot et la redirection des logs vers bot.log),
            # puis on tue le process courant avec SIGKILL. Ça garantit un
            # vrai redémarrage propre : tunnel Cloudflare + admin panel +
            # bot repartent tous à zéro, sans fd hérité.
            #
            # start.sh fait un `cd "$(dirname "$0")"` avant de lancer
            # bot.py, donc le cwd courant du process est déjà la racine
            # du repo : c'est de là qu'on retrouve start.sh, peu importe
            # où se trouve ce fichier cog dans l'arborescence.
            start_sh = os.path.join(os.getcwd(), "start.sh")

            subprocess.Popen(
                ["bash", start_sh],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
                start_new_session=True
            )

            sys.stdout.flush()
            sys.stderr.flush()
            await asyncio.sleep(1)
            os.kill(os.getpid(), 9)
        except Exception as e:
            # Si on arrive ici, le relancement a échoué : on ne veut pas
            # rester bloqué en "busy" pour toujours.
            print(f"[Restart] Échec du redémarrage : {e}")
            self.busy = False
            for child in self.children:
                child.disabled = False
            embed = self._base_embed(discord.Color.red())
            embed.add_field(name="🔁 Redémarrage", value=f"❌ Échec : `{e}`", inline=False)
            await safe_edit(self.message, embed=embed, view=self)

# ================================================================================
# 🧠 Cog principal
# ================================================================================
class BotControl(commands.Cog):
    """Commandes /bot_control et !bot_control — Panneau admin (git pull / reload / restart)."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _send_panel(self, channel: discord.abc.Messageable, author: discord.abc.User):
        view = ControlView(self.bot, author.id)
        embed = view._base_embed()
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
