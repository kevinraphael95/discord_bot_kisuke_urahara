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
from datetime import datetime, timedelta

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

    # ────────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction principale du RPG
    # ────────────────────────────────────────────────────────────────────────────────
    async def process_rpg(self, user_id, ctx, action, is_slash=False):
        # Création profil
        await create_profile_if_not_exists(user_id)

        # Récupération joueur
        res = supabase.table("rpg_players").select("*").eq("user_id", user_id).execute()
        if not res.data:
            error = "❌ Impossible de charger ton profil."
            return await (safe_respond(ctx, error) if is_slash else safe_send(ctx.channel, error))
        player_data = res.data[0]

        stats = player_data.get("stats", {})
        cooldowns = player_data.get("cooldowns", {})
        zone = str(player_data.get("zone", "1"))
        defeated = player_data.get("defeated_bosses", [])

        # ────────────────────────────────────────────────────────────
        # 🆕 Fonction send
        # ────────────────────────────────────────────────────────────
        async def send(content):
            if isinstance(content, discord.Embed):
                return await (safe_respond(ctx, embed=content) if is_slash else safe_send(ctx.channel, embed=content))
            else:
                return await (safe_respond(ctx, content) if is_slash else safe_send(ctx.channel, content))

        # ────────────────────────────────────────────────────────────
        # AUCUNE ACTION → MENU
        # ────────────────────────────────────────────────────────────
        if not action:
            embed = discord.Embed(
                title="🗡️ RPG Bleach",
                description=(
                    "Bienvenue dans le RPG inspiré de Bleach ! Tu es un shinigami rebelle ton but est de détruire la Soul Society. Tu affrontes toutes les divisions de la 12e à la 1ere.\n\n"
                    "**Commandes disponibles :**\n"
                    "`!rpg profil` — Statistiques et équipement\n"
                    "`!rpg combat` — Combat contre un shinigami de base\n"
                    "`!rpg boss` — Affronter un vice-capitaine puis un capitaine"
                ),
                color=discord.Color.red()
            )
            return await send(embed)

        action = action.lower()
        now = datetime.utcnow()

        # ────────────────────────────────────────────────────────────
        # VÉRIFICATION COOLDOWNS
        # ────────────────────────────────────────────────────────────
        if action == "combat":
            last = datetime.fromisoformat(cooldowns.get("combat", "1970-01-01T00:00:00"))
            if (now - last).total_seconds() < 300:
                remaining = int(300 - (now - last).total_seconds())
                return await send(f"⏳ Combat en cooldown. Patiente {remaining} secondes.")
            cooldowns["combat"] = now.isoformat()

        if action == "boss":
            last = datetime.fromisoformat(cooldowns.get("boss", "1970-01-01T00:00:00"))
            if (now - last).total_seconds() < 3600:
                remaining = int(3600 - (now - last).total_seconds())
                return await send(f"⏳ Boss en cooldown. Patiente {remaining} secondes.")
            cooldowns["boss"] = now.isoformat()

        # Met à jour les cooldowns dans la DB
        supabase.table("rpg_players").update({"cooldowns": cooldowns}).eq("user_id", user_id).execute()

        # ────────────────────────────────────────────────────────────
        # PROFIL
        # ────────────────────────────────────────────────────────────
        if action == "profil":
            embed = discord.Embed(
                title=f"📘 Profil de {ctx.user.name if is_slash else ctx.author.name}",
                color=discord.Color.blue()
            )
        
            # Stats principales
            embed.add_field(
                name="📊 Stats",
                value=(
                    f"Niveau: {stats.get('level',1)}\n"
                    f"XP: {stats.get('xp',0)}/{stats.get('xp_next',100)}\n"
                    f"HP / SP: {stats.get('hp',0)} / {stats.get('sp',0)}\n"
                    f"ATK / DEF: {stats.get('atk',0)} / {stats.get('def',0)}\n"
                    f"DEX / EVA: {stats.get('dex',0)} / {stats.get('eva',0)}\n"
                    f"Crit: {stats.get('crit',0)}"
                ),
                inline=False
            )
        
            # Effets actuels
            effects_text = ", ".join(stats.get("effects", {}).keys()) or "Aucun"
            embed.add_field(name="✨ Effets actifs", value=effects_text, inline=False)
        
            # Cooldowns
            CD_DURATIONS = {
                "combat": 300,  # 5 minutes
                "boss": 3600    # 1 heure
            }
            now = datetime.utcnow()
            cd_text = ""
            for cmd, dt_str in cooldowns.items():
                dt = datetime.fromisoformat(dt_str)
                elapsed = (now - dt).total_seconds()
                remaining = max(0, CD_DURATIONS.get(cmd, 0) - elapsed)
                ready = "✅ ready" if remaining <= 0 else str(timedelta(seconds=int(remaining)))
                cd_text += f"{cmd.upper()}: {ready}\n"
            embed.add_field(name="⏱️ Cooldowns", value=cd_text or "Aucun", inline=False)

        
            # Boss vaincus
            defeated_text = ", ".join(defeated) if defeated else "Aucun"
            embed.add_field(name="🏆 Boss vaincus", value=defeated_text, inline=False)
        
            # Zone actuelle
            embed.add_field(name="📍 Zone actuelle", value=f"{zone}", inline=False)
        
            return await send(embed)


        # ────────────────────────────────────────────────────────────
        # COMBAT / BOSS — RÉSUMÉ
        # ────────────────────────────────────────────────────────────
        is_boss = action == "boss"
        if is_boss:
            boss1 = ENEMIES[zone]["boss1"]
            boss2 = ENEMIES[zone]["boss2"]
            enemy = boss1 if boss1["name"] not in defeated else boss2
            if not enemy:
                embed = discord.Embed(
                    title="🎉 Division nettoyée",
                    description="Tous les capitaines de cette division ont été vaincus !",
                    color=discord.Color.green()
                )
                return await send(embed)
        else:
            enemy = ENEMIES[zone]["minions"][0]

        # Stats
        e_hp, e_atk, e_def, e_dex, e_crit = (
            enemy["hp"], enemy["atk"], enemy["def"],
            enemy.get("dex", 5), enemy.get("crit", 2)
        )
        p_hp, p_atk, p_def, p_dex, p_crit = (
            stats.get("hp",100), stats.get("atk",10), stats.get("def",5),
            stats.get("dex",5), stats.get("crit",5)
        )

        turn = 0
        while p_hp > 0 and e_hp > 0:
            turn += 1
            # Player attacks
            dmg = max(1, p_atk - e_def)
            if random.randint(1,100) <= p_crit*5: dmg *= 2
            e_hp -= dmg
            if e_hp <= 0: break
            # Enemy attacks
            dmg = max(1, e_atk - p_def)
            if random.randint(1,100) <= e_crit*5: dmg *= 2
            p_hp -= dmg

        # ────────────────────────────────────────────────────────────
        # Résultat résumé
        # ────────────────────────────────────────────────────────────
        if p_hp > 0:
            gain_xp = 200 if is_boss else 50
            stats["xp"] = stats.get("xp",0) + gain_xp
            stats["hp"] = p_hp
            if is_boss:
                defeated.append(enemy["name"])
                supabase.table("rpg_players").update({"defeated_bosses": defeated}).eq("user_id", user_id).execute()
            if stats["xp"] >= stats.get("xp_next",100):
                stats["level"] = stats.get("level",1) + 1
                stats["xp"] -= stats.get("xp_next",100)
                stats["xp_next"] = int(stats.get("xp_next",100) * 1.5)
            supabase.table("rpg_players").update({"stats": stats, "cooldowns": cooldowns}).eq("user_id", user_id).execute()

            embed = discord.Embed(
                title=f"⚔️ Combat contre {enemy['name']}",
                description=(
                    f"🏆 Vous avez vaincu {enemy['name']} !\n"
                    f"💖 PV restants : {p_hp}/{stats.get('hp',100)}\n"
                    f"⏳ Combats terminés en {turn} tours.\n"
                    f"💰 Vous gagnez {gain_xp} XP !"
                ),
                color=discord.Color.green()
            )
        else:
            stats["hp"] = max(1, int(stats.get("hp",100)*0.5))
            supabase.table("rpg_players").update({"stats": stats, "cooldowns": cooldowns}).eq("user_id", user_id).execute()

            embed = discord.Embed(
                title=f"⚔️ Combat contre {enemy['name']}",
                description=(
                    f"💀 Vous avez été vaincu par {enemy['name']}...\n"
                    f"💖 PV restants : {p_hp}/{stats.get('hp',100)}\n"
                    f"⏳ Combats terminés en {turn} tours."
                ),
                color=discord.Color.red()
            )

        return await send(embed)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = RPG(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Bleach"
    await bot.add_cog(cog)
