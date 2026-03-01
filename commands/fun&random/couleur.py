# ────────────────────────────────────────────────────────────────────────────────
# 📌 couleur.py — Commande interactive !couleur et /couleur
# Objectif : Afficher une couleur aléatoire avec ses codes HEX et RGB dans un embed Discord
# Catégorie : Fun&Random
# Accès : Public
# Cooldown : 1 utilisation / 3 sec / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import random
import json
import logging
import discord
from discord import app_commands
from discord.ext import commands

from utils.discord_utils import safe_send, safe_edit, safe_respond, safe_interact
from utils.init_db import get_conn

log = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────────────────────────
# 🗄️ Accès base de données locale
# ────────────────────────────────────────────────────────────────────────────────

def db_valider_quete(user_id: int) -> int | None:
    """
    Vérifie si la quête 'couleur' est déjà validée pour l'utilisateur.
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

        if "couleur" in quetes:
            conn.close()
            return None

        quetes.append("couleur")
        new_lvl = niveau + 1
        cursor.execute(
            "UPDATE reiatsu SET quetes = ?, niveau = ? WHERE user_id = ?",
            (json.dumps(quetes), new_lvl, user_id)
        )
        conn.commit()
        conn.close()
        return new_lvl

    except Exception as e:
        log.exception("[couleur] Erreur validation quête SQLite : %s", e)
        return None

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ Vue interactive avec bouton "Nouvelle couleur"
# ────────────────────────────────────────────────────────────────────────────────

class CouleurView(discord.ui.View):
    def __init__(self, author: discord.User | discord.Member):
        super().__init__(timeout=60)
        self.author  = author
        self.message: discord.Message | None = None

    def generer_embed(self) -> discord.Embed:
        """Génère un embed avec une couleur aléatoire."""
        code_hex = random.randint(0, 0xFFFFFF)
        hex_str  = f"#{code_hex:06X}"
        r, g, b  = (code_hex >> 16) & 0xFF, (code_hex >> 8) & 0xFF, code_hex & 0xFF
        rgb_str  = f"({r}, {g}, {b})"

        embed = discord.Embed(
            title="🌈 Couleur aléatoire",
            description=f"🔹 **Code HEX** : `{hex_str}`\n🔸 **Code RGB** : `{rgb_str}`",
            color=code_hex
        )
        embed.set_image(url=f"https://dummyimage.com/700x200/{code_hex:06x}/{code_hex:06x}.png&text=+")
        return embed

    @discord.ui.button(label="🔁 Nouvelle couleur", style=discord.ButtonStyle.primary)
    async def regenerate(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            return await safe_interact(interaction, content="❌ Tu ne peux pas utiliser ce bouton.", ephemeral=True)
        new_embed = self.generer_embed()
        await safe_interact(interaction, edit=True, embed=new_embed, view=self)

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message:
            try:
                await safe_edit(self.message, view=self)
            except Exception:
                pass

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────

class CouleurCommand(commands.Cog):
    """Commandes /couleur et !couleur — Génère une couleur aléatoire avec codes HEX et RGB."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction interne — validation de la quête
    # ────────────────────────────────────────────────────────────────────────────
    async def _valider_quete(
        self,
        user:        discord.User | discord.Member,
        channel:     discord.abc.Messageable | None = None,
        interaction: discord.Interaction | None     = None
    ):
        """Valide la quête 'couleur' et envoie un embed de félicitations si nécessaire."""
        new_lvl = db_valider_quete(user.id)
        if new_lvl is None:
            return

        embed = discord.Embed(
            title="🎉 Quête accomplie !",
            description=(
                f"Bravo **{user.display_name}** ! Tu as terminé la quête **Couleur** 🏆\n\n"
                f"⭐ **Niveau +1 !** (Niveau {new_lvl})"
            ),
            color=0x00FF7F
        )

        try:
            if channel:
                await safe_send(channel, embed=embed)
            elif interaction:
                if not interaction.response.is_done():
                    await interaction.response.send_message(embed=embed)
                else:
                    await interaction.followup.send(embed=embed)
            else:
                await safe_send(user, embed=embed)
        except Exception as e:
            log.exception("[couleur] Erreur envoi embed quête : %s", e)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="couleur",
        description="Affiche une couleur aléatoire avec un aperçu visuel et ses codes HEX & RGB."
    )
    @app_commands.checks.cooldown(1, 3.0, key=lambda i: i.user.id)
    async def slash_couleur(self, interaction: discord.Interaction):
        try:
            view  = CouleurView(interaction.user)
            embed = view.generer_embed()

            await safe_interact(interaction, embed=embed, view=view)
            view.message = await interaction.original_response()

            await self._valider_quete(interaction.user, channel=interaction.channel, interaction=interaction)

        except Exception as e:
            log.exception("[/couleur] Erreur inattendue : %s", e)
            await safe_respond(interaction, content="❌ Une erreur est survenue.", ephemeral=True)

    @slash_couleur.error
    async def slash_couleur_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            await safe_respond(interaction, f"⏳ Attends encore {error.retry_after:.1f}s.", ephemeral=True)
        else:
            log.exception("[/couleur] Erreur non gérée : %s", error)
            await safe_respond(interaction, "❌ Une erreur est survenue.", ephemeral=True)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(
        name="couleur",
        help="🎨 Affiche une couleur aléatoire avec ses codes HEX et RGB."
    )
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def prefix_couleur(self, ctx: commands.Context):
        try:
            view         = CouleurView(ctx.author)
            embed        = view.generer_embed()
            view.message = await safe_send(ctx, embed=embed, view=view)

            await self._valider_quete(ctx.author, channel=ctx.channel)

        except Exception as e:
            log.exception("[!couleur] Erreur inattendue : %s", e)
            await safe_send(ctx, "❌ Une erreur est survenue.")

    @prefix_couleur.error
    async def prefix_couleur_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.CommandOnCooldown):
            await safe_send(ctx.channel, f"⏳ Attends encore {error.retry_after:.1f}s.")
        else:
            log.exception("[!couleur] Erreur non gérée : %s", error)
            await safe_send(ctx.channel, "❌ Une erreur est survenue.")

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = CouleurCommand(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Fun&Random"
    await bot.add_cog(cog)
