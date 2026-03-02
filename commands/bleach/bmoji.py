# ────────────────────────────────────────────────────────────────────────────────
# 📌 bmoji.py — Commande interactive !bmoji + /bmoji
# Objectif : Deviner quel personnage Bleach se cache derrière un emoji
# Catégorie : Bleach
# Accès : Public
# Cooldown : 1 utilisation / 5s / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands
from discord import app_commands
import json
import random
import os
import logging

from utils.discord_utils import safe_send, safe_respond
from utils.init_db import get_conn

log = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────────────────────────
# 📂 Chargement des données JSON
# ────────────────────────────────────────────────────────────────────────────────
DATA_JSON_PATH = os.path.join("data", "bleach_emojis.json")

def load_characters() -> list:
    """Charge les personnages et leurs emojis depuis le fichier JSON."""
    try:
        with open(DATA_JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log.exception("[bmoji] Impossible de charger %s : %s", DATA_JSON_PATH, e)
        return []

# ────────────────────────────────────────────────────────────────────────────────
# 🗄️ Accès base de données locale
# ────────────────────────────────────────────────────────────────────────────────

def db_valider_quete(user_id: int) -> int | None:
    """
    Vérifie si la quête 'bmoji' est déjà validée pour l'utilisateur.
    Si non, l'ajoute et incrémente le niveau.
    Retourne le nouveau niveau si la quête vient d'être validée, sinon None.
    """
    try:
        conn   = get_conn()
        cursor = conn.cursor()

        cursor.execute("SELECT quetes, niveau FROM reiatsu WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()

        if not row:
            conn.close()
            return None

        quetes = json.loads(row[0] or "[]")
        niveau = row[1] or 0

        if "bmoji" in quetes:
            conn.close()
            return None

        quetes.append("bmoji")
        new_lvl = niveau + 1
        cursor.execute(
            "UPDATE reiatsu SET quetes = ?, niveau = ? WHERE user_id = ?",
            (json.dumps(quetes), new_lvl, user_id)
        )
        conn.commit()
        conn.close()
        return new_lvl

    except Exception as e:
        log.exception("[bmoji] Erreur validation quête SQLite : %s", e)
        return None

# ────────────────────────────────────────────────────────────────────────────────
# 🏆 Validation de la quête "Réussir un Bmoji"
# ────────────────────────────────────────────────────────────────────────────────

async def valider_quete_bmoji(user: discord.User | discord.Member, channel: discord.abc.Messageable):
    """Valide la quête 'bmoji' et envoie un embed de félicitations si nécessaire."""
    new_lvl = db_valider_quete(user.id)
    if new_lvl is None:
        return

    embed = discord.Embed(
        title="🎉 Quête accomplie !",
        description=(
            f"Tu as réussi ton premier **Bmoji** !\n"
            f"Tu gagnes **+1 niveau** 🆙"
        ),
        color=discord.Color.green()
    )
    embed.set_footer(text=f"Niveau actuel : {new_lvl}")

    try:
        await safe_send(channel, embed=embed)
    except Exception as e:
        log.exception("[bmoji] Erreur envoi embed quête : %s", e)

# ────────────────────────────────────────────────────────────────────────────────
# ⚔️ Fonction commune (slash + préfixe)
# ────────────────────────────────────────────────────────────────────────────────

async def _run_bmoji(target: discord.Interaction | commands.Context):
    """Lance une partie de Bmoji pour l'utilisateur donné."""
    try:
        characters = load_characters()
        if not characters:
            msg = "⚠️ Le fichier d'emojis est vide ou introuvable."
            if isinstance(target, discord.Interaction):
                return await safe_respond(target, msg, ephemeral=True)
            return await safe_send(target.channel, msg)

        perso      = random.choice(characters)
        nom        = perso["nom"]
        emojis     = random.sample(perso["emojis"], k=min(3, len(perso["emojis"])))
        distracteurs = random.sample([c["nom"] for c in characters if c["nom"] != nom], 3)
        options    = distracteurs + [nom]
        random.shuffle(options)

        lettres = ["🇦", "🇧", "🇨", "🇩"]
        bonne   = lettres[options.index(nom)]

        # ─────────────── Embed ───────────────
        embed = discord.Embed(
            title="Bmoji",
            description="Devine le personnage de Bleach derrière ces emojis !",
            color=discord.Color.purple()
        )
        embed.add_field(
            name=" ".join(emojis),
            value="\n".join(f"{lettres[i]} : {options[i]}" for i in range(4)),
            inline=False
        )

        # ─────────────── Boutons ───────────────
        class PersoButton(discord.ui.Button):
            def __init__(self, emoji, idx):
                super().__init__(emoji=emoji, style=discord.ButtonStyle.secondary)
                self.idx = idx

            async def callback(self, inter_button: discord.Interaction):
                if isinstance(target, discord.Interaction):
                    user_ok = inter_button.user == target.user
                else:
                    user_ok = inter_button.user == target.author

                if not user_ok:
                    return await safe_respond(inter_button, "❌ Ce défi ne t'est pas destiné.", ephemeral=True)

                view.success = (lettres[self.idx] == bonne)
                view.stop()
                await inter_button.response.defer()

        view         = discord.ui.View(timeout=30)
        view.success = False
        for i in range(4):
            view.add_item(PersoButton(lettres[i], i))

        # ─────────────── Envoi ───────────────
        if isinstance(target, discord.Interaction):
            await target.response.send_message(embed=embed, view=view)
            msg = await target.original_response()
        else:
            msg = await safe_send(target.channel, embed=embed, view=view)

        view.message = msg
        await view.wait()

        # ─────────────── Résultat ───────────────
        if view.success:
            if isinstance(target, discord.Interaction):
                await target.followup.send("✅ Bonne réponse !")
                await valider_quete_bmoji(target.user, target.channel)
            else:
                await safe_send(target.channel, "✅ Bonne réponse !")
                await valider_quete_bmoji(target.author, target.channel)
        else:
            result_msg = f"❌ Mauvaise réponse (c'était **{nom}**)"
            if isinstance(target, discord.Interaction):
                await target.followup.send(result_msg)
            else:
                await safe_send(target.channel, result_msg)

    except Exception as e:
        log.exception("[bmoji] Erreur inattendue : %s", e)
        err = "⚠️ Une erreur est survenue."
        if isinstance(target, discord.Interaction):
            await safe_respond(target, err, ephemeral=True)
        else:
            await safe_send(target.channel, err)

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────

class BMojiCommand(commands.Cog):
    """Commandes /bmoji et !bmoji — Devine le personnage Bleach caché derrière des emojis."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="bmoji", help="Devine quel personnage Bleach se cache derrière ces emojis.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def bmoji_prefix(self, ctx: commands.Context):
        await _run_bmoji(ctx)

    @bmoji_prefix.error
    async def bmoji_prefix_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.CommandOnCooldown):
            await safe_send(ctx.channel, f"⏳ Attends encore {error.retry_after:.1f}s.")
        else:
            log.exception("[!bmoji] Erreur non gérée : %s", error)
            await safe_send(ctx.channel, "❌ Une erreur est survenue.")

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(name="bmoji", description="Devine quel personnage Bleach se cache derrière ces emojis.")
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def bmoji_slash(self, interaction: discord.Interaction):
        await _run_bmoji(interaction)

    @bmoji_slash.error
    async def bmoji_slash_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            await safe_respond(interaction, f"⏳ Attends encore {error.retry_after:.1f}s.", ephemeral=True)
        else:
            log.exception("[/bmoji] Erreur non gérée : %s", error)
            await safe_respond(interaction, "❌ Une erreur est survenue.", ephemeral=True)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = BMojiCommand(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Bleach"
    await bot.add_cog(cog)
