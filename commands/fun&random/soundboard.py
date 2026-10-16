# ================================================================================
# 📌 soundboard.py
# Objectif : Jouer des sons dans un salon vocal via menus interactifs
# Catégorie : Audio
# Accès : Tous
# Cooldown : 1 min / user (commande) + 30s / user (lecture)
# ================================================================================

# ================================================================================
# 📦 Imports nécessaires
# ================================================================================
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Select, Button
import os
import time

from utils.discord_utils import safe_send, safe_edit, safe_respond

# ================================================================================
# ⏱️ Configuration des cooldowns (en secondes)
# ================================================================================
COMMAND_COOLDOWN = 60.0   # /soundboard et !soundboard
PLAY_COOLDOWN = 30.0      # clic sur un son
COOLDOWN_CLEANUP = 300.0  # purge les entrées > 5 min

# ================================================================================
# 📂 Scan automatique du dossier sounds/
# ================================================================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOUNDS_DIR = os.path.join(BASE_DIR, "sounds")
AUDIO_EXTENSIONS = (".mp3", ".ogg", ".wav", ".m4a", ".flac", ".opus")

def scan_sounds():
    """
    Scanne le dossier sounds/ et retourne un dict :
    {
        "Memes": {"rickroll": "chemin/absolu/rickroll.mp3", "bruh": ...},
        "Effets": {"applause": ..., "drumroll": ...}
    }
    """
    data = {}
    if not os.path.isdir(SOUNDS_DIR):
        print(f"[SOUNDBOARD] Dossier introuvable : {SOUNDS_DIR}")
        return data

    for category in sorted(os.listdir(SOUNDS_DIR)):
        cat_path = os.path.join(SOUNDS_DIR, category)
        if not os.path.isdir(cat_path):
            continue

        sounds = {}
        for filename in sorted(os.listdir(cat_path)):
            if not filename.lower().endswith(AUDIO_EXTENSIONS):
                continue
            name = os.path.splitext(filename)[0]
            sounds[name] = os.path.join(cat_path, filename)

        if sounds:
            data[category] = sounds

    return data

# ================================================================================
# ⏱️ Gestionnaire de cooldowns par utilisateur (anti-spam lecture)
# ================================================================================
class CooldownManager:
    """Gère des cooldowns simples par user_id avec purge automatique."""
    def __init__(self, delay: float):
        self.delay = delay
        self._last: dict[int, float] = {}
        self._last_cleanup = time.time()

    def check(self, user_id: int) -> float:
        """Retourne le temps restant (0 si OK)."""
        now = time.time()

        # Purge périodique pour éviter la fuite mémoire
        if now - self._last_cleanup > COOLDOWN_CLEANUP:
            cutoff = now - self.delay
            self._last = {uid: t for uid, t in self._last.items() if t > cutoff}
            self._last_cleanup = now

        last = self._last.get(user_id, 0)
        remaining = self.delay - (now - last)
        return max(0.0, remaining)

    def update(self, user_id: int):
        self._last[user_id] = time.time()

# ================================================================================
# 🎛️ UI — Premier menu (catégories)
# ================================================================================
class CategorySelectView(View):
    def __init__(self, bot, data):
        super().__init__(timeout=120)
        self.bot = bot
        self.data = data
        self.message = None
        self.add_item(CategorySelect(self))

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message:
            await safe_edit(self.message, view=self)

class CategorySelect(Select):
    def __init__(self, parent_view: CategorySelectView):
        self.parent_view = parent_view
        options = [
            discord.SelectOption(
                label=cat[:100],
                value=cat,
                emoji="📁",
                description=f"{len(sounds)} son(s)"
            )
            for cat, sounds in list(parent_view.data.items())[:25]
        ]
        super().__init__(placeholder="Choisis une catégorie de sons", options=options)

    async def callback(self, interaction: discord.Interaction):
        category = self.values[0]
        new_view = SoundSelectView(self.parent_view.bot, self.parent_view.data, category)
        new_view.message = interaction.message
        await safe_edit(
            interaction.message,
            content=f"📁 Catégorie : **{category}**\nChoisis un son à jouer :",
            embed=None,
            view=new_view
        )

# ================================================================================
# 🎛️ UI — Deuxième menu (sons) + boutons Stop / Retour
# ================================================================================
class SoundSelectView(View):
    def __init__(self, bot, data, category):
        super().__init__(timeout=120)
        self.bot = bot
        self.data = data
        self.category = category
        self.message = None
        self.add_item(SoundSelect(self))
        self.add_item(StopButton(self))
        self.add_item(BackButton(self))

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message:
            await safe_edit(self.message, view=self)

class SoundSelect(Select):
    def __init__(self, parent_view: SoundSelectView):
        self.parent_view = parent_view
        sounds = parent_view.data[parent_view.category]
        options = [
            discord.SelectOption(
                label=name[:100],
                value=name,
                emoji="🎵"
            )
            for name in list(sounds.keys())[:25]
        ]
        super().__init__(placeholder="Choisis un son", options=options)

    async def callback(self, interaction: discord.Interaction):
        # ---------------------------------------------------------------
        # ⏱️ Cooldown anti-spam (par user)
        # ---------------------------------------------------------------
        cog: Soundboard = interaction.client.get_cog("Soundboard")
        if cog is None:
            await safe_respond(interaction, "❌ Erreur interne (cog introuvable).", ephemeral=True)
            return

        remaining = cog.play_cooldowns.check(interaction.user.id)
        if remaining > 0:
            await safe_respond(
                interaction,
                f"⏱️ Doucement ! Attends encore **{int(remaining) + 1}s** avant de relancer un son.",
                ephemeral=True
            )
            return

        # ---------------------------------------------------------------
        # 🔍 Vérifications
        # ---------------------------------------------------------------
        sound_name = self.values[0]
        sound_path = self.parent_view.data[self.parent_view.category][sound_name]

        if not os.path.isfile(sound_path):
            await safe_respond(interaction, f"❌ Fichier introuvable : `{sound_path}`", ephemeral=True)
            return

        member = interaction.user
        if not isinstance(member, discord.Member) or not member.voice or not member.voice.channel:
            await safe_respond(interaction, "❌ Tu dois être dans un salon vocal.", ephemeral=True)
            return

        # ---------------------------------------------------------------
        # 🔊 Connexion / déplacement
        # ---------------------------------------------------------------
        voice_client = interaction.guild.voice_client
        try:
            if voice_client is None:
                voice_client = await member.voice.channel.connect()
            elif voice_client.channel != member.voice.channel:
                await voice_client.move_to(member.voice.channel)
        except Exception as e:
            await safe_respond(interaction, f"❌ Impossible de rejoindre le vocal : `{e}`", ephemeral=True)
            return

        # ---------------------------------------------------------------
        # 🎵 Lecture
        # ---------------------------------------------------------------
        try:
            if voice_client.is_playing():
                voice_client.stop()
            source = discord.FFmpegPCMAudio(sound_path)
            voice_client.play(
                source,
                after=lambda err: print(f"[AUDIO] Erreur : {err}") if err else None
            )
        except Exception as e:
            await safe_respond(interaction, f"❌ Erreur lecture : `{e}`", ephemeral=True)
            return

        # ---------------------------------------------------------------
        # ✅ Cooldown appliqué seulement si la lecture a réussi
        # ---------------------------------------------------------------
        cog.play_cooldowns.update(interaction.user.id)

        embed = discord.Embed(
            title="🎵 Lecture en cours",
            description=f"**{sound_name}** dans {member.voice.channel.mention}",
            color=discord.Color.green()
        )
        embed.set_footer(text=f"Catégorie : {self.parent_view.category} • Cooldown : {int(PLAY_COOLDOWN)}s")
        await safe_respond(interaction, embed=embed, ephemeral=True)

class StopButton(Button):
    def __init__(self, parent_view: SoundSelectView):
        super().__init__(label="Stop", emoji="⏹️", style=discord.ButtonStyle.danger)

    async def callback(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc and vc.is_playing():
            vc.stop()
            await safe_respond(interaction, "⏹️ Son arrêté.", ephemeral=True)
        else:
            await safe_respond(interaction, "❌ Aucun son en cours.", ephemeral=True)

class BackButton(Button):
    def __init__(self, parent_view: SoundSelectView):
        super().__init__(label="Retour", emoji="↩️", style=discord.ButtonStyle.secondary)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        new_view = CategorySelectView(self.parent_view.bot, self.parent_view.data)
        new_view.message = interaction.message
        await safe_edit(
            interaction.message,
            content="🎵 **Soundboard** — Choisis une catégorie :",
            embed=None,
            view=new_view
        )

# ================================================================================
# 🧠 Cog principal
# ================================================================================
class Soundboard(commands.Cog):
    """
    Commande /soundboard et !soundboard — Jouer des sons dans un salon vocal.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.play_cooldowns = CooldownManager(PLAY_COOLDOWN)

    async def _send_menu(self, channel: discord.abc.Messageable):
        data = scan_sounds()
        if not data:
            await safe_send(
                channel,
                f"❌ Aucun son trouvé.\nDépose des fichiers audio dans `{SOUNDS_DIR}/<catégorie>/`.",
            )
            return
        view = CategorySelectView(self.bot, data)
        view.message = await safe_send(
            channel,
            "🎵 **Soundboard** — Choisis une catégorie :",
            view=view
        )

    # ============================================================================
    # 🔹 Gestion des erreurs de cooldown (slash)
    # ============================================================================
    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            await safe_respond(
                interaction,
                f"⏱️ Doucement ! Réessaie dans **{int(error.retry_after) + 1}s**.",
                ephemeral=True
            )
            return
        # Autres erreurs : log
        print(f"[SOUNDBOARD] Erreur slash : {error}")

    # ============================================================================
    # 🔹 Gestion des erreurs de cooldown (prefix)
    # ============================================================================
    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.CommandOnCooldown):
            await safe_send(ctx.channel, f"⏱️ {ctx.author.mention}, réessaie dans **{int(error.retry_after) + 1}s**.")
            return
        print(f"[SOUNDBOARD] Erreur prefix : {error}")

    # ============================================================================
    # 🔹 Commande SLASH — 1 min / user
    # ============================================================================
    @app_commands.command(name="soundboard", description="Ouvre le soundboard pour jouer des sons.")
    @app_commands.checks.cooldown(rate=1, per=COMMAND_COOLDOWN, key=lambda i: i.user.id)
    async def slash_soundboard(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self._send_menu(interaction.channel)
        await interaction.delete_original_response()

    # ============================================================================
    # 🔹 Commande PREFIX — 1 min / user
    # ============================================================================
    @commands.command(name="soundboard")
    @commands.cooldown(1, COMMAND_COOLDOWN, commands.BucketType.user)
    async def prefix_soundboard(self, ctx: commands.Context):
        await self._send_menu(ctx.channel)

    # ============================================================================
    # 🔹 Commande /leave
    # ============================================================================
    @app_commands.command(name="leave", description="Fait quitter le bot du salon vocal.")
    async def slash_leave(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc:
            await vc.disconnect()
            await safe_respond(interaction, "👋 Déconnecté du vocal.", ephemeral=True)
        else:
            await safe_respond(interaction, "❌ Je ne suis dans aucun salon vocal.", ephemeral=True)

    # ============================================================================
    # 🔹 Commande /reload_sounds (admin)
    # ============================================================================
    @app_commands.command(name="reload_sounds", description="Rescanne le dossier sounds/ (admin).")
    @app_commands.default_permissions(manage_guild=True)
    async def slash_reload(self, interaction: discord.Interaction):
        data = scan_sounds()
        total = sum(len(s) for s in data.values())
        await safe_respond(
            interaction,
            f"✅ Rescan terminé : **{len(data)}** catégorie(s), **{total}** son(s).",
            ephemeral=True
        )

# ================================================================================
# 🔌 Setup du Cog
# ================================================================================
async def setup(bot: commands.Bot):
    cog = Soundboard(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Audio"
    await bot.add_cog(cog)
