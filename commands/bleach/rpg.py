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
    async def slash_rpg(self, interaction: discord.Interaction, action: str = None, zone_target: str = None):
        await self.process_rpg(interaction.user.id, interaction, action, zone_target, is_slash=True)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="rpg")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_rpg(self, ctx: commands.Context, action: str = None, zone_target: str = None):
        await self.process_rpg(ctx.author.id, ctx, action, zone_target, is_slash=False)

    # ────────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction principale du RPG
    # ────────────────────────────────────────────────────────────────────────────────
    async def process_rpg(self, user_id, ctx, action, zone_target=None, is_slash=False):
        # Création profil si inexistant
        username = ctx.user.name if is_slash else ctx.author.name
        await create_profile_if_not_exists(user_id, username)

        # Récupération joueur
        res = supabase.table("rpg_players").select("*").eq("user_id", user_id).execute()
        if not res.data:
            error = "❌ Impossible de charger ton profil."
            return await (safe_respond(ctx, error) if is_slash else safe_send(ctx.channel, error))
        player_data = res.data[0]

        stats = player_data.get("stats", {})
        cooldowns = player_data.get("cooldowns", {})
        zone = str(player_data.get("zone", "1"))
        unlocked_zones = player_data.get("unlocked_zones", ["1"])

        # ────────────────────────────────────────────────────────────
        # 🆕 Fonction send simplifiée
        # ────────────────────────────────────────────────────────────
        async def send(content):
            if isinstance(content, discord.Embed):
                return await (safe_respond(ctx, embed=content) if is_slash else safe_send(ctx.channel, embed=content))
            return await (safe_respond(ctx, content) if is_slash else safe_send(ctx.channel, content))

        now = datetime.utcnow()

        # ────────────────────────────────────────────────────────────
        # AUCUNE ACTION → MENU
        # ────────────────────────────────────────────────────────────
        if not action:
            embed = discord.Embed(
                title="🗡️ RPG Bleach",
                description=(
                    "Bienvenue dans le RPG inspiré de Bleach ! Tu es un shinigami rebelle et ton but est de détruire la Soul Society.\n\n"
                    "**Commandes disponibles :**\n"
                    "`!rpg profil` — Statistiques et équipement\n"
                    "`!rpg combat` — Combat contre un shinigami de base\n"
                    "`!rpg boss` — Affronter un vice-capitaine puis un capitaine\n"
                    "`!rpg zone` — Voir les zones débloquées et se déplacer\n\n"
                    "**Comment Jouer :**\n"
                    "Affronter les 13 Divisions des 13 armées de la cour, faire des combhat pour monter les stats puis battre les 2 boss de chaque zone pour passer à la suivante avec rpg zone."
                ),
                color=discord.Color.red()
            )
            return await send(embed)

        action = action.lower()

        # ────────────────────────────────────────────────────────────
        # 📌 Cooldowns combat / boss
        # ────────────────────────────────────────────────────────────
        CD_DURATIONS = {"combat": 300, "boss": 3600}

        if action in ["combat", "boss"]:
            last_str = cooldowns.get(action, "1970-01-01T00:00:00")
            last = datetime.fromisoformat(last_str)
            elapsed = (now - last).total_seconds()
            if elapsed < CD_DURATIONS[action]:
                remaining = CD_DURATIONS[action] - elapsed
                return await send(f"⏳ **{action.upper()}** en cooldown — reviens dans `{str(timedelta(seconds=int(remaining)))}`.")
            cooldowns[action] = now.isoformat()
            supabase.table("rpg_players").update({"cooldowns": cooldowns}).eq("user_id", user_id).execute()

        # ────────────────────────────────────────────────────────────
        # PROFIL
        # ────────────────────────────────────────────────────────────
        if action == "profil":
            embed = discord.Embed(
                title=f"📘 Profil de {player_data.get('username', username)}",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="📊 Stats",
                value=(
                    f"Niveau: {stats.get('level',1)} (XP: {stats.get('xp',0)}/{stats.get('xp_next',100)})\n"
                    f"💖 HP : {stats.get('hp',0)} / {stats.get('hp_max',100)}\n"
                    f"🔮 SP : {stats.get('sp',0)}\n"
                    f"⚔️ ATK : {stats.get('atk',0)} / 🛡️ DEF: {stats.get('def',0)}\n"
                    f"🤺 DEX : {stats.get('dex',0)} / 🏃 EVA: {stats.get('eva',0)}\n"
                    f"🎯 Crit: {stats.get('crit',0)}"
                ),
                inline=False
            )
            embed.add_field(name="✨ Effets actifs", value=", ".join(stats.get("effects", {}).keys()) or "Aucun", inline=False)

            cd_text = ""
            for cmd, dt_str in cooldowns.items():
                dt = datetime.fromisoformat(dt_str)
                elapsed = (now - dt).total_seconds()
                remaining = max(0, CD_DURATIONS.get(cmd, 0) - elapsed)
                cd_text += f"{cmd.upper()}: {'✅ ready' if remaining <= 0 else str(timedelta(seconds=int(remaining)))}\n"
            embed.add_field(name="⏱️ Cooldowns", value=cd_text or "Aucun", inline=False)

            embed.add_field(name="🗺️ Zones débloquées", value=", ".join(unlocked_zones), inline=False)
            embed.add_field(name="📍 Zone actuelle", value=zone, inline=False)
            return await send(embed)

        # ────────────────────────────────────────────────────────────
        # ZONE / MAP
        # ────────────────────────────────────────────────────────────
        if action in ["zone", "map"]:
            if zone_target:
                if zone_target in unlocked_zones:
                    zone = zone_target
                    supabase.table("rpg_players").update({"zone": zone}).eq("user_id", user_id).execute()
                    return await send(f"📍 Vous vous déplacez vers la zone {zone}.")
                return await send(f"❌ Vous ne pouvez pas accéder à la zone {zone_target}, elle n'est pas débloquée.")
            embed = discord.Embed(
                title="🗺️ Zones débloquées",
                description=", ".join(unlocked_zones),
                color=discord.Color.orange()
            )
            embed.add_field(name="Zone actuelle", value=zone)
            return await send(embed)

        # ────────────────────────────────────────────────────────────
        # COMBAT / BOSS
        # ────────────────────────────────────────────────────────────
        is_boss = action == "boss"
        if is_boss:
            boss1, boss2 = ENEMIES[zone]["boss1"], ENEMIES[zone]["boss2"]
            enemy = boss1 if boss1["name"] not in unlocked_zones else boss2
            if not enemy:
                return await send(discord.Embed(
                    title="🎉 Division nettoyée",
                    description="Tous les capitaines ont été vaincus !",
                    color=discord.Color.green()
                ))
        else:
            enemy = ENEMIES[zone]["minions"][0]

        # Stats joueur
        p_stats = {k: stats.get(k, default) for k, default in [("hp", 100), ("hp_max",100), ("atk",10), ("def",5), ("dex",5), ("eva",5), ("crit",5)]}
        # Stats ennemi
        e_stats = {k: enemy.get(k, default) for k, default in [("hp",100), ("atk",10), ("def",5), ("dex",5), ("eva",5), ("crit",2)]}
        e_stats["crit"] *= 5
        p_stats["crit"] *= 5

        def attempt_attack(atk, defense, crit_chance):
            dmg = max(1, atk - defense)
            if random.randint(1, 100) <= crit_chance:
                dmg = int(dmg * 1.2)
            return dmg

        combat_log, turn = [], 0
        while p_stats["hp"] > 0 and e_stats["hp"] > 0:
            turn += 1
            # Tour joueur
            if random.randint(1, 100) > e_stats["eva"]:
                dmg = attempt_attack(p_stats["atk"], e_stats["def"], p_stats["crit"])
                e_stats["hp"] -= dmg
                combat_log.append(f"Tour {turn} — Vous attaquez {enemy['name']} et infligez {dmg} dmg (PV restants: {max(0,e_stats['hp'])})")
            else:
                combat_log.append(f"Tour {turn} — {enemy['name']} a esquivé votre attaque !")

            if random.randint(1, 100) <= p_stats["dex"]:
                if random.randint(1, 100) > e_stats["eva"]:
                    dmg = attempt_attack(p_stats["atk"], e_stats["def"], p_stats["crit"])
                    e_stats["hp"] -= dmg
                    combat_log.append(f"Tour {turn} — Double attaque ! Vous infligez {dmg} dmg à {enemy['name']} (PV restants: {max(0,e_stats['hp'])})")
                else:
                    combat_log.append(f"Tour {turn} — {enemy['name']} a esquivé votre double attaque !")
            if e_stats["hp"] <= 0: break

            # Tour ennemi
            if random.randint(1, 100) > p_stats["eva"]:
                dmg = attempt_attack(e_stats["atk"], p_stats["def"], e_stats["crit"])
                p_stats["hp"] -= dmg
                combat_log.append(f"Tour {turn} — {enemy['name']} vous attaque et inflige {dmg} dmg (Vos PV: {max(0,p_stats['hp'])})")
            else:
                combat_log.append(f"Tour {turn} — Vous avez esquivé l'attaque de {enemy['name']} !")

            if random.randint(1, 100) <= e_stats["dex"]:
                if random.randint(1, 100) > p_stats["eva"]:
                    dmg = attempt_attack(e_stats["atk"], p_stats["def"], e_stats["crit"])
                    p_stats["hp"] -= dmg
                    combat_log.append(f"Tour {turn} — Double attaque de {enemy['name']} ! {dmg} dmg (Vos PV: {max(0,p_stats['hp'])})")
                else:
                    combat_log.append(f"Tour {turn} — Vous avez esquivé la double attaque de {enemy['name']} !")

        # ────────────────────────────────────────────────────────────
        # Fin combat — mise à jour stats
        # ────────────────────────────────────────────────────────────
        if p_stats["hp"] > 0:
            gain_xp = 200 if is_boss else 50
            stats["xp"] = stats.get("xp",0) + gain_xp
            stats["hp"] = p_stats["hp"]
            if is_boss:
                next_zone = str(int(zone)+1)
                if next_zone not in unlocked_zones and next_zone in ENEMIES:
                    unlocked_zones.append(next_zone)
                    supabase.table("rpg_players").update({"unlocked_zones": unlocked_zones}).eq("user_id", user_id).execute()
            if stats["xp"] >= stats.get("xp_next",100):
                stats["level"] = stats.get("level",1)+1
                stats["xp"] -= stats.get("xp_next",100)
                stats["xp_next"] = int(stats.get("xp_next",100)*1.5)

            supabase.table("rpg_players").update({"stats": stats,"cooldowns": cooldowns,"zone": zone}).eq("user_id", user_id).execute()

            embed = discord.Embed(
                title=f"⚔️ Combat contre {enemy['name']}",
                description=(
                    f"🏆 Vous avez vaincu {enemy['name']} !\n"
                    f"💖 Vos PV : {p_stats['hp']}/{p_stats['hp_max']}\n"
                    f"💀 PV ennemi : 0/{e_stats['hp']}\n"
                    f"⏳ Combats terminés en {turn} tours.\n"
                    f"💰 Vous gagnez {gain_xp} XP !"
                ),
                color=discord.Color.green()
            )
        else:
            stats["hp"] = max(1, int(p_stats["hp_max"]*0.5))
            supabase.table("rpg_players").update({"stats": stats,"cooldowns": cooldowns}).eq("user_id", user_id).execute()

            embed = discord.Embed(
                title=f"⚔️ Combat contre {enemy['name']}",
                description=(
                    f"💀 Vous avez été vaincu par {enemy['name']}...\n"
                    f"💖 Vos PV : 0/{p_stats['hp_max']}\n"
                    f"💀 PV ennemi : {max(0,e_stats['hp'])}/{e_stats['hp']}\n"
                    f"⏳ Combats terminés en {turn} tours."
                ),
                color=discord.Color.red()
            )

        # ────────────────────────────────────────────────────────────
        # Logs interactifs
        # ────────────────────────────────────────────────────────────
        from discord.ui import View, Button

        class CombatLogView(View):
            def __init__(self, log):
                super().__init__(timeout=None)
                self.pages = [log[i:i+15] for i in range(0,len(log),15)]
                self.current_page = 0

            def get_embed(self):
                page = self.pages[self.current_page]
                return discord.Embed(
                    title=f"📜 Logs du combat ({self.current_page+1}/{len(self.pages)})",
                    description="\n".join(page),
                    color=discord.Color.blurple()
                )

            @discord.ui.button(label="Voir les logs", style=discord.ButtonStyle.blurple)
            async def show_log(self, interaction: discord.Interaction, button: Button):
                await interaction.response.send_message(embed=self.get_embed(), ephemeral=True, view=self)

            @discord.ui.button(label="⬅️", style=discord.ButtonStyle.secondary)
            async def previous(self, interaction: discord.Interaction, button: Button):
                if self.current_page > 0: self.current_page -= 1
                await interaction.response.edit_message(embed=self.get_embed(), view=self)

            @discord.ui.button(label="➡️", style=discord.ButtonStyle.secondary)
            async def next(self, interaction: discord.Interaction, button: Button):
                if self.current_page < len(self.pages)-1: self.current_page += 1
                await interaction.response.edit_message(embed=self.get_embed(), view=self)

        view = CombatLogView(combat_log)
        if is_slash:
            await ctx.followup.send(embed=embed, view=view)
        else:
            await ctx.send(embed=embed, view=view)


# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup Cog
# ────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = RPG(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Bleach"
    await bot.add_cog(cog)
