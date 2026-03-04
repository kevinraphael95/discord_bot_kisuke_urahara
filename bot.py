# ────────────────────────────────────────────────────────────────────────────────
# 📌 bot.py — Script principal du bot Discord
# Objectif : Initialisation, gestion des commandes et événements du bot
# Catégorie : Général
# Accès : Public
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Modules standards
# ────────────────────────────────────────────────────────────────────────────────
import os
import asyncio
import threading
import logging

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Modules tiers
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands
from dotenv import load_dotenv
from discord import app_commands

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Modules internes
# ────────────────────────────────────────────────────────────────────────────────
from utils.discord_utils import safe_send, safe_respond
from utils.init_db import init_db
from utils.logger import init_logger

# ────────────────────────────────────────────────────────────────────────────────
# 🔧 Initialisation de l'environnement
# ────────────────────────────────────────────────────────────────────────────────
os.chdir(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

log = logging.getLogger(__name__)  # ✅ Ajout manquant

TOKEN = os.getenv("DISCORD_TOKEN")
COMMAND_PREFIX = os.getenv("COMMAND_PREFIX", "!!")
ADMIN_PORT = int(os.getenv("ADMIN_PORT", "5050"))

def get_prefix(bot, message):
    return COMMAND_PREFIX

# ────────────────────────────────────────────────────────────────────────────────
# ⚙️ Intents & Création du bot
# ────────────────────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
intents.guild_reactions = True
intents.dm_reactions = True

bot = commands.Bot(
    command_prefix=get_prefix,
    intents=intents,
    help_command=None
)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Chargement dynamique des commandes depuis /commands/*
# ────────────────────────────────────────────────────────────────────────────────
async def load_commands():
    for category in os.listdir("commands"):
        cat_path = os.path.join("commands", category)
        if os.path.isdir(cat_path):
            for filename in os.listdir(cat_path):
                if filename.endswith(".py") and filename != "__init__.py":
                    path = f"commands.{category}.{filename[:-3]}"
                    try:
                        await bot.load_extension(path)
                        print(f"✅ Loaded {path}")
                    except Exception as e:
                        print(f"❌ Failed to load {path}: {e}")

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Chargement dynamique des tasks depuis /tasks/*
# ────────────────────────────────────────────────────────────────────────────────
async def load_tasks():
    for filename in os.listdir("tasks"):
        if filename.endswith(".py") and filename != "__init__.py":
            path = f"tasks.{filename[:-3]}"
            try:
                await bot.load_extension(path)
                print(f"✅ Task loaded: {path}")
            except Exception as e:
                print(f"❌ Failed to load task {path}: {e}")

# ────────────────────────────────────────────────────────────────────────────────
# 🔔 On Ready : présence
# ────────────────────────────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    print(f"✅ Connecté en tant que {bot.user.name}")
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="Bleach"
        )
    )

# ────────────────────────────────────────────────────────────────────────────────
# 📩 Message reçu : réagir aux mots-clés et lancer les commandes
# ────────────────────────────────────────────────────────────────────────────────
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.content.strip() in (f"<@{bot.user.id}>", f"<@!{bot.user.id}>"):
        prefix = get_prefix(bot, message)
        embed = discord.Embed(
            title="Coucou !",
            description=(
                f"Bonjour ! Je suis **Kisuke Urahara**, un bot discord inspiré du manga Bleach.\n"
                f"• Utilise la commande `{prefix}help` pour avoir la liste des commandes du bot "
                f"ou `{prefix}help <commande>` pour en avoir une description."
            ),
            color=discord.Color.red()
        )

        if bot.user.avatar:
            embed.set_thumbnail(url=bot.user.avatar.url)
        else:
            embed.set_thumbnail(url=bot.user.default_avatar.url)

        await safe_send(message.channel, embed=embed)
        return

    await bot.process_commands(message)

# ────────────────────────────────────────────────────────────────────────────────
# ❗ Gestion des erreurs de commandes préfixe
# ────────────────────────────────────────────────────────────────────────────────
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        retry = round(error.retry_after, 1)
        await safe_send(ctx.channel, f"⏳ Cette commande est en cooldown. Réessaie dans `{retry}` secondes.")
    elif isinstance(error, commands.MissingPermissions):
        await safe_send(ctx.channel, "❌ Tu n'as pas les permissions pour cette commande.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await safe_send(ctx.channel, "⚠️ Il manque un argument à cette commande.")
    elif isinstance(error, commands.CommandNotFound):
        return
    else:
        raise error

# ────────────────────────────────────────────────────────────────────────────────
# ❗ Gestion des erreurs slash commands
# ────────────────────────────────────────────────────────────────────────────────
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandOnCooldown):
        await safe_respond(interaction, f"⏳ Attends encore {error.retry_after:.1f}s.", ephemeral=True)
    elif isinstance(error, app_commands.MissingPermissions):
        await safe_respond(interaction, "❌ Tu n'as pas les permissions pour cette commande.", ephemeral=True)
    else:
        log.exception("[slash] Erreur non gérée : %s", error)
        await safe_respond(interaction, "❌ Une erreur est survenue.", ephemeral=True)

# ────────────────────────────────────────────────────────────────────────────────
# 🚀 Lancement
# ────────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":

    init_logger()

    from admin_panel import run_admin, set_bot
    admin_thread = threading.Thread(target=run_admin, args=(ADMIN_PORT,), daemon=True)
    admin_thread.start()
    print(f"🌐 Panel admin lancé sur http://localhost:{ADMIN_PORT}")

    async def start():
        init_db()
        await load_commands()
        await load_tasks()
        set_bot(bot)
        await bot.start(TOKEN)

    asyncio.run(start())
