# ────────────────────────────────────────────────────────────────────────────────
# 📌 motssecrets.py — Jeu des Mots Secrets multijoueur
# Objectif : Pendant 3 minutes, tout le monde peut proposer un mot secret pour gagner du Reiatsu
# Catégorie : Jeux
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
import json
import asyncio
import logging
from pathlib import Path
from datetime import datetime, timedelta

from utils.discord_utils import safe_send, safe_respond
from utils.init_db import get_conn

log = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────────────────────────
# 📂 Chargement des données JSON
# ────────────────────────────────────────────────────────────────────────────────
MOTS_PATH = Path("data/motssecrets.json")

def load_mots() -> list:
    """Charge la liste des mots secrets depuis le fichier JSON."""
    try:
        with MOTS_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log.exception("[motssecrets] Impossible de charger %s : %s", MOTS_PATH, e)
        return []

MOTS = load_mots()

# ────────────────────────────────────────────────────────────────────────────────
# 🗄️ Accès base de données locale
# ────────────────────────────────────────────────────────────────────────────────

def db_get_mots_trouves(user_id: int) -> list:
    """Récupère la liste des IDs de mots déjà trouvés par l'utilisateur."""
    try:
        conn   = get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT mots FROM mots_trouves WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return []
        return json.loads(row[0] or "[]")
    except Exception as e:
        log.exception("[motssecrets] Erreur lecture mots_trouves : %s", e)
        return []

def db_save_mot_trouve(user_id: int, username: str, mots_trouves: list):
    """Sauvegarde la liste mise à jour des mots trouvés."""
    try:
        conn   = get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM mots_trouves WHERE user_id = ?", (user_id,))
        exists = cursor.fetchone()

        if exists:
            cursor.execute("""
                UPDATE mots_trouves SET mots = ?, last_found_at = ?
                WHERE user_id = ?
            """, (json.dumps(mots_trouves), datetime.utcnow().isoformat(), user_id))
        else:
            cursor.execute("""
                INSERT INTO mots_trouves (user_id, username, mots, last_found_at)
                VALUES (?, ?, ?, ?)
            """, (user_id, username, json.dumps(mots_trouves), datetime.utcnow().isoformat()))

        conn.commit()
        conn.close()
    except Exception as e:
        log.exception("[motssecrets] Erreur sauvegarde mots_trouves : %s", e)

def db_add_reiatsu(user_id: int, username: str, points: int = 10):
    """Ajoute des points de Reiatsu à l'utilisateur."""
    try:
        conn   = get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT points FROM reiatsu WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()

        if row:
            cursor.execute(
                "UPDATE reiatsu SET points = ? WHERE user_id = ?",
                (row[0] + points, user_id)
            )
        else:
            cursor.execute(
                "INSERT INTO reiatsu (user_id, username, points) VALUES (?, ?, ?)",
                (user_id, username, points)
            )

        conn.commit()
        conn.close()
    except Exception as e:
        log.exception("[motssecrets] Erreur ajout reiatsu : %s", e)

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────

class MotsSecretsMulti(commands.Cog):
    """Jeu des Mots Secrets Multijoueur — Pendant 3 minutes, proposez des mots pour gagner du Reiatsu."""

    def __init__(self, bot: commands.Bot):
        self.bot          = bot
        self.active_games = {}  # channel_id : end_time

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction interne — normalisation
    # ────────────────────────────────────────────────────────────────────────────
    def normalize(self, text: str) -> str:
        return text.strip().lower()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction interne — démarrage du jeu
    # ────────────────────────────────────────────────────────────────────────────
    async def start_game(self, channel: discord.TextChannel):
        """Démarre un nouveau jeu de 3 minutes dans le channel."""
        if channel.id in self.active_games:
            await safe_send(channel, "⚠️ Un jeu est déjà en cours ici !")
            return

        self.active_games[channel.id] = datetime.utcnow() + timedelta(minutes=3)

        embed = discord.Embed(
            title="📝 Jeu des Mots Secrets !",
            description=(
                "💡 Il y a 100 mots secrets à trouver, un mot trouvé rapporte **10 Reiatsu** une fois par personne.\n"
                "Pendant **3 minutes**, proposez autant de mots que vous voulez en mettant `.` ou `*` devant.\n"
                "Exemple : `.exemple` ou `*exemple`\n\n"
                "🎯 Si le mot proposé n'est pas un mot secret, le bot ne répond pas.\n"
                "⚠️ Si c'est un mot que vous aviez déjà trouvé, le bot vous le signalera.\n\n"
                "Bonne chance !"
            ),
            color=discord.Color.green()
        )
        embed.set_footer(text="⏳ Le jeu se terminera automatiquement dans 3 minutes.")
        await safe_send(channel, embed=embed)

        async def stop_later():
            await asyncio.sleep(180)
            if channel.id in self.active_games:
                await safe_send(channel, "⏰ Le jeu des mots secrets est terminé !")
                del self.active_games[channel.id]

        asyncio.create_task(stop_later())

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction interne — vérification d'un mot proposé
    # ────────────────────────────────────────────────────────────────────────────
    async def handle_guess(self, message: discord.Message):
        """Vérifie si le mot proposé est un mot secret et attribue les points."""
        mot_propose = self.normalize(message.content[1:])
        mot_data    = [m for m in MOTS if self.normalize(m["mot"]) == mot_propose]

        if not mot_data:
            return  # mot inconnu, on ne répond pas

        mot_id   = mot_data[0]["id"]
        user_id  = message.author.id
        username = str(message.author)

        mots_trouves = db_get_mots_trouves(user_id)

        if mot_id in mots_trouves:
            await message.reply(f"⚠️ {message.author.mention}, tu as déjà trouvé ce mot secret !")
            return

        mots_trouves.append(mot_id)
        db_save_mot_trouve(user_id, username, mots_trouves)
        db_add_reiatsu(user_id, username, 10)

        await message.reply(
            f"✅ Bravo {message.author.mention} ! Tu as trouvé un mot secret et gagnes **10 Reiatsu** 🎉"
        )

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="motsecret",
        description="Pendant 3 minutes, cherchez l'un des 100 mots secrets pour gagner 10 Reiatsu."
    )
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_motsecret(self, interaction: discord.Interaction):
        await self.start_game(interaction.channel)
        await safe_respond(interaction, "✅ Jeu des mots secrets lancé dans ce salon !", ephemeral=True)

    @slash_motsecret.error
    async def slash_motsecret_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            await safe_respond(interaction, f"⏳ Attends encore {error.retry_after:.1f}s.", ephemeral=True)
        else:
            log.exception("[/motsecret] Erreur non gérée : %s", error)
            await safe_respond(interaction, "❌ Une erreur est survenue.", ephemeral=True)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(
        name="motsecret",
        aliases=["motssecrets", "ms"],
        help="Pendant 3 minutes, cherchez l'un des 100 mots secrets pour gagner 10 Reiatsu."
    )
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_motsecret(self, ctx: commands.Context):
        await self.start_game(ctx.channel)

    @prefix_motsecret.error
    async def prefix_motsecret_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.CommandOnCooldown):
            await safe_send(ctx.channel, f"⏳ Attends encore {error.retry_after:.1f}s.")
        else:
            log.exception("[!motsecret] Erreur non gérée : %s", error)
            await safe_send(ctx.channel, "❌ Une erreur est survenue.")

    # ────────────────────────────────────────────────────────────────────────────
    # 🎧 Événement — Proposition de mot
    # ────────────────────────────────────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if message.channel.id not in self.active_games:
            return
        if not (message.content.startswith(".") or message.content.startswith("*")):
            return
        if not message.content[1:].strip():
            return  # ignore "." ou "*" seuls
        await self.handle_guess(message)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = MotsSecretsMulti(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Jeux"
    await bot.add_cog(cog)
