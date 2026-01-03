# ────────────────────────────────────────────────────────────────────────────────
# 📌 bot.py — Script principal du bot Discord
# Objectif : Initialisation, gestion des commandes et événements du bot
# Catégorie : Général
# Accès : Public
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 🟢 Serveur Keep-Alive (Render)
# ────────────────────────────────────────────────────────────────────────────────
from tasks.keep_alive import keep_alive

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Modules standards
# ────────────────────────────────────────────────────────────────────────────────
import os
import json
import uuid
import random
from datetime import datetime, timezone
import asyncio

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Modules tiers
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands
from dotenv import load_dotenv
from dateutil import parser

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Modules internes
# ────────────────────────────────────────────────────────────────────────────────
from utils.supabase_client import supabase
from utils.discord_utils import safe_send  # ✅ Utilitaires anti-429

# ────────────────────────────────────────────────────────────────────────────────
# 🔧 Initialisation de l’environnement
# ────────────────────────────────────────────────────────────────────────────────
os.chdir(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
COMMAND_PREFIX = os.getenv("COMMAND_PREFIX", "!!")
INSTANCE_ID = str(uuid.uuid4())

with open("instance_id.txt", "w") as f:
    f.write(INSTANCE_ID)

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

bot = commands.Bot(command_prefix=get_prefix, intents=intents, help_command=None)
bot.is_main_instance = False
bot.INSTANCE_ID = INSTANCE_ID
bot.supabase = supabase

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Chargement dynamique des commandes depuis /commands/*
# ────────────────────────────────────────────────────────────────────────────────
async def load_commands():
    for category in os.listdir("commands"):
        cat_path = os.path.join("commands", category)
        if os.path.isdir(cat_path):
            for filename in os.listdir(cat_path):
                if filename.endswith(".py"):
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
        if filename.endswith(".py") and filename != "keep_alive.py":
            path = f"tasks.{filename[:-3]}"
            try:
                await bot.load_extension(path)
                print(f"✅ Task loaded: {path}")
            except Exception as e:
                print(f"❌ Failed to load task {path}: {e}")

# ────────────────────────────────────────────────────────────────────────────────
# 🔁 Tâche de vérification continue du verrou
# ────────────────────────────────────────────────────────────────────────────────
async def verify_lock_loop():
    while True:
        await asyncio.sleep(10)
        try:
            lock = supabase.table("bot_lock").select("instance_id").eq("id", "bot_lock").execute()
            if lock.data and lock.data[0]["instance_id"] != INSTANCE_ID:
                print("🔴 Cette instance n'est plus maître. Fermeture propre du bot...")
                await bot.close()  # Ferme le bot correctement
                break  # Quitte la boucle sans tuer Python brutalement
        except Exception as e:
            print(f"⚠️ Erreur dans la vérification du verrou (ignorée) : {e}")


# ────────────────────────────────────────────────────────────────────────────────
# 🔔 On Ready : présence + verrouillage + surveillance
# ────────────────────────────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    print(f"✅ Connecté en tant que {bot.user.name}")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="Bleach"))

    try:
        now = datetime.now(timezone.utc).isoformat()
        supabase.table("bot_lock").upsert({
            "id": "bot_lock",
            "instance_id": INSTANCE_ID,
            "updated_at": now
        }).execute()

        print(f"🔐 Verrou mis à jour pour cette instance : {INSTANCE_ID}")
        bot.is_main_instance = True
        bot.loop.create_task(verify_lock_loop())
    except Exception as e:
        print(f"⚠️ Impossible de se connecter à Supabase : {e}")
        print("🔓 Aucune gestion de verrou — le bot démarre quand même.")
        bot.is_main_instance = True

# ────────────────────────────────────────────────────────────────────────────────
# 📩 Message reçu : réagir aux mots-clés et lancer les commandes
# ────────────────────────────────────────────────────────────────────────────────
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    try:
        lock = supabase.table("bot_lock").select("instance_id").eq("id", "bot_lock").execute()
        if lock.data and isinstance(lock.data, list):
            if lock.data and lock.data[0].get("instance_id") != INSTANCE_ID:
                return
    except Exception as e:
        print(f"⚠️ Erreur lors de la vérification du lock (ignorée) : {e}")

    if message.content.strip() in [f"<@!{bot.user.id}>", f"<@{bot.user.id}>"]:
        prefix = get_prefix(bot, message)
        embed = discord.Embed(
            title="Coucou !",
            description=(
                f"Bonjour ! Je suis **Kisuke Urahara**, un bot discord inspiré du manga Bleach.\n"
                f"• Utilise la commande `{prefix}help` pour avoir la liste des commandes du bot "
                f"ou `{prefix}help + le nom d'une commande` pour en avoir une description."
            ),
            color=discord.Color.red()
        )
        embed.set_footer(text="123")

        if bot.user.avatar:
            embed.set_thumbnail(url=bot.user.avatar.url)
        else:
            embed.set_thumbnail(url=bot.user.default_avatar.url)

        await safe_send(message.channel, embed=embed)
        return

    await bot.process_commands(message)

# ────────────────────────────────────────────────────────────────────────────────
# ❗ Gestion des erreurs de commandes
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
# 🚀 Lancement
# ────────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    keep_alive()  # lance Flask + self-ping

    async def start():
        await load_commands()
        await load_tasks()
        await bot.start(TOKEN)

    asyncio.run(start())




