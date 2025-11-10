# ────────────────────────────────────────────────────────────────────────────────
# 📌 bleach_solo.py — Mini-JDR solo Bleach interactif avec choix par réactions
# Objectif : Jouer un mini-JDR solo avec zones, rencontres, objets, boss, combats interactifs
# Catégorie : Fun
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
import random, json
from utils.discord_utils import safe_send, safe_respond  # ✅ Utilitaires sécurisés

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class BleachSolo(commands.Cog):
    """
    Commande /jdrsolo et !jdrsolo — Mini-JDR solo Bleach interactif avec zones, rencontres, objets, boss
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        with open("data/bleach_solo_data.json", "r", encoding="utf-8") as f:
            self.data = json.load(f)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Tirer une carte aléatoire
    # ────────────────────────────────────────────────────────────────────────────
    def tirer_carte(self, pile):
        return random.choice(self.data[pile])

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Choix action par réaction
    # ────────────────────────────────────────────────────────────────────────────
    async def choix_action(self, ctx, joueur, ennemi):
        embed = discord.Embed(title=f"⚔️ Combat : {joueur['nom']} vs {ennemi['nom']}")
        embed.add_field(name="PV", value=f"{joueur['nom']}={joueur['pv']} | {ennemi['nom']}={ennemi.get('pv', 0)}")
        embed.add_field(name="Choix", value="⚔️ Attaque | 🔥 Bankai | 🧪 Objet")
        message = await safe_send(ctx, embed=embed)

        reactions = ["⚔️", "🔥", "🧪"]
        for r in reactions:
            await message.add_reaction(r)

        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in reactions and reaction.message.id == message.id

        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
        except:
            return "attaque"  # default

        if str(reaction.emoji) == "⚔️":
            return "attaque"
        elif str(reaction.emoji) == "🔥":
            return "bankai"
        elif str(reaction.emoji) == "🧪":
            return "objet"

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Lancer combat interactif
    # ────────────────────────────────────────────────────────────────────────────
    async def lancer_combat(self, ctx, joueur, ennemi):
        while joueur["pv"] > 0 and ennemi.get("pv", 5) > 0:
            action = await self.choix_action(ctx, joueur, ennemi)

            # Action joueur
            if action == "attaque":
                degat = random.randint(1, 6)
                ennemi["pv"] -= degat
                await safe_send(ctx, f"💥 {joueur['nom']} attaque et inflige {degat} dégâts !")
            elif action == "bankai":
                degat = random.randint(2, 6) + 2
                ennemi["pv"] -= degat
                await safe_send(ctx, f"🔥 {joueur['nom']} utilise Bankai et inflige {degat} dégâts !")
            elif action == "objet":
                if joueur["objets"]:
                    objet = joueur["objets"].pop()
                    degat = objet.get("attaque", objet.get("pv", 3))
                    await safe_send(ctx, f"🧪 {joueur['nom']} utilise {objet['nom']} et inflige {degat} dégâts !")
                    ennemi["pv"] -= degat
                else:
                    await safe_send(ctx, "❌ Pas d'objet disponible !")

            # Action ennemi
            if ennemi.get("pv", 5) > 0:
                degat_ennemi = random.randint(1, 6)
                joueur["pv"] -= degat_ennemi
                await safe_send(ctx, f"👹 {ennemi['nom']} attaque et inflige {degat_ennemi} dégâts !")

            await safe_send(ctx, f"PV: {joueur['nom']}={joueur['pv']} | {ennemi['nom']}={ennemi.get('pv', 0)}")

        if joueur["pv"] <= 0:
            await safe_send(ctx, "💀 Vous avez été vaincu !")
        else:
            await safe_send(ctx, f"🏆 Vous avez vaincu **{ennemi['nom']}** !")

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="jdrsolo",
        description="Lance le mini-JDR solo Bleach avec zones, rencontres et combats interactifs."
    )
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_jdrsolo(self, interaction: discord.Interaction):
        await safe_respond(interaction, "🎮 Début du mini-JDR solo Bleach !")
        joueur = {"nom": "Shinigami", "pv": 10, "objets": []}

        # Boucle zones
        for tour in range(3):
            zone = random.choice(self.data["zones"])
            effet = zone["d6"][str(random.randint(1, 6))]
            await safe_send(interaction, f"🌍 Zone: **{zone['nom']}** | Effet: {effet}")

            if "Rencontre" in effet or "rencontre" in effet:
                ennemi = self.tirer_carte("rencontres")
                if "pv" not in ennemi:
                    ennemi["pv"] = 5
                await self.lancer_combat(interaction, joueur, ennemi)
            elif "Objet" in effet or "Pouvoir" in effet:
                objet = self.tirer_carte("objets_pouvoirs")
                joueur["objets"].append(objet)
                await safe_send(interaction, f"🎁 Vous trouvez un objet : {objet['nom']}")
            elif "Événement" in effet or "evenement" in effet:
                evenement = self.tirer_carte("evenements")
                await safe_send(interaction, f"✨ Événement : {evenement}")
            else:
                await safe_send(interaction, "🌿 Rien à signaler dans cette zone.")

        # Boss final
        boss = self.tirer_carte("boss")
        if "pv" not in boss:
            boss["pv"] = 10
        await safe_send(interaction, f"👑 Boss final : {boss['nom']} !")
        await self.lancer_combat(interaction, joueur, boss)
        await safe_send(interaction, "🏁 Partie terminée !")

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="jdrsolo")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_jdrsolo(self, ctx: commands.Context):
        await self.slash_jdrsolo(ctx)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = BleachSolo(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Fun"
    await bot.add_cog(cog)
