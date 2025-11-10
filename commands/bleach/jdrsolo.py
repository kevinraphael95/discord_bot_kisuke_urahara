# ────────────────────────────────────────────────────────────────────────────────
# 📌 bleach_solo.py — Mini-JDR solo Bleach interactif avec choix par réactions
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
import random, json
from utils.discord_utils import safe_send, safe_respond

class BleachSolo(commands.Cog):
    """Mini-JDR solo Bleach avec zones, rencontres, objets, boss et événements."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        with open("data/bleach_solo_data.json", "r", encoding="utf-8") as f:
            self.data = json.load(f)

    # Tirer une carte aléatoire
    def tirer_carte(self, pile):
        return random.choice(self.data[pile])

    # Choix d'action par réaction
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
            return "attaque"

        return {
            "⚔️": "attaque",
            "🔥": "bankai",
            "🧪": "objet"
        }[str(reaction.emoji)]

    # Lancer combat interactif
    async def lancer_combat(self, ctx, joueur, ennemi):
        await safe_send(ctx, f"⚔️ Un combat commence contre **{ennemi['nom']}** !")

        while joueur["pv"] > 0 and ennemi.get("pv", 5) > 0:
            action = await self.choix_action(ctx, joueur, ennemi)

            # Action joueur
            if action == "attaque":
                degat = random.randint(1, 6)
                degat += joueur.get("bonus_attaque", 0)
                ennemi["pv"] -= degat
                await safe_send(ctx, f"💥 {joueur['nom']} attaque et inflige {degat} dégâts !")

            elif action == "bankai":
                degat = random.randint(2, 6) + 2
                degat += joueur.get("bonus_attaque", 0)
                ennemi["pv"] -= degat
                await safe_send(ctx, f"🔥 {joueur['nom']} utilise Bankai et inflige {degat} dégâts !")

            elif action == "objet":
                if joueur["objets"]:
                    objet = joueur["objets"].pop()
                    degat = objet.get("attaque", objet.get("pv", 0))
                    bonus = objet.get("bonus", 0)
                    joueur["bonus_attaque"] = joueur.get("bonus_attaque", 0) + bonus
                    ennemi["pv"] -= degat
                    await safe_send(ctx, f"🧪 {joueur['nom']} utilise {objet['nom']} et inflige {degat} dégâts !")
                else:
                    await safe_send(ctx, "❌ Pas d'objet disponible !")

            # Action ennemi
            if ennemi.get("pv", 0) > 0:
                degat_ennemi = random.randint(1, 6)
                joueur["pv"] -= degat_ennemi
                await safe_send(ctx, f"👹 {ennemi['nom']} attaque et inflige {degat_ennemi} dégâts !")

            joueur["pv"] = max(joueur["pv"], 0)
            ennemi["pv"] = max(ennemi.get("pv", 0), 0)
            await safe_send(ctx, f"📊 PV restants : {joueur['nom']}={joueur['pv']} | {ennemi['nom']}={ennemi.get('pv', 0)}")

        if joueur["pv"] <= 0:
            await safe_send(ctx, "💀 Vous avez été vaincu !")
            return False
        else:
            await safe_send(ctx, f"🏆 Vous avez vaincu **{ennemi['nom']}** !")
            return True

    # Appliquer un événement
    async def appliquer_evenement(self, ctx, joueur, effet):
        if "Tempête" in effet:
            joueur["bonus_attaque"] = max(joueur.get("bonus_attaque", 0) -1, 0)
            await safe_send(ctx, "🌪️ Tempête spirituelle : -1 à tous les jets !")
        elif "Ruine" in effet:
            joueur["pv"] -= 1
            await safe_send(ctx, "🏚️ Ruine partielle : -1 PV")
        elif "Piège" in effet:
            perte = random.choice([1,0])
            joueur["pv"] -= perte
            await safe_send(ctx, f"⚠️ Piège spirituel : -{perte} PV")
        elif "Renforts" in effet:
            ennemi = self.tirer_carte("rencontres")
            ennemi.setdefault("pv", 5)
            await safe_send(ctx, f"👹 Renforts ennemis : **{ennemi['nom']}** apparaît !")
            await self.lancer_combat(ctx, joueur, ennemi)
        elif "Objet caché" in effet:
            objet = self.tirer_carte("objets_pouvoirs")
            joueur["objets"].append(objet)
            await safe_send(ctx, f"🎁 Objet caché trouvé : {objet['nom']}")
        elif "Distorsion" in effet:
            await safe_send(ctx, "⏳ Distorsion temporelle : relance le dé pour cette zone !")
        elif "Zone purifiée" in effet:
            joueur["bonus_attaque"] = joueur.get("bonus_attaque",0) +1
            await safe_send(ctx, "✨ Zone purifiée : +1 attaque")
        elif "Vision" in effet:
            bonus = random.randint(1,6)
            joueur["bonus_attaque"] = joueur.get("bonus_attaque",0) + bonus
            await safe_send(ctx, f"👀 Vision d'Ichigo : +{bonus} attaque pour le prochain combat")
        elif "Malédiction" in effet:
            joueur["bonus_attaque"] = max(joueur.get("bonus_attaque",0)-1,0)
            await safe_send(ctx, "🔮 Malédiction spirituelle : -1 attaque prochain tour")
        elif "Chance" in effet:
            objet = self.tirer_carte("objets_pouvoirs")
            joueur["objets"].append(objet)
            await safe_send(ctx, f"🍀 Chance inespérée : vous obtenez {objet['nom']}")

    # Jouer le mini-JDR
    async def jouer_jdr(self, ctx_or_inter, user):
        await safe_send(ctx_or_inter, f"🎮 Début du mini-JDR solo Bleach pour **{user.display_name}** !")
        joueur = {"nom": "Shinigami", "pv": 10, "objets": [], "bonus_attaque": 0}

        # Boucle zones
        for tour in range(3):
            zone = random.choice(self.data["zones"])
            effet = zone["d6"][str(random.randint(1,6))]
            await safe_send(ctx_or_inter, f"🌍 Zone : **{zone['nom']}** | Effet : {effet}")

            if "Rencontre" in effet or "rencontre" in effet:
                ennemi = self.tirer_carte("rencontres")
                ennemi.setdefault("pv", 5)
                success = await self.lancer_combat(ctx_or_inter, joueur, ennemi)
                if not success:
                    return
            elif "Objet" in effet or "Pouvoir" in effet:
                objet = self.tirer_carte("objets_pouvoirs")
                joueur["objets"].append(objet)
                await safe_send(ctx_or_inter, f"🎁 Vous trouvez un objet : {objet['nom']}")
            elif "Événement" in effet or "evenement" in effet:
                evenement = self.tirer_carte("evenements")
                await self.appliquer_evenement(ctx_or_inter, joueur, evenement)

        # Combat final contre boss
        boss = self.tirer_carte("boss")
        boss.setdefault("pv", 10)
        await safe_send(ctx_or_inter, f"🏹 Combat final contre **{boss['nom']}** !")
        await self.lancer_combat(ctx_or_inter, joueur, boss)

    # Commande slash
    @app_commands.command(name="jdrsolo", description="Lance le mini-JDR solo Bleach.")
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_jdrsolo(self, interaction: discord.Interaction):
        await self.jouer_jdr(interaction, interaction.user)

    # Commande prefix
    @commands.command(name="jdrsolo")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_jdrsolo(self, ctx: commands.Context):
        await self.jouer_jdr(ctx, ctx.author)

# Setup Cog
async def setup(bot: commands.Bot):
    cog = BleachSolo(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Fun"
    await bot.add_cog(cog)
