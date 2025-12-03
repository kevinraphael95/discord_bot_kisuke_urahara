# ────────────────────────────────────────────────────────────────────────────────
# 📌 rpg_combat.py — Gestion des combats RPG (compatible slash + prefix)
# ────────────────────────────────────────────────────────────────────────────────

import random
from datetime import datetime
import discord
from utils.supabase_client import supabase
from utils.rpg_utils import update_player_stats
from utils.rpg_classes import get_class_effects  # ✅ Import pour les effets de classe

# ────────────────────────────────────────────────────────────
# Fonction d'attaque
# ────────────────────────────────────────────────────────────
def attempt_attack(atk, defense, crit_chance):
    dmg = max(1, atk - defense)
    if random.randint(1, 100) <= crit_chance:
        dmg = int(dmg * 1.2)
    return dmg

# ────────────────────────────────────────────────────────────
# Fonction principale du combat
# ────────────────────────────────────────────────────────────
async def run_combat(user_id, is_boss, zone, stats, cooldowns, send, ENEMIES, player_data=None):
    now = datetime.utcnow()

    # Choix de l'ennemi
    if is_boss:
        boss1, boss2 = ENEMIES[zone]["boss1"], ENEMIES[zone]["boss2"]
        unlocked = player_data.get("unlocked_zones", []) if player_data else []
        enemy = boss1 if boss1["name"] not in unlocked else boss2
        if not enemy:
            return await send(discord.Embed(
                title="🎉 Division nettoyée",
                description="Tous les capitaines ont été vaincus !",
                color=discord.Color.green()
            ))
    else:
        enemy = ENEMIES[zone]["minions"][0]

    # Stats joueur / ennemi
    p_stats = {k: stats.get(k, default) for k, default in [("hp", 100), ("hp_max",100), ("atk",10), ("def",5), ("dex",5), ("eva",5), ("crit",5)]}
    e_stats = {k: enemy.get(k, default) for k, default in [("hp",100), ("atk",10), ("def",5), ("dex",5), ("eva",5), ("crit",2)]}
    e_stats["crit"] *= 5
    p_stats["crit"] *= 5

    # ────────────────────────────────────────────────────────────
    # Effets de classe
    # ────────────────────────────────────────────────────────────
    class_effects = get_class_effects(player_data.get("class")) if player_data else {}

    combat_log, turn = [], 0

    # ────────────────────────────────────────────────────────────
    # Boucle combat
    # ────────────────────────────────────────────────────────────
    while p_stats["hp"] > 0 and e_stats["hp"] > 0:
        turn += 1

        # --- TOUR JOUEUR ---
        if random.randint(1, 100) > e_stats["eva"]:
            dmg = attempt_attack(p_stats["atk"], e_stats["def"], p_stats["crit"])

            # BERSERKER : +10% ATK si HP <50%
            if "atk_bonus_below_50" in class_effects and p_stats["hp"] < p_stats["hp_max"] * 0.5:
                dmg = int(dmg * (1 + class_effects["atk_bonus_below_50"] / 100))

            # STRATEGIST : coups critiques infligent +40%
            if "crit_multiplier" in class_effects and random.randint(1,100) <= p_stats["crit"]:
                dmg = int(dmg * class_effects["crit_multiplier"])

            e_stats["hp"] -= dmg

            # HYBRID : lifesteal
            if "lifesteal_percent" in class_effects:
                heal = int(dmg * class_effects["lifesteal_percent"] / 100)
                p_stats["hp"] = min(p_stats["hp_max"], p_stats["hp"] + heal)

            combat_log.append(f"Tour {turn} — Vous attaquez {enemy['name']} et infligez {dmg} dmg (PV restants: {max(0,e_stats['hp'])})")
        else:
            combat_log.append(f"Tour {turn} — {enemy['name']} a esquivé votre attaque !")

        # Double attaque ASSASSIN
        if "double_attack_chance" in class_effects and random.randint(1,100) <= class_effects["double_attack_chance"]:
            if random.randint(1, 100) > e_stats["eva"]:
                dmg = attempt_attack(p_stats["atk"], e_stats["def"], p_stats["crit"])
                e_stats["hp"] -= dmg
                combat_log.append(f"Tour {turn} — Double attaque ! Vous infligez {dmg} dmg à {enemy['name']} (PV restants: {max(0,e_stats['hp'])})")
            else:
                combat_log.append(f"Tour {turn} — {enemy['name']} a esquivé votre double attaque !")

        if e_stats["hp"] <= 0: break

        # --- TOUR ENNEMI ---
        if random.randint(1, 100) > p_stats["eva"]:
            dmg = attempt_attack(e_stats["atk"], p_stats["def"], e_stats["crit"])

            # TANK : réduction des dégâts subis
            if "reduce_damage_percent" in class_effects:
                dmg = int(dmg * (1 - class_effects["reduce_damage_percent"]/100))

            # SPIRITUALIST : chance d'annuler les dégâts
            if "chance_block_damage" in class_effects and random.randint(1,100) <= class_effects["chance_block_damage"]:
                dmg = 0

            p_stats["hp"] -= dmg
            combat_log.append(f"Tour {turn} — {enemy['name']} vous attaque et inflige {dmg} dmg (Vos PV: {max(0,p_stats['hp'])})")
        else:
            combat_log.append(f"Tour {turn} — Vous avez esquivé l'attaque de {enemy['name']} !")

        if random.randint(1, 100) <= e_stats["dex"]:
            if random.randint(1, 100) > p_stats["eva"]:
                dmg = attempt_attack(e_stats["atk"], p_stats["def"], e_stats["crit"])

                # TANK / SPIRITUALIST encore appliqué
                if "reduce_damage_percent" in class_effects:
                    dmg = int(dmg * (1 - class_effects["reduce_damage_percent"]/100))
                if "chance_block_damage" in class_effects and random.randint(1,100) <= class_effects["chance_block_damage"]:
                    dmg = 0

                p_stats["hp"] -= dmg
                combat_log.append(f"Tour {turn} — Double attaque de {enemy['name']} ! {dmg} dmg (Vos PV: {max(0,p_stats['hp'])})")
            else:
                combat_log.append(f"Tour {turn} — Vous avez esquivé la double attaque de {enemy['name']} !")

    # ────────────────────────────────────────────────────────────
    # Mise à jour stats joueur
    # ────────────────────────────────────────────────────────────
    gain_xp = 200 if is_boss else 50
    stats["xp"] = stats.get("xp",0) + gain_xp
    stats["hp"] = max(1, p_stats["hp"])

    if stats["xp"] >= stats.get("xp_next",100):
        stats["level"] = stats.get("level",1)+1
        stats["xp"] -= stats.get("xp_next",100)
        stats["xp_next"] = int(stats.get("xp_next",100)*1.5)

    await update_player_stats(user_id, stats, cooldowns)

    # ────────────────────────────────────────────────────────────
    # Embed combat final
    # ────────────────────────────────────────────────────────────
    if p_stats["hp"] > 0:
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
    await send(embed, view=view)
