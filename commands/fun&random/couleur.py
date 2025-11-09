# ────────────────────────────────────────────────────────────────────────────────
# 📌 couleur.py — Commande interactive !couleur et /couleur
# Objectif : Afficher une couleur aléatoire avec ses codes HEX et RGB dans un embed Discord
# Catégorie : 🎨 Fun&Random
# Accès : Public
# Cooldown : 1 utilisation / 3 sec / utilisateur
# Version : ✅ Optimisée + intègre la quête "couleur"
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import random
import discord
from discord import app_commands
from discord.ext import commands
from utils.discord_utils import safe_send, safe_edit, safe_respond, safe_interact
from utils.supabase_client import supabase  # ✅ pour accéder à la base

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ Vue interactive avec bouton "Nouvelle couleur"
# ────────────────────────────────────────────────────────────────────────────────
class CouleurView(discord.ui.View):
    def __init__(self, author: discord.User | discord.Member):
        super().__init__(timeout=60)
        self.author = author
        self.message: discord.Message | None = None

    def generer_embed(self) -> discord.Embed:
        code_hex = random.randint(0, 0xFFFFFF)
        hex_str = f"#{code_hex:06X}"
        r, g, b = (code_hex >> 16) & 0xFF, (code_hex >> 8) & 0xFF, code_hex & 0xFF
        rgb_str = f"({r}, {g}, {b})"

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
    """Commande !couleur et /couleur — Génère et affiche une couleur aléatoire avec codes HEX et RGB."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # ⚙️ Fonction interne pour valider la quête "couleur"
    # ────────────────────────────────────────────────────────────────────────────
    async def valider_quete_couleur(
        self, 
        user: discord.User, 
        channel: discord.abc.Messageable | None = None, 
        interaction: discord.Interaction | None = None
    ):
        try:
            data = supabase.table("reiatsu").select("quetes, niveau").eq("user_id", user.id).execute()
            if not data.data:
                return  # Aucun profil trouvé

            quetes = data.data[0].get("quetes", [])
            niveau = data.data[0].get("niveau", 1)

            # Si la quête est déjà faite, rien à faire
            if "couleur" in quetes:
                return

            # Ajoute la quête et augmente le niveau
            quetes.append("couleur")
            new_lvl = niveau + 1
            supabase.table("reiatsu").update({"quetes": quetes, "niveau": new_lvl}).eq("user_id", user.id).execute()

            # ✅ Embed de félicitations
            embed = discord.Embed(
                title="🎉 Quête accomplie !",
                description=f"Bravo **{user.name}** ! Tu as terminé la quête **Couleur** 🏆\n\n⭐ **Niveau +1 !** (Niveau {new_lvl})",
                color=0x00FF7F
            )

            # Envoi dans le salon approprié
            if interaction:
                if channel:
                    await safe_send(channel, embed=embed)
                else:
                    if not interaction.response.is_done():
                        await interaction.response.send_message(embed=embed)
                    else:
                        await interaction.followup.send(embed=embed)
            elif channel:
                await safe_send(channel, embed=embed)
            else:
                # fallback au MP
                await safe_send(user, embed=embed)

        except Exception as e:
            print(f"[ERREUR validation quête couleur] {e}")

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="couleur",
        description="Affiche une couleur aléatoire avec un aperçu visuel et ses codes HEX & RGB."
    )
    @app_commands.checks.cooldown(1, 3.0, key=lambda i: (i.user.id))
    async def slash_couleur(self, interaction: discord.Interaction):
        try:
            view = CouleurView(interaction.user)
            embed = view.generer_embed()

            await safe_interact(interaction, embed=embed, view=view)
            view.message = await interaction.original_response()

            # ✅ Validation de la quête dans le salon
            await self.valider_quete_couleur(interaction.user, channel=interaction.channel, interaction=interaction)

        except Exception as e:
            print(f"[ERREUR /couleur] {e}")
            await safe_respond(interaction, content="❌ Une erreur est survenue lors de la génération de la couleur.", ephemeral=True)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(
        name="couleur",
        help="🎨 Affiche une couleur aléatoire avec ses codes HEX et RGB.",
        description="Affiche une couleur aléatoire avec un aperçu visuel et ses codes HEX & RGB."
    )
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.user)
    async def prefix_couleur(self, ctx: commands.Context):
        try:
            view = CouleurView(ctx.author)
            embed = view.generer_embed()
            view.message = await safe_send(ctx, embed=embed, view=view)

            # ✅ Validation de la quête dans le salon
            await self.valider_quete_couleur(ctx.author, channel=ctx.channel)

        except Exception as e:
            print(f"[ERREUR !couleur] {e}")
            await safe_send(ctx, "❌ Une erreur est survenue lors de la génération de la couleur.")

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = CouleurCommand(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Fun&Random"
    await bot.add_cog(cog)
