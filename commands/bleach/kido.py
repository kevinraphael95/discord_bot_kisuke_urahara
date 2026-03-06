# ────────────────────────────────────────────────────────────────────────────────
# 📌 kido.py — Commande interactive /kido et !kido
# Objectif : Affiche un Kido aléatoire, précis ou liste tous les Kido paginés
# Catégorie : Bleach
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import json
import logging
import os
import random

import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button

from utils.discord_utils import safe_send, safe_edit

log = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────────────────────────
# 📂 Chargement des données JSON
# ────────────────────────────────────────────────────────────────────────────────
DATA_JSON_PATH = os.path.join("data", "kido.json")

def load_data():
    """Charge le fichier JSON contenant les Kido."""
    try:
        with open(DATA_JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log.exception("[kido] Impossible de charger %s : %s", DATA_JSON_PATH, e)
        return {}

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ UI — Pagination
# ────────────────────────────────────────────────────────────────────────────────

class KidoPaginator(View):
    def __init__(self, embed_pages: list):
        super().__init__(timeout=180)
        self.pages       = embed_pages
        self.current     = 0
        self.message     = None
        self.prev_button = Button(label="⬅️", style=discord.ButtonStyle.secondary)
        self.next_button = Button(label="➡️", style=discord.ButtonStyle.secondary)
        self.prev_button.callback = self.prev_page
        self.next_button.callback = self.next_page
        self.add_item(self.prev_button)
        self.add_item(self.next_button)
        self._update_buttons()

    def _update_buttons(self):
        self.prev_button.disabled = self.current == 0
        self.next_button.disabled = self.current == len(self.pages) - 1

    async def prev_page(self, interaction: discord.Interaction):
        self.current -= 1
        self._update_buttons()
        await safe_edit(self.message, embed=self.pages[self.current], view=self)
        await interaction.response.defer()

    async def next_page(self, interaction: discord.Interaction):
        self.current += 1
        self._update_buttons()
        await safe_edit(self.message, embed=self.pages[self.current], view=self)
        await interaction.response.defer()

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────

class Kido(commands.Cog):
    """
    Commandes /kido et !kido — Affiche un Kido aléatoire, précis ou liste tous les Kido paginés.
    """
    def __init__(self, bot: commands.Bot):
        self.bot   = bot
        self.data  = load_data()
        self.alias = {"h": "hado", "b": "bakudo", "a": "autre", "r": "random"}
        self.types = list(self.data.keys())
        self.colors = {
            "hado":   discord.Color.red(),
            "bakudo": discord.Color.blue(),
            "other":  discord.Color.purple()
        }

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonctions internes communes
    # ────────────────────────────────────────────────────────────────────────────
    async def _send_kido(self, channel: discord.abc.Messageable, kido_type: str = None, number: str = None):
        """Affiche un Kido selon le type et le numéro demandés."""

        # ─── Aide si aucun argument ───
        if not kido_type:
            help_embed = discord.Embed(
                title="📜 Commande Kido",
                description=(
                    "**Utilisation :**\n"
                    "`!!kido <type> <numéro>` — Affiche un Kido précis\n"
                    "`!!kido <type> random` ou `!!kido <type> r` — Kido aléatoire dans ce type\n"
                    "`!!kido random` ou `!!kido r` — Kido aléatoire total\n"
                    "`!!kido all` — Liste de tous les Kido paginés\n\n"
                    "**Types disponibles :** Hado (`h`), Bakudo (`b`), Autre (`a`)"
                ),
                color=discord.Color.teal()
            )
            await safe_send(channel, embed=help_embed)
            return

        kido_type = self.alias.get(kido_type.lower(), kido_type.lower())

        # ─── Liste complète ───
        if kido_type == "all":
            embed_pages = []
            for t in self.types:
                items = list(self.data[t].keys())
                for i in range(0, len(items), 15):
                    chunk = items[i:i + 15]
                    desc  = "\n".join(f"{key} - {self.data[t][key].get('nom', 'Unknown')}" for key in chunk)
                    embed_pages.append(discord.Embed(
                        title=f"{t.capitalize()} [{i + 1}-{min(i + 15, len(items))}]",
                        description=desc,
                        color=self.colors.get(t, discord.Color.teal())
                    ))
            if not embed_pages:
                await safe_send(channel, "❌ Aucun Kido trouvé.")
                return
            paginator         = KidoPaginator(embed_pages)
            paginator.message = await safe_send(channel, embed=embed_pages[0], view=paginator)
            return

        # ─── Liste paginée pour un type précis ───
        if kido_type in self.data and not number:
            items       = list(self.data[kido_type].keys())
            embed_pages = []
            for i in range(0, len(items), 15):
                chunk = items[i:i + 15]
                desc  = "\n".join(f"{key} - {self.data[kido_type][key].get('nom', 'Unknown')}" for key in chunk)
                embed_pages.append(discord.Embed(
                    title=f"{kido_type.capitalize()} [{i + 1}-{min(i + 15, len(items))}]",
                    description=desc,
                    color=self.colors.get(kido_type, discord.Color.teal())
                ))
            paginator         = KidoPaginator(embed_pages)
            paginator.message = await safe_send(channel, embed=embed_pages[0], view=paginator)
            return

        # ─── Random global ou par type ───
        if kido_type == "random":
            kido_type = random.choice(self.types)
            number    = random.choice(list(self.data[kido_type].keys()))
        elif not number or number.lower() in ["random", "r"]:
            number = random.choice(list(self.data[kido_type].keys()))

        # ─── Vérification existence ───
        if kido_type not in self.data or number not in self.data[kido_type]:
            await safe_send(channel, f"❌ Type ou numéro de Kido invalide : `{kido_type} {number}`")
            return

        # ─── Affichage du Kido ───
        infos = self.data[kido_type][number]
        embed = discord.Embed(
            title=f"{infos.get('nom', number)} ({kido_type.capitalize()} {number})",
            color=self.colors.get(kido_type, discord.Color.teal())
        )
        for field_name, field_value in infos.items():
            value = "\n".join(f"• {item}" for item in field_value) if isinstance(field_value, list) else str(field_value)
            embed.add_field(name=field_name.capitalize(), value=value, inline=False)
        await safe_send(channel, embed=embed)

    async def type_autocomplete(self, interaction: discord.Interaction, current: str):
        all_types = self.types + list(self.alias.keys())
        return [
            app_commands.Choice(name=t, value=t)
            for t in all_types if current.lower() in t.lower()
        ][:25]

    async def number_autocomplete(self, interaction: discord.Interaction, current: str):
        type_param = getattr(interaction.namespace, "type", None)
        if not type_param:
            return []
        type_param = self.alias.get(type_param.lower(), type_param.lower())
        if type_param not in self.data:
            return []
        return [
            app_commands.Choice(name=num, value=num)
            for num in self.data[type_param].keys() if current in num
        ][:25]

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(name="kido",description="Affiche un Kido aléatoire, précis ou liste tous les Kido.")
    @app_commands.describe(type="Type de Kido (hado, bakudo, autres) ou abrégé (h, b, a)", number="Numéro du Kido ou 'random'")
    @app_commands.autocomplete(type=type_autocomplete, number=number_autocomplete)
    @app_commands.checks.cooldown(rate=1, per=5.0, key=lambda i: i.user.id)
    async def slash_kido(self, interaction: discord.Interaction, type: str = None, number: str = None):
        await interaction.response.defer()
        await self._send_kido(interaction.channel, type, number)
        await interaction.delete_original_response()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="kido",help="Affiche un Kido précis, aléatoire ou la liste paginée.")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_kido(self, ctx: commands.Context, kido_type: str = None, number: str = None):
        await self._send_kido(ctx.channel, kido_type, number)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Kido(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Bleach"
    await bot.add_cog(cog)
