# ────────────────────────────────────────────────────────────────────────────────
# 📌 hollow.py — Commande interactive !hollow
# Objectif : Faire apparaître un Hollow, attaquer (1 reiatsu), réussir 3 tâches.
# Catégorie : Reiatsu
# Accès : Public
# Cooldown : 1 utilisation / 10 sec / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands
import os
import traceback
from utils.supabase_client import supabase
from utils.taches import lancer_3_taches

# ────────────────────────────────────────────────────────────────────────────────
# 📂 Constantes
# ────────────────────────────────────────────────────────────────────────────────
HOLLOW_IMAGE_PATH = os.path.join("data", "images", "hollows", "hollow0.jpg")
REIATSU_COST = 1

# ────────────────────────────────────────────────────────────────────────────────
# ⚔️ Commande principale
# ────────────────────────────────────────────────────────────────────────────────
class Hollow(commands.Cog):
    """👹 Combat contre un Hollow — dépense du reiatsu et réussis 3 épreuves !"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="hollow", help="👹 Fais apparaître un Hollow et tente de le vaincre (1 reiatsu requis).")
    @commands.cooldown(1, 10.0, commands.BucketType.user)
    async def hollow_cmd(self, ctx: commands.Context):
        user_id = str(ctx.author.id)

        # ───────── Vérif image ─────────
        if not os.path.isfile(HOLLOW_IMAGE_PATH):
            return await ctx.send("❌ Image du Hollow introuvable.")

        # ───────── Vérif reiatsu ─────────
        try:
            res = supabase.table("reiatsu").select("points").eq("user_id", user_id).execute()
            reiatsu = res.data[0]["points"] if res.data else 0
        except Exception:
            traceback.print_exc()
            return await ctx.send("⚠️ Erreur lors de la vérification du reiatsu.")

        if reiatsu < REIATSU_COST:
            return await ctx.send(f"❌ Il te faut au moins {REIATSU_COST} reiatsu pour attaquer un Hollow.")

        # ───────── Embed initial ─────────
        file = discord.File(HOLLOW_IMAGE_PATH, filename="hollow.jpg")
        embed = discord.Embed(
            title="👹 Un Hollow est apparu !",
            description=f"{ctx.author.mention}, un Hollow approche... ⚠️\n"
                        f"Clique sur **Attaquer** pour dépenser {REIATSU_COST} reiatsu et lancer le combat.",
            color=discord.Color.dark_red()
        )
        embed.set_image(url="attachment://hollow.jpg")
        embed.set_footer(text="Tu as 60 secondes pour agir.")

        # ───────── Vue avec bouton ─────────
        view = discord.ui.View(timeout=60)

        class AttackButton(discord.ui.Button):
            def __init__(self):
                super().__init__(label="⚔️ Attaquer", style=discord.ButtonStyle.danger)

            async def callback(self, interaction: discord.Interaction):
                if interaction.user.id != ctx.author.id:
                    return await interaction.response.send_message("❌ Ce combat ne t'appartient pas.", ephemeral=True)

                self.disabled = True
                for child in view.children:
                    child.disabled = True
                await interaction.response.edit_message(view=view)

                # Déduire le reiatsu
                try:
                    supabase.table("reiatsu").update({"points": reiatsu - REIATSU_COST}).eq("user_id", user_id).execute()
                except Exception:
                    traceback.print_exc()
                    return await ctx.send("⚠️ Erreur de mise à jour du reiatsu.")

                # Lancer les épreuves
                embed.title = "⚔️ Combat contre le Hollow"
                embed.description = (
                    f"{ctx.author.display_name} affronte le Hollow !\n\n"
                    f"🌀 Trois épreuves vont être lancées... sois prêt !"
                )
                embed.color = discord.Color.orange()
                await interaction.edit_original_response(embed=embed, attachments=[], view=None)

                async def update_embed(e: discord.Embed):
                    await interaction.edit_original_response(embed=e)

                # Préparation
                embed.clear_fields()
                embed.add_field(name="Préparation...", value="Les épreuves vont commencer...", inline=False)
                await update_embed(embed)

                # Lancer les 3 tâches
                try:
                    victoire = await lancer_3_taches(interaction, embed, update_embed)
                except Exception:
                    traceback.print_exc()
                    victoire = False

                # Résultat final
                result = discord.Embed(
                    title="🎯 Résultat du combat",
                    description=(
                        f"🎉 Tu as vaincu le Hollow ! Bravo, {ctx.author.mention} !"
                        if victoire else f"💀 Le Hollow t’a vaincu... retente ta chance !"
                    ),
                    color=discord.Color.green() if victoire else discord.Color.red()
                )
                result.set_footer(text=f"Combat terminé pour {ctx.author.display_name}")
                await interaction.edit_original_response(embed=result, view=None)

        view.add_item(AttackButton())

        # ───────── Envoi du message ─────────
        msg = await ctx.send(embed=embed, file=file, view=view)
        view.message = msg

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Hollow(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Reiatsu"
    await bot.add_cog(cog)
