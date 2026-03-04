# ────────────────────────────────────────────────────────────────────────────────
# 📌 keylottery.py — Commande interactive /scratchkey et !scratchkey
# Objectif : Ticket à gratter avec 10 boutons et remise en jeu d'une clé Steam
# Catégorie : Reiatsu
# Accès : Public
# Cooldown : 1 utilisation / 10 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button
import random
import sqlite3
from utils.discord_utils import safe_send, safe_edit, safe_respond
from utils.init_db import REIATSU_DB_PATH

# ────────────────────────────────────────────────────────────────────────────────
# 📂 Constantes
# ────────────────────────────────────────────────────────────────────────────────
SCRATCH_COST = 250
NB_BUTTONS = 10

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Fonctions DB
# ────────────────────────────────────────────────────────────────────────────────
def get_conn():
    return sqlite3.connect(REIATSU_DB_PATH)


# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ UI — Ticket à gratter
# ────────────────────────────────────────────────────────────────────────────────
class ScratchTicketView(View):

    def __init__(self, author_id: int, message: discord.Message = None, parent=None):
        super().__init__(timeout=120)
        self.author_id = author_id
        self.message = message
        self.value = None
        self.last_interaction = None
        self.parent = parent

        self.winning_button = random.randint(0, NB_BUTTONS - 1)
        self.double_button = random.randint(0, NB_BUTTONS - 1)
        while self.double_button == self.winning_button:
            self.double_button = random.randint(0, NB_BUTTONS - 1)

        self.add_item(BetButton(self))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await safe_respond(interaction, "❌ Ce ticket n'est pas pour toi.", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message and self.message.embeds:
            embed = self.message.embeds[0]
            embed.set_footer(text="⏳ Temps écoulé. Relance /scratchkey pour retenter ta chance.")
            await safe_edit(self.message, embed=embed, view=self)


# ────────────────────────────────────────────────────────────────────────────────
# 🔹 Bouton Miser
# ────────────────────────────────────────────────────────────────────────────────
class BetButton(Button):

    def __init__(self, parent_view: ScratchTicketView):
        super().__init__(label=f"Miser {SCRATCH_COST} Reiatsu et jouer", style=discord.ButtonStyle.green)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        reiatsu_points = await self.parent_view.parent._get_reiatsu(interaction.user.id)

        if reiatsu_points < SCRATCH_COST:
            return await safe_respond(interaction, f"❌ Pas assez de Reiatsu ! Il te faut {SCRATCH_COST}.", ephemeral=True)

        await self.parent_view.parent._update_reiatsu(interaction.user.id, reiatsu_points - SCRATCH_COST)

        self.parent_view.clear_items()
        for i in range(NB_BUTTONS):
            self.parent_view.add_item(ScratchButton(i, self.parent_view))

        await interaction.response.edit_message(view=self.parent_view)


# ────────────────────────────────────────────────────────────────────────────────
# 🔹 Boutons du ticket
# ────────────────────────────────────────────────────────────────────────────────
class ScratchButton(Button):

    def __init__(self, index: int, parent: ScratchTicketView):
        super().__init__(label=f"🎟️ {index+1}", style=discord.ButtonStyle.blurple)
        self.index = index
        self.parent_view = parent

    async def callback(self, interaction: discord.Interaction):

        for child in self.parent_view.children:
            child.disabled = True

        if self.index == self.parent_view.winning_button:
            result_type = "key"
            color = discord.Color.green()
            msg = "🎉 Tu as trouvé une clé Steam !"

        elif self.index == self.parent_view.double_button:
            result_type = "jackpot"
            color = discord.Color.gold()
            msg = "💎 Jackpot ! Tu gagnes le double de ta mise !"

        else:
            result_type = "lose"
            color = discord.Color.red()
            msg = "😢 Pas de chance cette fois !"

        await interaction.message.edit(view=self.parent_view)

        embed = discord.Embed(
            title="🎰 Résultat du Ticket à Gratter",
            description=msg,
            color=color
        )
        embed.set_footer(text="Relance /scratchkey pour tenter à nouveau.")

        await interaction.response.send_message(embed=embed)

        self.parent_view.value = result_type
        self.parent_view.last_interaction = interaction
        self.parent_view.stop()


# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class ScratchKey(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ───────────── Gestion Reiatsu ─────────────
    async def _get_reiatsu(self, user_id: int) -> int:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT points FROM reiatsu WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else 0

    async def _update_reiatsu(self, user_id: int, new_points: int):
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("UPDATE reiatsu SET points = ? WHERE user_id = ?", (new_points, user_id))
        conn.commit()
        conn.close()

    # ───────────── Gestion Steam Keys ─────────────
    async def _get_all_steam_keys(self):
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT id, game_name, steam_url, steam_key FROM steam_keys WHERE won = 0 OR won = 'false' OR won IS NULL")
        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "id": r[0],
                "game_name": r[1],
                "steam_url": r[2],
                "steam_key": r[3]
            }
            for r in rows
        ]

    async def _mark_steam_key_won(self, key_id: int, winner: str):
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE steam_keys SET won = 1, winner = ? WHERE id = ? AND (won = 0 OR won = 'false')",
            (winner, key_id)
        )
        conn.commit()
        conn.close()

    # ───────────── Envoi Ticket ─────────────
    async def _send_ticket(self, channel, user, user_id: int):
        reiatsu_points = await self._get_reiatsu(user_id)
        keys_dispo = await self._get_all_steam_keys()

        jeux = ", ".join([k["game_name"] for k in keys_dispo[:5]]) or "Aucun"
        if len(keys_dispo) > 5:
            jeux += "…"

        embed = discord.Embed(
            title="🎟️ Ticket à gratter",
            description=(
                f"**Reiatsu possédé** : **{reiatsu_points}**\n"
                f"**Prix du ticket** : **{SCRATCH_COST}**\n"
                f"**🔑 Nombre de clés à gagner** : **{len(keys_dispo)}**\n"
                f"**🎮 Jeux gagnables** : {jeux}\n\n"
                f"Appuie sur **Miser et jouer** pour commencer."
            ),
            color=discord.Color.blurple()
        )

        view = ScratchTicketView(user_id, parent=self)
        message = await safe_send(channel, embed=embed, view=view)
        view.message = message
        return view

    # ───────────── Gestion Résultat ─────────────
    async def _handle_result(self, interaction, result_type: str, user_id: int):
        reiatsu_points = await self._get_reiatsu(user_id)

        if result_type == "jackpot":
            await self._update_reiatsu(user_id, reiatsu_points + SCRATCH_COST * 2)

        elif result_type == "key":
            await self._update_reiatsu(user_id, reiatsu_points + SCRATCH_COST)

            keys_dispo = await self._get_all_steam_keys()
            if not keys_dispo:
                return await safe_send(interaction.channel, "⛔ Aucune clé Steam disponible.")

            chosen = random.choice(keys_dispo)
            await self._mark_steam_key_won(chosen["id"], interaction.user.name)

            try:
                await interaction.user.send(
                    f"🎁 **Clé Steam pour {chosen['game_name']}**\n`{chosen['steam_key']}`"
                )
            except discord.Forbidden:
                await safe_send(interaction.channel, "⚠️ Impossible d'envoyer un DM.")

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────       
    @app_commands.command(name="keylottery", description="Ticket à gratter : tente ta chance")
    @app_commands.checks.cooldown(1, 10.0, key=lambda i: (i.user.id))
    async def slash_scratchkey(self, interaction: discord.Interaction):
        await interaction.response.defer()
        view = await self._send_ticket(interaction.channel, interaction.user, interaction.user.id)
        await view.wait()
        if view.value:
            await self._handle_result(view.last_interaction, view.value, interaction.user.id)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────     
    @commands.command(name="keylottery", aliases=["kl"], help="Ticket à gratter : tente ta chance")
    @commands.cooldown(1, 10.0, commands.BucketType.user)
    async def prefix_scratchkey(self, ctx: commands.Context):
        view = await self._send_ticket(ctx.channel, ctx.author, ctx.author.id)
        await view.wait()
        if view.value:
            class Dummy:
                def __init__(self, user, channel):
                    self.user = user
                    self.channel = channel
            await self._handle_result(Dummy(ctx.author, ctx.channel), view.value, ctx.author.id)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = ScratchKey(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Reiatsu"
    await bot.add_cog(cog)
