# ────────────────────────────────────────────────────────────────────────────────
# 📌 rpg.py — Commande simple /rpg et !rpg
# Objectif : RPG Soul Society (profil, combat et boss)
# Catégorie : Bleach
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────


# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
import json
import random

from utils.rpg_utils import create_profile_if_not_exists
from utils.supabase_client import supabase
from utils.discord_utils import safe_send, safe_respond

# ────────────────────────────────────────────────────────────────────────────────
# 📂 Chargement des ennemis depuis JSON
# ────────────────────────────────────────────────────────────────────────────────
with open("data/enemies.json", "r", encoding="utf-8") as f:
    ENEMIES = json.load(f)

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class RPG(commands.Cog):
    """Commande /rpg et !rpg — RPG Soul Society"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="rpg",
        description="Affiche le RPG Soul Society, profil, combat et boss"
    )
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_rpg(self, interaction: discord.Interaction, action: str = None):
        await self.process_rpg(interaction.user.id, interaction, action, is_slash=True)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="rpg")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_rpg(self, ctx: commands.Context, action: str = None):
        await self.process_rpg(ctx.author.id, ctx, action, is_slash=False)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction principale du RPG
    # ────────────────────────────────────────────────────────────────────────────
    async def process_rpg(self, user_id, ctx, action, is_slash=False):
        # ✅ Création du profil si inexistant
        await create_profile_if_not_exists(user_id)

        # Récupération des données du joueur
        res = supabase.table("rpg_players").select("*").eq("user_id", user_id).execute()
        if not res.data:
            return await (safe_respond(ctx, "❌ Impossible de charger ton profil.") if is_slash else safe_send(ctx.channel, "❌ Impossible de charger ton profil."))
        player_data = res.data[0]

        zone = str(player_data.get("zone", "1"))
        defeated = player_data.get("defeated_bosses", [])

        # Fonction interne d'envoi
        def send(msg):
            return safe_respond(ctx, msg) if is_slash else safe_send(ctx.channel, msg)

        # ─ Affichage d'accueil si aucune action ─
        if not action:
            msg = (
                "🗡️ **Bienvenue dans le RPG Soul Society !**\n\n"
                "Votre objectif : envahir les divisions de la Soul Society et affronter les capitaines !\n\n"
                "**Stats :** Niveau/XP, HP/SP, ATK/DEF/DEX, Crit/EVA\n"
                "**Commandes :** `!rpg profil`, `!rpg combat`, `!rpg boss`"
            )
            return await send(msg)

        action = action.lower()
        if action == "profil":
            msg = (
                f"**Profil de <@{user_id}>**\n"
                f"Niveau: {player_data['level']} | XP: {player_data['xp']}/{player_data['xp_next']}\n"
                f"HP: {player_data['hp']} | SP: {player_data['sp']}\n"
                f"ATK: {player_data['atk']} | DEF: {player_data['def']} | DEX: {player_data['dex']}\n"
                f"Crit: {player_data['crit']} | EVA: {player_data['eva']}\n"
                f"Équipement: {player_data['equipment']}"
            )
            await send(msg)
            return

        # ─ Combat (minions ou boss) ─
        is_boss = action == "boss"
        if is_boss:
            boss1 = ENEMIES[zone]["boss1"]
            boss2 = ENEMIES[zone]["boss2"]
            enemy = boss1 if boss1["name"] not in defeated else boss2
            if not enemy:
                return await send("✅ Tous les boss de cette division ont été vaincus !")
        else:
            enemy = ENEMIES[zone]["minions"][0]

        # ─ Stats combat ─
        e_hp, e_atk, e_def, e_dex, e_crit = enemy["hp"], enemy["atk"], enemy["def"], enemy.get("dex", 5), enemy.get("crit", 2)
        p_hp, p_atk, p_def, p_dex, p_crit = player_data["hp"], player_data["atk"], player_data["def"], player_data["dex"], player_data["crit"]

        turn = 1
        combat_log = []

        while p_hp > 0 and e_hp > 0:
            # Joueur attaque
            if random.randint(1, 100) <= p_dex * 5:
                dmg = max(0, p_atk - e_def)
                if random.randint(1, 100) <= p_crit * 5:
                    dmg *= 2
                    combat_log.append(f"Tour {turn}: Coup critique ! Vous infligez {dmg} dégâts.")
                else:
                    combat_log.append(f"Tour {turn}: Vous infligez {dmg} dégâts.")
                e_hp -= dmg
            else:
                combat_log.append(f"Tour {turn}: Vous avez manqué votre attaque !")
            if e_hp <= 0:
                break

            # Ennemi attaque
            if random.randint(1, 100) <= e_dex * 5:
                dmg = max(0, e_atk - p_def)
                if random.randint(1, 100) <= e_crit * 5:
                    dmg *= 2
                    combat_log.append(f"Tour {turn}: {enemy['name']} critique ! Vous subissez {dmg} dégâts.")
                else:
                    combat_log.append(f"Tour {turn}: {enemy['name']} attaque et inflige {dmg} dégâts.")
                p_hp -= dmg
            else:
                combat_log.append(f"Tour {turn}: {enemy['name']} a manqué son attaque !")

            turn += 1

        # ─ Résultat ─
        result = "🎉 Vous avez vaincu l'ennemi !" if p_hp > 0 else "💀 Vous avez été vaincu..."
        combat_log.append(f"\nRésultat : {result}")
        combat_log.append(f"PV restants : {max(0, p_hp)}")
        combat_log.append(f"Nombre de tours : {turn-1}")

        # Mise à jour joueur
        if p_hp > 0:
            gain_xp = 200 if is_boss else 50
            player_data["xp"] += gain_xp
            if is_boss:
                defeated.append(enemy["name"])
                supabase.table("rpg_players").update({"defeated_bosses": defeated}).eq("user_id", user_id).execute()

            # Montée de niveau simple
            if player_data["xp"] >= player_data["xp_next"]:
                player_data["level"] += 1
                player_data["xp"] -= player_data["xp_next"]
                player_data["xp_next"] = int(player_data["xp_next"] * 1.5)
            player_data["hp"] = p_hp
            supabase.table("rpg_players").update(player_data).eq("user_id", user_id).execute()

        await send("\n".join(combat_log))

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = RPG(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Bleach"
    await bot.add_cog(cog)
