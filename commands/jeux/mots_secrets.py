# ────────────────────────────────────────────────────────────────────────────────
# 📌 motssecrets_multijoueur.py — Jeu des Mots Secrets multijoueur
# Objectif : Tout le monde peut proposer un mot secret pendant 3 minutes pour gagner du Reiatsu
# Catégorie : Jeux / Fun
# Accès : Tous
# Cooldown : 1 lancement / 5 secondes
# ────────────────────────────────────────────────────────────────────────────────

import discord
from discord.ext import commands, tasks
from utils.discord_utils import safe_send, safe_respond
from utils.supabase_client import supabase
import json
from pathlib import Path
from datetime import datetime, timedelta

MOTS_PATH = Path("data/motssecrets.json")
with MOTS_PATH.open("r", encoding="utf-8") as f:
    MOTS = json.load(f)

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class MotsSecretsMulti(commands.Cog):
    """
    🎮 Jeu des Mots Secrets Multijoueur — Tout le monde peut proposer un mot secret pendant 3 minutes
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active_games = {}  # channel_id : end_time

    def normalize(self, text: str) -> str:
        return text.strip().lower()

    async def start_game(self, channel: discord.TextChannel):
        """Démarre un nouveau jeu de 3 minutes dans le channel."""
        if channel.id in self.active_games:
            await safe_send(channel, "⚠️ Un jeu est déjà en cours ici !")
            return

        end_time = datetime.utcnow() + timedelta(minutes=3)
        self.active_games[channel.id] = end_time

        embed = discord.Embed(
            title="📝 Jeu des Mots Secrets !",
            description=(
                "💡 Pendant **3 minutes**, proposez vos mots secrets en commençant par `!` suivi du mot.\n"
                "Exemple : `!prout`\n\n"
                "🎯 Chaque mot correct vous fera gagner **10 Reiatsu** !\n"
                "⚠️ Si vous avez déjà trouvé le mot, le bot vous le signalera.\n"
                "Bonne chance !"
            ),
            color=discord.Color.green()
        )
        embed.set_footer(text="Le jeu se terminera automatiquement au bout de 3 minutes.")
        await safe_send(channel, embed=embed)

        # Lance une tâche pour arrêter le jeu automatiquement
        self.end_game_task.start(channel)

    @tasks.loop(seconds=5)
    async def end_game_task(self, channel):
        """Vérifie si le temps du jeu est écoulé."""
        if channel.id not in self.active_games:
            self.end_game_task.stop()
            return

        if datetime.utcnow() >= self.active_games[channel.id]:
            await safe_send(channel, "⏰ Le jeu des mots secrets est terminé !")
            del self.active_games[channel.id]
            self.end_game_task.stop()

    # ────────────────────────────────────────────────────────────
    @commands.command(name="startmots", help="Lance le jeu des mots secrets multijoueur pendant 3 minutes")
    async def start_mots_command(self, ctx: commands.Context):
        await self.start_game(ctx.channel)

    # ────────────────────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Ignore bot messages
        if message.author.bot:
            return

        # Vérifie si le jeu est actif dans ce channel
        if message.channel.id not in self.active_games:
            return

        # Vérifie si le message commence par "!" (proposition de mot)
        if not message.content.startswith("!"):
            return

        mot_propose = self.normalize(message.content[1:])

        # Vérifie si le mot est dans la liste
        mot_data = [m for m in MOTS if self.normalize(m["mot"]) == mot_propose]
        if not mot_data:
            return  # mot inconnu, on ne répond pas

        mot_id = mot_data[0]["id"]
        user_id = message.author.id
        username = str(message.author)

        # ── Récupère ou crée l'utilisateur dans mots_trouves
        user_data = supabase.table("mots_trouves").select("*").eq("user_id", user_id).execute()
        if user_data.data:
            mots_trouves = user_data.data[0].get("mots") or []
        else:
            mots_trouves = []

        if mot_id in mots_trouves:
            await message.reply(f"⚠️ {message.author.mention}, tu as déjà trouvé ce mot secret !")
            return

        # ── Ajoute le mot trouvé
        mots_trouves.append(mot_id)
        if user_data.data:
            supabase.table("mots_trouves").update({"mots": mots_trouves, "last_found_at": datetime.utcnow().isoformat()}).eq("user_id", user_id).execute()
        else:
            supabase.table("mots_trouves").insert({"user_id": user_id, "username": username, "mots": mots_trouves}).execute()

        # ── Donne 10 Reiatsu
        reiatsu_data = supabase.table("reiatsu").select("*").eq("user_id", user_id).execute()
        if reiatsu_data.data:
            points = reiatsu_data.data[0].get("points") or 0
            supabase.table("reiatsu").update({"points": points + 10}).eq("user_id", user_id).execute()
        else:
            supabase.table("reiatsu").insert({"user_id": user_id, "username": username, "points": 10}).execute()

        await message.reply(f"✅ Bravo {message.author.mention} ! Tu as trouvé un mot secret et gagnes **10 Reiatsu** !")

# ────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ───────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = MotsSecretsMulti(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Jeux"
    await bot.add_cog(cog)
