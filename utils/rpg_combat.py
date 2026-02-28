# ────────────────────────────────────────────────────────────────────────────────
# 📌 rpg_combat.py — Gestion des combats RPG (compatible slash + prefix)
# ────────────────────────────────────────────────────────────────────────────────

import random
import json
import os
import sqlite3
from datetime import datetime
import discord
from discord.ui import View, Button

from utils.rpg_utils import update_player_stats
from utils.rpg_classes import get_class_effects

DB_PATH = os.path.join("database", "reiatsu.db")

def get_conn():
    return sqlite3.connect(DB_PATH)

# ────────────────────────────────────────────────────────────────────────────────
# 🔹 Unlock de zone après victoire boss
# ────────────────────────────────────────────────────────────────────────────────
def _try_unlock_next_zone(user_id: int, zone: str, unlocked_zones: list, boss_name: str) -> tuple[list, str | None]:
    """Tente de débloquer la zone suivante. Retourne (unlocked_zones_maj, message|None)."""
    next_zone = str(int(zone) + 1)
    if next_zone not in unlocked_zones:
        unlocked_zones = unlocked_zones + [next_zone]
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE rpg_players SET unlocked_zones = ? WHERE user_id = ?",
            (json.dumps(unlocked_zones), user_id)
        )
        conn.commit()
        conn.close()
        return unlocked_zones, f"🎉 Zone **{next_zone}** débloquée après la victoire contre **{boss_name}** !"
    return unlocked_zones, None

# ────────────────────────────────────────────────────────────────────────────────
# 🔹 Calcul d'une attaque
# ────────────────────────────────────────────────────────────────────────────────
def attempt_attack(atk: int, defense: int, crit_chance: int) -> tuple[int, bool]:
    """Retourne (dégâts, est_critique)."""
    dmg = max(1, atk - defense)
    is_crit = random.randint(1, 100) <= crit_chance
    if is_crit:
        dmg = int(dmg * 1.2)
    return dmg, is_crit

# ────────────────────────────────────────────────────────────────────────────────
# 🔹 Vue logs interactifs
# ────────────────────────────────────────────────────────────────────────────────
class CombatLogView(View):
    def __init__(self, log: list[str]):
        super().__init__(timeout=120)
        self.pages = [log[i:i+15] for i in range(0, len(log), 15)]
        self.current_page = 0

    def get_embed(self) -> discord.Embed:
        page = self.pages[self.current_page]
        return discord.Embed(
            title=f"📜 Logs du combat ({self.current_page + 1}/{len(self.pages)})",
            description="\n".join(page),
            color=discord.Color.blurple()
        )

    @discord.ui.button(label="Voir les logs", style=discord.ButtonStyle.blurple)
    async def show_log(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message(embed=self.get_embed(), ephemeral=True, view=CombatLogPager(self.pages))

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True


class CombatLogPager(View):
    """Vue de pagination pour les logs en éphémère."""
    def __init__(self, pages: list):
        super().__init__(timeout=120)
        self.pages = pages
        self.current_page = 0

    def get_embed(self) -> discord.Embed:
        return discord.Embed(
            title=f"📜 Logs ({self.current_page + 1}/{len(self.pages)})",
            description="\n".join(self.pages[self.current_page]),
            color=discord.Color.blurple()
        )

    @discord.ui.button(label="⬅️", style=discord.ButtonStyle.secondary)
    async def previous(self, interaction: discord.Interaction, button: Button):
        if self.current_page > 0:
            self.current_page -= 1
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="➡️", style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction: discord.Interaction, button: Button):
        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

# ────────────────────────────────────────────────────────────────────────────────
# 🔹 Fonction principale du combat
# ────────────────────────────────────────────────────────────────────────────────
async def run_combat(user_id: int, is_boss: bool, zone: str, stats: dict, cooldowns: dict, send, ENEMIES: dict, player_data: dict = None):

    # ── Sélection de l'ennemi ────────────────────────────────────────────────
    if is_boss:
        boss1 = ENEMIES[zone]["boss1"]
        boss2 = ENEMIES[zone]["boss2"]
        unlocked = player_data.get("unlocked_zones", []) if player_data else []
        enemy = boss1 if boss1["name"] not in unlocked else boss2
        if not enemy:
            return await send(discord.Embed(
                title="🎉 Division nettoyée !",
                description="Tous les capitaines de cette zone ont été vaincus.",
                color=discord.Color.green()
            ))
    else:
        enemy = ENEMIES[zone]["minions"][0]

    # ── Initialisation des stats ─────────────────────────────────────────────
    PLAYER_DEFAULTS = [("hp",100),("hp_max",100),("atk",10),("def",5),("dex",5),("eva",5),("crit",5)]
    ENEMY_DEFAULTS  = [("hp",100),("atk",10),("def",5),("dex",5),("eva",5),("crit",2)]

    p = {k: stats.get(k, d) for k, d in PLAYER_DEFAULTS}
    e = {k: enemy.get(k, d) for k, d in ENEMY_DEFAULTS}
    p["crit"] *= 5
    e["crit"] *= 5

    # ── Effets de classe ─────────────────────────────────────────────────────
    class_effects = get_class_effects(player_data.get("class")) if player_data else {}

    combat_log: list[str] = []
    turn = 0
    MAX_TURNS = 50  # sécurité anti-boucle infinie

    # ── Boucle de combat ─────────────────────────────────────────────────────
    while p["hp"] > 0 and e["hp"] > 0 and turn < MAX_TURNS:
        turn += 1

        # === TOUR JOUEUR ===
        if random.randint(1, 100) > e["eva"]:
            dmg, is_crit = attempt_attack(p["atk"], e["def"], p["crit"])

            # BERSERKER : +10% ATK si HP < 50%
            if "atk_bonus_below_50" in class_effects and p["hp"] < p["hp_max"] * 0.5:
                dmg = int(dmg * (1 + class_effects["atk_bonus_below_50"] / 100))

            # STRATÈGE : critiques +40%
            if is_crit and "crit_multiplier" in class_effects:
                dmg = int(dmg * class_effects["crit_multiplier"])

            e["hp"] -= dmg
            crit_tag = " 💥 CRIT!" if is_crit else ""
            combat_log.append(f"Tour {turn} — Vous attaquez {enemy['name']} : **{dmg} dmg**{crit_tag} (PV ennemi: {max(0, e['hp'])})")

            # HYBRIDE : lifesteal
            if "lifesteal_percent" in class_effects:
                heal = int(dmg * class_effects["lifesteal_percent"] / 100)
                p["hp"] = min(p["hp_max"], p["hp"] + heal)
                if heal:
                    combat_log.append(f"  ↳ 🩸 Lifesteal : +{heal} PV (Vos PV: {p['hp']})")
        else:
            combat_log.append(f"Tour {turn} — {enemy['name']} esquive votre attaque !")

        # Double attaque ASSASSIN
        if "double_attack_chance" in class_effects and random.randint(1, 100) <= class_effects["double_attack_chance"]:
            if random.randint(1, 100) > e["eva"]:
                dmg, _ = attempt_attack(p["atk"], e["def"], p["crit"])
                e["hp"] -= dmg
                combat_log.append(f"Tour {turn} — ⚡ Double attaque Assassin : **{dmg} dmg** (PV ennemi: {max(0, e['hp'])})")
            else:
                combat_log.append(f"Tour {turn} — {enemy['name']} esquive votre double attaque !")

        if e["hp"] <= 0:
            break

        # === TOUR ENNEMI ===
        if random.randint(1, 100) > p["eva"]:
            dmg, _ = attempt_attack(e["atk"], p["def"], e["crit"])

            # TANK : réduction des dégâts
            if "reduce_damage_percent" in class_effects:
                dmg = int(dmg * (1 - class_effects["reduce_damage_percent"] / 100))

            # SPIRITUALISTE : chance de bloquer
            if "chance_block_damage" in class_effects and random.randint(1, 100) <= class_effects["chance_block_damage"]:
                combat_log.append(f"Tour {turn} — 🟩 Reiatsu instable bloque l'attaque de {enemy['name']} !")
                dmg = 0

            p["hp"] -= dmg
            if dmg:
                combat_log.append(f"Tour {turn} — {enemy['name']} vous attaque : **{dmg} dmg** (Vos PV: {max(0, p['hp'])})")
        else:
            combat_log.append(f"Tour {turn} — Vous esquivez l'attaque de {enemy['name']} !")

        # Double attaque ennemi (via DEX)
        if random.randint(1, 100) <= e["dex"]:
            if random.randint(1, 100) > p["eva"]:
                dmg, _ = attempt_attack(e["atk"], p["def"], e["crit"])
                if "reduce_damage_percent" in class_effects:
                    dmg = int(dmg * (1 - class_effects["reduce_damage_percent"] / 100))
                if "chance_block_damage" in class_effects and random.randint(1, 100) <= class_effects["chance_block_damage"]:
                    dmg = 0
                p["hp"] -= dmg
                if dmg:
                    combat_log.append(f"Tour {turn} — Double attaque de {enemy['name']} : **{dmg} dmg** (Vos PV: {max(0, p['hp'])})")
            else:
                combat_log.append(f"Tour {turn} — Vous esquivez la double attaque de {enemy['name']} !")

    # ── Résultat et XP ───────────────────────────────────────────────────────
    victoire = p["hp"] > 0
    gain_xp = 200 if is_boss else 50
    stats["xp"] = stats.get("xp", 0) + gain_xp
    stats["hp"] = max(1, p["hp"])

    # Level up
    if stats["xp"] >= stats.get("xp_next", 100):
        stats["level"] = stats.get("level", 1) + 1
        stats["xp"] -= stats.get("xp_next", 100)
        stats["xp_next"] = int(stats.get("xp_next", 100) * 1.5)

    await update_player_stats(user_id, stats, cooldowns)

    # Déblocage zone si boss vaincu
    unlock_msg = None
    if victoire and is_boss and player_data:
        unlocked_zones = player_data.get("unlocked_zones", ["1"])
        _, unlock_msg = _try_unlock_next_zone(user_id, zone, unlocked_zones, enemy["name"])

    # ── Embed résultat ───────────────────────────────────────────────────────
    if victoire:
        desc = (
            f"🏆 Vous avez vaincu **{enemy['name']}** !\n"
            f"💖 Vos PV : **{p['hp']}/{p['hp_max']}**\n"
            f"⏳ Combat terminé en **{turn}** tours.\n"
            f"💰 +{gain_xp} XP"
        )
        if unlock_msg:
            desc += f"\n\n{unlock_msg}"
        embed = discord.Embed(title=f"⚔️ Victoire contre {enemy['name']} !", description=desc, color=discord.Color.green())
    else:
        embed = discord.Embed(
            title=f"💀 Défaite contre {enemy['name']}...",
            description=(
                f"Vous avez été vaincu par **{enemy['name']}**.\n"
                f"💖 Vos PV : **0/{p['hp_max']}**\n"
                f"⏳ Combat terminé en **{turn}** tours."
            ),
            color=discord.Color.red()
        )

    await send(embed, view=CombatLogView(combat_log))
