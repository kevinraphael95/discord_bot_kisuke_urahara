# ────────────────────────────────────────────────────────────────────────────────
# 📌 pizza_aléatoire.py — Commande interactive /pizza et !pizza
# Objectif : Générer une pizza aléatoire simple (pâte, sauce, fromage, garnitures, toppings)
# Catégorie : Fun&Random
# Accès : Tous
# Cooldown : 1 utilisation / 3 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, button
import json
import os
import random
from utils.discord_utils import safe_send, safe_edit, safe_respond, safe_interact

# ────────────────────────────────────────────────────────────────────────────────
# 📂 Chargement des données JSON
# ────────────────────────────────────────────────────────────────────────────────
DATA_JSON_PATH = os.path.join("data", "pizza_options.json")

def load_data():
    """Charge les options de pizza depuis le fichier JSON."""
    try:
        with open(DATA_JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERREUR JSON] Impossible de charger {DATA_JSON_PATH} : {e}")
        return {}

# ────────────────────────────────────────────────────────────────────────────────
# 🧩 Génération d'une pizza aléatoire (embed)
# ────────────────────────────────────────────────────────────────────────────────
def generate_pizza_embed(data: dict) -> discord.Embed:
    """Génère un embed représentant une pizza aléatoire."""
    pate = random.choice(data.get("pates", ["Classique"]))
    base = random.choice(data.get("bases", ["Tomate"]))
    fromage = random.choice(data.get("fromages", ["Mozzarella"]))
    garnitures = random.sample(data.get("garnitures", ["Champignons", "Jambon"]), k=min(2, len(data.get("garnitures", []))))
    toppings = random.sample(data.get("toppings_speciaux", ["Olives"]), k=min(1, len(data.get("toppings_speciaux", []))))

    embed = discord.Embed(
        title="🍕 Ta pizza aléatoire",
        color=discord.Color.orange()
    )
    embed.add_field(name="Pâte", value=pate, inline=False)
    embed.add_field(name="Base (sauce)", value=base, inline=False)
    embed.add_field(name="Fromage", value=fromage, inline=False)
    embed.add_field(name="Garnitures", value=", ".join(garnitures), inline=False)
    embed.add_field(name="Toppings spéciaux", value=", ".join(toppings), inline=False)
    embed.set_footer(text="Clique sur 🍕 Nouvelle pizza pour en générer une autre !")
    return embed

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ Vue interactive avec bouton
# ────────────────────────────────────────────────────────────────────────────────
class PizzaView(View):
    """Vue contenant un bouton pour régénérer une pizza aléatoire."""
    def __init__(self, data: dict, author: discord.User | discord.Member):
        super().__init__(timeout=60)
        self.data = data
        self.author = author
        self.message: discord.Message | None = None

    async def on_timeout(self):
        """Désactive les boutons à la fin du timeout."""
        for child in self.children:
            child.disabled = True
        if self.message:
            try:
                await safe_edit(self.message, view=self)
            except Exception:
                pass

    @button(label="🍕 Nouvelle pizza", style=discord.ButtonStyle.green)
    async def nouvelle_pizza(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Régénère une pizza aléatoire (seul l’auteur peut le faire)."""
        if interaction.user != self.author:
            return await safe_interact(interaction, content="❌ Ce n'est pas ta pizza !", ephemeral=True)

        new_embed = generate_pizza_embed(self.data)
        await safe_interact(interaction, edit=True, embed=new_embed, view=self)

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class PizzaAleatoire(commands.Cog):
    """Commande /pizza et !pizza — Génère une pizza aléatoire simple."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Fonction interne partagée
    async def _send_pizza(self, destination, author):
        data = load_data()
        if not data:
            return await safe_send(destination, "❌ Impossible de charger les options de pizza.")
        embed = generate_pizza_embed(data)
        view = PizzaView(data, author)
        view.message = await safe_send(destination, embed=embed, view=view)

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

            view = PizzaView(data, interaction.user)
            embed = generate_pizza_embed(data)

            await safe_interact(interaction, embed=embed, view=view)
            view.message = await interaction.original_response()

        except app_commands.CommandOnCooldown as e:
            await safe_respond(interaction, f"⏳ Attends encore {e.retry_after:.1f}s.", ephemeral=True)
        except Exception as e:
            print(f"[ERREUR /pizza] {e}")
            await safe_respond(interaction, "❌ Une erreur est survenue lors de la génération de la pizza.", ephemeral=True)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="pizza", help="🍕 Génère une pizza aléatoire.")
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def prefix_pizza(self, ctx: commands.Context):
        try:
            await self._send_pizza(ctx.channel, ctx.author)
        except commands.CommandOnCooldown as e:
            await safe_send(ctx, f"⏳ Attends encore {e.retry_after:.1f}s.")
        except Exception as e:
            print(f"[ERREUR !pizza] {e}")
            await safe_send(ctx, "❌ Une erreur est survenue lors de la génération de la pizza.")

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = PizzaAleatoire(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Fun&Random"
    await bot.add_cog(cog)
