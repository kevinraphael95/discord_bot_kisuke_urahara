# ================================================================================
# 📌 soundboard.py — Soundboard moderne (queue, autocomplete, event-driven)
# Objectif : Jouer des sons dans un salon vocal via menus interactifs
# Catégorie : Audio
# Accès : Tous
# Cooldown : géré globalement par bot.py
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
import asyncio
from collections import deque

from utils.discord_utils import safe_send, safe_edit, safe_respond, safe_followup

# ================================================================================
# ⚙️ Configuration
# ================================================================================
PLAY_COOLDOWN = 5.0       # anti-spam clic (secondes)
COOLDOWN_CLEANUP = 300.0  # purge auto du cache cooldowns

# ================================================================================
# 📂 Scan automatique du dossier sounds/
# ================================================================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SOUNDS_DIR = os.path.join(BASE_DIR, "sounds")
AUDIO_EXTENSIONS = (".mp3", ".ogg", ".wav", ".m4a", ".flac", ".opus")

def scan_sounds() -> dict:
    """Scanne le dossier sounds/ et retourne {catégorie: {nom: chemin}}."""
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

def find_sound(sound_name: str):
    """Retourne (catégorie, nom, chemin) ou None."""
    data = scan_sounds()
    for cat, sounds in data.items():
        for name, path in sounds.items():
            if name.lower() == sound_name.lower():
                return cat, name, path
    return None

def all_sound_names() -> list[str]:
    """Liste plate de tous les noms de sons (pour autocomplete)."""
    data = scan_sounds()
    names = []
    for sounds in data.values():
        names.extend(sounds.keys())
    return sorted(names)

# ================================================================================
# ⏱️ Gestionnaire de cooldowns par utilisateur
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
        if now - self._last_cleanup > COOLDOWN_CLEANUP:
            cutoff = now - self.delay
            self._last = {uid: t for uid, t in self._last.items() if t > cutoff}
            self._last_cleanup = now
        last = self._last.get(user_id, 0)
        return max(0.0, self.delay - (now - last))

    def update(self, user_id: int):
        self._last[user_id] = time.time()

# ================================================================================
# 🎵 Gestionnaire de file d'attente par serveur
# ================================================================================
class GuildQueue:
    """Une queue par guilde : (chemin, nom_affiche, demandeur_id)."""
    def __init__(self):
        self.queue: deque[tuple[str, str, int]] = deque()
        self.current: tuple[str, str, int] | None = None

    def add(self, path: str, name: str, user_id: int):
        self.queue.append((path, name, user_id))

    def pop_next(self):
        if self.queue:
            self.current = self.queue.popleft()
            return self.current
        self.current = None
        return None

    def clear(self):
        self.queue.clear()
        self.current = None

    def __len__(self):
        return len(self.queue)

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
        # ⚡ Defer en premier (anti-timeout Discord)
        await interaction.response.defer(ephemeral=True)

        cog: Soundboard = interaction.client.get_cog("Soundboard")
        if cog is None:
            await safe_followup(interaction, "❌ Erreur interne (cog introuvable).", ephemeral=True)
            return

        # ⏱️ Cooldown anti-spam
        remaining = cog.play_cooldowns.check(interaction.user.id)
        if remaining > 0:
            await safe_followup(
                interaction,
                f"⏱️ Doucement ! Attends encore **{int(remaining) + 1}s**.",
                ephemeral=True
            )
            return

        # 🔍 Vérifications
        sound_name = self.values[0]
        sound_path = self.parent_view.data[self.parent_view.category][sound_name]

        if not os.path.isfile(sound_path):
            await safe_followup(interaction, f"❌ Fichier introuvable : `{sound_path}`", ephemeral=True)
            return

        member = interaction.user
        if not isinstance(member, discord.Member) or not member.voice or not member.voice.channel:
            await safe_followup(interaction, "❌ Tu dois être dans un salon vocal.", ephemeral=True)
            return

        cog.play_cooldowns.update(interaction.user.id)
        result = await cog.enqueue_and_play(interaction.guild, member, sound_path, sound_name)
        await safe_followup(interaction, result, ephemeral=True)

class StopButton(Button):
    def __init__(self, parent_view: SoundSelectView):
        super().__init__(label="Stop", emoji="⏹️", style=discord.ButtonStyle.danger)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        cog: Soundboard = interaction.client.get_cog("Soundboard")
        vc = interaction.guild.voice_client
        if cog:
            cog.queues[interaction.guild.id] = GuildQueue()
        if vc and (vc.is_playing() or vc.is_paused()):
            vc.stop()
            await safe_followup(interaction, "⏹️ Stop + queue vidée.", ephemeral=True)
        else:
            await safe_followup(interaction, "❌ Rien en cours.", ephemeral=True)

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
    Commandes /play, /soundboard, /queue, /skip, /stop, /leave — Soundboard moderne.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.play_cooldowns = CooldownManager(PLAY_COOLDOWN)
        self.queues: dict[int, GuildQueue] = {}

    # ----------------------------------------------------------------------------
    # 🔹 Helpers internes
    # ----------------------------------------------------------------------------
    def get_queue(self, guild_id: int) -> GuildQueue:
        if guild_id not in self.queues:
            self.queues[guild_id] = GuildQueue()
        return self.queues[guild_id]

    async def ensure_voice(self, guild: discord.Guild, member: discord.Member) -> discord.VoiceClient | None:
        vc = guild.voice_client
        try:
            if vc is None:
                vc = await member.voice.channel.connect()
            elif vc.channel != member.voice.channel:
                await vc.move_to(member.voice.channel)
        except Exception as e:
            print(f"[SOUNDBOARD] Erreur connexion vocal : {e}")
            return None
        return vc

    def play_next(self, guild: discord.Guild):
        vc = guild.voice_client
        if vc is None:
            return
        queue = self.get_queue(guild.id)
        nxt = queue.pop_next()
        if nxt is None:
            return
        path, name, _ = nxt
        try:
            source = discord.FFmpegPCMAudio(path)
            vc.play(source, after=lambda err: self._after_play(guild, err))
        except Exception as e:
            print(f"[SOUNDBOARD] Erreur lecture {name} : {e}")

    def _after_play(self, guild: discord.Guild, err):
        if err:
            print(f"[SOUNDBOARD] Erreur audio : {err}")
        # ✅ Relance proprement la boucle async
        asyncio.run_coroutine_threadsafe(self._play_next_async(guild), self.bot.loop)

    async def _play_next_async(self, guild: discord.Guild):
        self.play_next(guild)

    async def enqueue_and_play(
        self,
        guild: discord.Guild,
        member: discord.Member,
        sound_path: str,
        sound_name: str
    ) -> str:
        vc = await self.ensure_voice(guild, member)
        if vc is None:
            return "❌ Impossible de rejoindre le vocal."

        queue = self.get_queue(guild.id)

        if vc.is_playing() or vc.is_paused():
            queue.add(sound_path, sound_name, member.id)
            return f"➕ **{sound_name}** ajouté à la queue (position {len(queue)})"

        queue.add(sound_path, sound_name, member.id)
        self.play_next(guild)
        return f"🎵 **{sound_name}** en cours de lecture"

    # ============================================================================
    # 🔹 Commande SLASH — /play <nom> (autocomplete)
    # ============================================================================
    @app_commands.command(name="play", description="Joue un son par son nom.")
    @app_commands.describe(nom="Nom du son à jouer")
    async def slash_play(self, interaction: discord.Interaction, nom: str):
        await interaction.response.defer(ephemeral=True)

        member = interaction.user
        if not isinstance(member, discord.Member) or not member.voice or not member.voice.channel:
            await safe_followup(interaction, "❌ Rejoins un salon vocal d'abord.", ephemeral=True)
            return

        found = find_sound(nom)
        if not found:
            await safe_followup(interaction, f"❌ Son `{nom}` introuvable.", ephemeral=True)
            return

        cat, name, path = found

        remaining = self.play_cooldowns.check(member.id)
        if remaining > 0:
            await safe_followup(
                interaction,
                f"⏱️ Doucement ! Attends **{int(remaining) + 1}s**.",
                ephemeral=True
            )
            return
        self.play_cooldowns.update(member.id)

        result = await self.enqueue_and_play(interaction.guild, member, path, name)
        await safe_followup(interaction, result, ephemeral=True)

    @slash_play.autocomplete("nom")
    async def play_autocomplete(self, interaction: discord.Interaction, current: str):
        names = all_sound_names()
        current_low = current.lower()
        matches = [n for n in names if current_low in n.lower()][:25]
        return [app_commands.Choice(name=n, value=n) for n in matches]

    # ============================================================================
    # 🔹 Commande SLASH — /soundboard (menu catégories)
    # ============================================================================
    @app_commands.command(name="soundboard", description="Ouvre le menu des sons.")
    async def slash_soundboard(self, interaction: discord.Interaction):
        await interaction.response.defer()
        data = scan_sounds()
        if not data:
            await safe_followup(
                interaction,
                f"❌ Aucun son trouvé.\nDépose des fichiers dans `{SOUNDS_DIR}/<catégorie>/`.",
                ephemeral=True
            )
            return
        view = CategorySelectView(self.bot, data)
        msg = await interaction.channel.send("🎵 **Soundboard** — Choisis une catégorie :", view=view)
        view.message = msg
        await interaction.delete_original_response()

    # ============================================================================
    # 🔹 Commande SLASH — /queue (voir la file)
    # ============================================================================
    @app_commands.command(name="queue", description="Affiche la file d'attente.")
    async def slash_queue(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        queue = self.get_queue(interaction.guild.id)

        embed = discord.Embed(title="🎵 File d'attente", color=discord.Color.blue())
        if queue.current:
            _, name, uid = queue.current
            embed.add_field(name="▶️ En cours", value=f"**{name}** (par <@{uid}>)", inline=False)

        if len(queue) == 0:
            embed.add_field(name="⏳ À venir", value="*File vide*", inline=False)
        else:
            lines = []
            for i, (_, name, uid) in enumerate(list(queue.queue)[:10], 1):
                lines.append(f"`{i}.` **{name}** — <@{uid}>")
            if len(queue) > 10:
                lines.append(f"*… et {len(queue) - 10} autres*")
            embed.add_field(name=f"⏳ À venir ({len(queue)})", value="\n".join(lines), inline=False)

        await safe_followup(interaction, embed=embed, ephemeral=True)

    # ============================================================================
    # 🔹 Commande SLASH — /skip (passe au suivant)
    # ============================================================================
    @app_commands.command(name="skip", description="Passe au son suivant.")
    async def slash_skip(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        vc = interaction.guild.voice_client
        if not vc or not vc.is_playing():
            await safe_followup(interaction, "❌ Rien en cours.", ephemeral=True)
            return
        vc.stop()
        await safe_followup(interaction, "⏭️ Son passé.", ephemeral=True)

    # ============================================================================
    # 🔹 Commande SLASH — /stop (stop + vide queue)
    # ============================================================================
    @app_commands.command(name="stop", description="Arrête la lecture et vide la file.")
    async def slash_stop(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        self.queues[interaction.guild.id] = GuildQueue()
        vc = interaction.guild.voice_client
        if vc and (vc.is_playing() or vc.is_paused()):
            vc.stop()
            await safe_followup(interaction, "⏹️ Stop + file vidée.", ephemeral=True)
        else:
            await safe_followup(interaction, "❌ Rien en cours.", ephemeral=True)

    # ============================================================================
    # 🔹 Commande SLASH — /leave (quitter vocal)
    # ============================================================================
    @app_commands.command(name="leave", description="Quitte le salon vocal.")
    async def slash_leave(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        self.queues[interaction.guild.id] = GuildQueue()
        vc = interaction.guild.voice_client
        if vc:
            await vc.disconnect()
            await safe_followup(interaction, "👋 Déconnecté.", ephemeral=True)
        else:
            await safe_followup(interaction, "❌ Pas dans un vocal.", ephemeral=True)

    # ============================================================================
    # 🔹 Commande SLASH — /reload_sounds (admin)
    # ============================================================================
    @app_commands.command(name="reload_sounds", description="Rescanne le dossier sounds/ (admin).")
    @app_commands.default_permissions(manage_guild=True)
    async def slash_reload(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        data = scan_sounds()
        total = sum(len(s) for s in data.values())
        await safe_followup(
            interaction,
            f"✅ Rescan terminé : **{len(data)}** catégorie(s), **{total}** son(s).",
            ephemeral=True
        )

    # ============================================================================
    # 🎧 Event — Déconnexion auto si plus personne dans le vocal
    # ============================================================================
    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState
    ):
        if member.bot:
            return
        guild = member.guild
        vc = guild.voice_client
        if not vc or not vc.channel:
            return

        if before.channel and before.channel == vc.channel and after.channel != vc.channel:
            humans = [m for m in vc.channel.members if not m.bot]
            if not humans:
                self.queues[guild.id] = GuildQueue()
                await asyncio.sleep(2)
                vc = guild.voice_client
                if vc and not [m for m in vc.channel.members if not m.bot]:
                    await vc.disconnect()
                    print(f"[SOUNDBOARD] Déconnexion auto (vide) — {guild.name}")

# ================================================================================
# 🔌 Setup du Cog
# ================================================================================
async def setup(bot: commands.Bot):
    cog = Soundboard(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Fun&Random"
    await bot.add_cog(cog)
