# ────────────────────────────────────────────────────────────────────────────────
# 📌 rpg.py — Commande /rpg et !rpg
# Objectif : RPG Soul Society (profil, combat et boss)
# Catégorie : Bleach
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta
import sqlite3
import json
import os

from utils.rpg_utils import create_profile_if_not_exists
from utils.rpg_zones import change_zone
from utils.rpg_embeds import menu_embed, profile_embed
from utils.discord_utils import safe_send, safe_respond
from utils.rpg_combat import run_combat

# ────────────────────────────────────────────────────────────────────────────────
# 🗄️ SQLite
# ────────────────────────────────────────────────────────────────────────────────
DB_PATH = os.path.join("database", "reiatsu.db")

def get_conn():
    return sqlite3.connect(DB_PATH)

def get_player(user_id: int) -> dict | None:
    """Retourne le profil RPG du joueur ou None."""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM rpg_players WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None
    columns = [desc[0] for desc in cursor.description]
    conn.close()
    data = dict(zip(columns, row))
    # Désérialisation des champs JSON
    for field in ("stats", "cooldowns", "unlocked_zones", "inventory"):
        if field in data and isinstance(data[field], str):
            try:
                data[field] = json.loads(data[field])
            except Exception:
                data[field] = {} if field != "unlocked_zones" else ["1"]
    return data

def update_player(user_id: int, fields: dict):
    """Met à jour les champs d'un joueur RPG (sérialise les dicts/lists en JSON)."""
    if not fields:
        return
    serialized = {}
    for k, v in fields.items():
        serialized[k] = json.dumps(v) if isinstance(v, (dict, list)) else v

    set_clause = ", ".join(f"{k} = ?" for k in serialized)
    values = list(serialized.values()) + [user_id]

    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(f"UPDATE rpg_players SET {set_clause} WHERE user_id = ?", values)
    conn.commit()
    conn.close()

# ────────────────────────────────────────────────────────────────────────────────
# 📂 Chargement des ennemis
# ────────────────────────────────────────────────────────────────────────────────
with open("data/enemies.json", "r", encoding="utf-8") as f:
    ENEMIES = json.load(f)

# ────────────────────────────────────────────────────────────────────────────────
# ⚙️ Constantes
# ────────────────────────────────────────────────────────────────────────────────
CD_DURATIONS = {
    "combat": 300,   # 5 minutes
    "boss":   3600,  # 1 heure
}

VALID_ACTIONS = {"profil", "combat", "boss", "zone", "map", "classe"}

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class RPG(commands.Cog):
    """Commande /rpg et !rpg — RPG Soul Society"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(name="rpg", description="Affiche le RPG Soul Society, profil, combat et boss")
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_rpg(self, interaction: discord.Interaction, action: str = None, zone_target: str = None):
        await interaction.response.defer()
        await self.process_rpg(interaction.user.id, interaction, action, zone_target, is_slash=True)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="rpg", help="RPG Soul Society — profil, combat, boss, zone, classe")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_rpg(self, ctx: commands.Context, action: str = None, zone_target: str = None):
        await self.process_rpg(ctx.author.id, ctx, action, zone_target, is_slash=False)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction principale
    # ────────────────────────────────────────────────────────────────────────────
    async def process_rpg(self, user_id: int, ctx, action: str | None, zone_target: str | None = None, is_slash: bool = False):
        username = ctx.user.name if is_slash else ctx.author.name

        # Créer le profil si absent
        await create_profile_if_not_exists(user_id, username)

        # Charger le profil depuis SQLite
        player_data = get_player(user_id)
        if not player_data:
            return await self._send(ctx, is_slash, "❌ Impossible de charger ton profil.")

        stats          = player_data.get("stats") or {}
        cooldowns      = player_data.get("cooldowns") or {}
        zone           = str(player_data.get("zone", "1"))
        unlocked_zones = player_data.get("unlocked_zones") or ["1"]
        now            = datetime.utcnow()

        # ── Aucune action → menu ──────────────────────────────────────────────
        if not action:
            return await self._send(ctx, is_slash, menu_embed())

        action = action.lower()

        # ── Action inconnue ───────────────────────────────────────────────────
        if action not in VALID_ACTIONS:
            return await self._send(
                ctx, is_slash,
                f"❓ Action inconnue. Disponibles : `{'` | `'.join(VALID_ACTIONS)}`"
            )

        # ── Profil ────────────────────────────────────────────────────────────
        if action == "profil":
            return await self._send(ctx, is_slash, profile_embed(player_data, stats, cooldowns, now))

        # ── Zones / map ───────────────────────────────────────────────────────
        if action in ("zone", "map"):
            send_fn = self._make_send(ctx, is_slash)
            return await change_zone(zone_target, unlocked_zones, zone, user_id, send_fn)

        # ── Choix de classe ───────────────────────────────────────────────────
        if action == "classe":
            from utils.rpg_choose_class import choose_class
            return await choose_class(ctx, user_id, is_slash=is_slash)

        # ── Combat / boss ─────────────────────────────────────────────────────
        if action in ("combat", "boss"):
            # Vérification cooldown
            last_str = cooldowns.get(action, "1970-01-01T00:00:00")
            try:
                last = datetime.fromisoformat(last_str)
            except ValueError:
                last = datetime.min

            remaining = CD_DURATIONS[action] - (now - last).total_seconds()
            if remaining > 0:
                return await self._send(
                    ctx, is_slash,
                    f"⏳ **{action.upper()}** en cooldown — reviens dans `{str(timedelta(seconds=int(remaining)))}`."
                )

            # Mise à jour du cooldown
            cooldowns[action] = now.isoformat()
            update_player(user_id, {"cooldowns": cooldowns})

            # Lancement du combat
            send_fn = self._make_send(ctx, is_slash)
            is_boss = (action == "boss")
            await run_combat(user_id, is_boss, zone, stats, cooldowns, send_fn, ENEMIES, player_data)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔧 Helpers d'envoi
    # ────────────────────────────────────────────────────────────────────────────
    async def _send(self, ctx, is_slash: bool, content, view=None):
        """Envoie un message (embed ou texte) selon le contexte."""
        if isinstance(content, discord.Embed):
            if is_slash:
                return await ctx.followup.send(embed=content, view=view)
            return await ctx.send(embed=content, view=view)
        if is_slash:
            return await safe_respond(ctx, content)
        return await safe_send(ctx.channel, content)

    def _make_send(self, ctx, is_slash: bool):
        """Retourne une fonction send prête à l'emploi pour les utils externes."""
        async def send(content, view=None):
            return await self._send(ctx, is_slash, content, view)
        return send

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = RPG(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Bleach"
    await bot.add_cog(cog)
