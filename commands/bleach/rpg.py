# ────────────────────────────────────────────────────────────────────────────────
# 📌 rpg.py — Commande simple /rpg et !rpg
# Objectif : Présenter le RPG Soul Society avec combat et boss
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
from utils.discord_utils import safe_send, safe_respond
from utils.rpg_utils import create_profile_if_not_exists
from utils.supabase_client import supabase
import json
import random

with open("data/enemies.json", "r") as f:
    ENEMIES = json.load(f)

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class RPG(commands.Cog):
    """
    Commande /rpg et !rpg — RPG Soul Society
    """
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
        await create_profile_if_not_exists(user_id)

        player_data = supabase.table("rpg_players").select("*").eq("user_id", user_id).execute().data[0]
        zone = str(player_data["zone"])
        defeated = player_data.get("defeated_bosses", [])

        def send(msg):
            return safe_respond(ctx, msg) if is_slash else safe_send(ctx.channel, msg)

        if not action:
            msg = (
                "🗡️ **Bienvenue dans le RPG Soul Society !**\n\n"
                "Votre objectif : envahir les divisions de la Soul Society et affronter les capitaines !\n\n"
                "**Système de stats :**\n"
                "- Niveau / XP : gagnez de l'expérience pour monter de niveau\n"
                "- HP / SP : points de vie et points de compétence\n"
                "- ATK / DEF / DEX : Force, défense, agilité\n"
                "- Crit / EVA : chance de coup critique et esquive\n\n"
                "**Combat minions :** affrontez des Shinigami de la division actuelle.\n"
                "**Combat boss :** affrontez Boss1 (vice-capitaine) puis Boss2 (capitaine) si non vaincu.\n\n"
                "Commandes : `!rpg profil`, `!rpg combat`, `!rpg boss`"
            )
            await send(msg)
            return

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

        elif action in ["combat", "boss"]:
            is_boss = action == "boss"
            if is_boss:
                boss_data = ENEMIES[zone]["boss1"] if ENEMIES[zone]["boss1"]["name"] not in defeated else ENEMIES[zone]["boss2"]
                if not boss_data:
                    await send("✅ Vous avez déjà vaincu tous les boss de cette division !")
                    return
                enemy = boss_data
            else:
                enemy = ENEMIES[zone]["minions"][0]

            # Stats de l'ennemi
            e_hp = enemy["hp"]
            e_atk = enemy["atk"]
            e_def = enemy["def"]
            e_dex = enemy.get("dex", 5)
            e_crit = enemy.get("crit", 2)

            # Stats du joueur
            p_hp = player_data["hp"]
            p_atk = player_data["atk"]
            p_def = player_data["def"]
            p_dex = player_data["dex"]
            p_crit = player_data["crit"]

            turn = 1
            combat_log = []

            while p_hp > 0 and e_hp > 0:
                # ─ Joueur attaque ─
                hit_chance = random.randint(1, 100)
                if hit_chance <= p_dex * 5:
                    damage = max(0, p_atk - e_def)
                    if random.randint(1, 100) <= p_crit * 5:
                        damage *= 2
                        combat_log.append(f"Tour {turn}: Coup critique ! Vous infligez {damage} dégâts.")
                    else:
                        combat_log.append(f"Tour {turn}: Vous infligez {damage} dégâts.")
                    e_hp -= damage
                else:
                    combat_log.append(f"Tour {turn}: Vous avez manqué votre attaque !")

                if e_hp <= 0:
                    break

                # ─ Ennemi attaque ─
                hit_chance = random.randint(1, 100)
                if hit_chance <= e_dex * 5:
                    damage = max(0, e_atk - p_def)
                    if random.randint(1, 100) <= e_crit * 5:
                        damage *= 2
                        combat_log.append(f"Tour {turn}: {enemy['name']} critique ! Vous subissez {damage} dégâts.")
                    else:
                        combat_log.append(f"Tour {turn}: {enemy['name']} attaque et inflige {damage} dégâts.")
                    p_hp -= damage
                else:
                    combat_log.append(f"Tour {turn}: {enemy['name']} a manqué son attaque !")

                turn += 1

            # Résumé du combat
            result = "🎉 Vous avez vaincu l'ennemi !" if p_hp > 0 else "💀 Vous avez été vaincu..."
            combat_log.append(f"\nRésultat : {result}")
            combat_log.append(f"PV restants : {p_hp if p_hp>0 else 0}")
            combat_log.append(f"Nombre de tours : {turn-1}")

            # Mise à jour joueur
            if p_hp > 0:
                gain_xp = 50 if not is_boss else 200
                player_data["xp"] += gain_xp
                if is_boss:
                    defeated.append(enemy["name"])
                    supabase.table("rpg_players").update({"defeated_bosses": defeated}).eq("user_id", user_id).execute()
                # Montée de niveau simple
                if player_data["xp"] >= player_data["xp_next"]:
                    player_data["level"] += 1
                    player_data["xp"] = player_data["xp"] - player_data["xp_next"]
                    player_data["xp_next"] = int(player_data["xp_next"] * 1.5)
                player_data["hp"] = p_hp
                supabase.table("rpg_players").update(player_data).eq("user_id", user_id).execute()

            await send("\n".join(combat_log))

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = RPG(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Bleach"
    await bot.add_cog(cog)
