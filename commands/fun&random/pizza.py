# ────────────────────────────────────────────────────────────────────────────────
# 📌 pizza_aléatoire.py — Commande interactive /pizza et !pizza
# Objectif : Générer une pizza aléatoire simple (pâte, sauce, fromage, garnitures, toppings)
# Catégorie : Fun&Random
# Accès : Tous
# Cooldown : 1 utilisation / 3 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, button
import json
import os
import random
import logging

from utils.discord_utils import safe_send, safe_edit, safe_respond, safe_interact
from utils.init_db import get_conn

log = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────────────────────────
# 📂 Chargement des données JSON
# ────────────────────────────────────────────────────────────────────────────────
DATA_JSON_PATH = os.path.join("data", "pizza_options.json")

def load_data() -> dict:
    """Charge les options de pizza depuis le fichier JSON."""
    try:
        with open(DATA_JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log.exception("[pizza] Impossible de charger %s : %s", DATA_JSON_PATH, e)
        return {}

# ────────────────────────────────────────────────────────────────────────────────
# 🗄️ Accès base de données locale
# ────────────────────────────────────────────────────────────────────────────────

def db_valider_quete(user_id: int) -> int | None:
    """
    Vérifie si la quête 'pizza' est déjà validée pour l'utilisateur.
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
        niveau = row[1] or 1

        if "pizza" in quetes:
            conn.close()
            return None

        quetes.append("pizza")
        new_lvl = niveau + 1
        cursor.execute(
            "UPDATE reiatsu SET quetes = ?, niveau = ? WHERE user_id = ?",
            (json.dumps(quetes), new_lvl, user_id)
        )
        conn.commit()
        conn.close()
        return new_lvl

    except Exception as e:
        log.exception("[pizza] Erreur validation quête SQLite : %s", e)
        return None

# ────────────────────────────────────────────────────────────────────────────────
# 🧩 Génération d'une pizza aléatoire (embed)
# ────────────────────────────────────────────────────────────────────────────────

def generate_pizza_embed(data: dict) -> discord.Embed:
    """Génère un embed représentant une pizza aléatoire."""
    pate       = random.choice(data.get("pates", ["Classique"]))
    base       = random.choice(data.get("bases", ["Tomate"]))
    fromage    = random.choice(data.get("fromages", ["Mozzarella"]))
    garnitures = random.sample(data.get("garnitures", ["Champignons", "Jambon"]), k=min(2, len(data.get("garnitures", []))))
    toppings   = random.sample(data.get("toppings_speciaux", ["Olives"]),          k=min(1, len(data.get("toppings_speciaux", []))))

    embed = discord.Embed(title="🍕 Ta pizza aléatoire", color=discord.Color.orange())
    embed.add_field(name="Pâte",             value=pate,                   inline=False)
    embed.add_field(name="Base (sauce)",     value=base,                   inline=False)
    embed.add_field(name="Fromage",          value=fromage,                inline=False)
    embed.add_field(name="Garnitures",       value=", ".join(garnitures),  inline=False)
    embed.add_field(name="Toppings spéciaux",value=", ".join(toppings),    inline=False)
    return embed

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ Vue interactive avec bouton
# ────────────────────────────────────────────────────────────────────────────────

class PizzaView(View):
    """Vue contenant un bouton pour régénérer une pizza aléatoire."""
    def __init__(self, data: dict, author: discord.User | discord.Member):
        super().__init__(timeout=60)
        self.data    = data
        self.author  = author
        self.message: discord.Message | None = None

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message:
            try:
                await safe_edit(self.message, view=self)
            except Exception:
                pass

    @button(label="🍕 Nouvelle pizza", style=discord.ButtonStyle.green)
    async def nouvelle_pizza(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            return await safe_interact(interaction, content="❌ Ce n'est pas ta pizza !", ephemeral=True)
        new_embed = generate_pizza_embed(self.data)
        await safe_interact(interaction, edit=True, embed=new_embed, view=self)

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────

class PizzaAleatoire(commands.Cog):
    """Commandes /pizza et !pizza — Génère une pizza aléatoire simple."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction interne — validation de la quête
    # ────────────────────────────────────────────────────────────────────────────
    async def _valider_quete(
        self,
        user:    discord.User | discord.Member,
        channel: discord.abc.Messageable | None = None
    ):
        """Valide la quête 'pizza' et envoie un embed de félicitations si nécessaire."""
        new_lvl = db_valider_quete(user.id)
        if new_lvl is None:
            return

        embed = discord.Embed(
            title="🎉 Quête accomplie !",
            description=(
                f"Bravo **{user.display_name}** ! Tu as terminé la quête **Pizza** 🍕\n\n"
                f"⭐ **Niveau +1 !** (Niveau {new_lvl})"
            ),
            color=0xFFA500
        )

        try:
            if channel:
                await safe_send(channel, embed=embed)
            else:
                await safe_send(user, embed=embed)
        except Exception as e:
            log.exception("[pizza] Erreur envoi embed quête : %s", e)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(name="pizza", description="🍕 Génère une pizza aléatoire.")
    @app_commands.checks.cooldown(1, 3.0, key=lambda i: i.user.id)
    async def slash_pizza(self, interaction: discord.Interaction):
        try:
            data = load_data()
            if not data:
                return await safe_respond(interaction, "❌ Impossible de charger les options de pizza.", ephemeral=True)

            view  = PizzaView(data, interaction.user)
            embed = generate_pizza_embed(data)

            await safe_interact(interaction, embed=embed, view=view)
            view.message = await interaction.original_response()

            await self._valider_quete(interaction.user, channel=interaction.channel)

        except Exception as e:
            log.exception("[/pizza] Erreur inattendue : %s", e)
            await safe_respond(interaction, "❌ Une erreur est survenue.", ephemeral=True)

    @slash_pizza.error
    async def slash_pizza_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            await safe_respond(interaction, f"⏳ Attends encore {error.retry_after:.1f}s.", ephemeral=True)
        else:
            log.exception("[/pizza] Erreur non gérée : %s", error)
            await safe_respond(interaction, "❌ Une erreur est survenue.", ephemeral=True)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="pizza", help="🍕 Génère une pizza aléatoire.")
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def prefix_pizza(self, ctx: commands.Context):
        try:
            data = load_data()
            if not data:
                return await safe_send(ctx, "❌ Impossible de charger les options de pizza.")

            view         = PizzaView(data, ctx.author)
            embed        = generate_pizza_embed(data)
            view.message = await safe_send(ctx, embed=embed, view=view)

            await self._valider_quete(ctx.author, channel=ctx.channel)

        except Exception as e:
            log.exception("[!pizza] Erreur inattendue : %s", e)
            await safe_send(ctx, "❌ Une erreur est survenue.")

    @prefix_pizza.error
    async def prefix_pizza_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.CommandOnCooldown):
            await safe_send(ctx.channel, f"⏳ Attends encore {error.retry_after:.1f}s.")
        else:
            log.exception("[!pizza] Erreur non gérée : %s", error)
            await safe_send(ctx.channel, "❌ Une erreur est survenue.")

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = PizzaAleatoire(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Fun&Random"
    await bot.add_cog(cog)
