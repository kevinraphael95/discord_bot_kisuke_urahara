# ────────────────────────────────────────────────────────────────────────────────
# 📌 rpg_choose_class.py — Choix interactif de classe RPG avec boutons
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ui import View, Button
from utils.supabase_client import supabase

# ────────────────────────────────────────────────────────────
# Embed détaillé de toutes les classes + boutons pour choisir
# ────────────────────────────────────────────────────────────
async def choose_class(ctx, user_id, is_slash=False):
    embed = discord.Embed(
        title="🎴 Choisissez votre classe RPG",
        description="Cliquez sur le bouton correspondant pour sélectionner votre classe :",
        color=discord.Color.dark_blue()
    )

    embed.add_field(
        name="🛡️ TANK (Garde du Seireitei)",
        value=(
            "**Bonus de base :** HP max +30, DEF +5\n"
            "**Talent :** 🟦 Peau d’acier — Réduit tous les dégâts subis de 10%\n"
            "**Bonus level-up :** +8 HP max, +2 DEF, +1 ATK"
        ),
        inline=False
    )

    embed.add_field(
        name="⚔️ BERSERKER (Soldat brutal)",
        value=(
            "**Bonus de base :** ATK +5, Crit +5\n"
            "**Talent :** 🔴 Rage sanglante — +10% ATK quand HP <50%\n"
            "**Bonus level-up :** +3 ATK, +1 Crit, +3 HP max"
        ),
        inline=False
    )

    embed.add_field(
        name="🌀 ASSASSIN (Ninja du Rukongai)",
        value=(
            "**Bonus de base :** DEX +5, EVA +5\n"
            "**Talent :** 🟣 Frappe éclair — +15% chance de double attaque\n"
            "**Bonus level-up :** +2 DEX, +2 EVA, +1 ATK"
        ),
        inline=False
    )

    embed.add_field(
        name="🧠 STRATÈGE (Officier tactique)",
        value=(
            "**Bonus de base :** Crit +10, DEX +2\n"
            "**Talent :** 🟡 Coup précis — Coups critiques infligent +40% de dégâts\n"
            "**Bonus level-up :** +2 Crit, +1 DEX, +1 ATK"
        ),
        inline=False
    )

    embed.add_field(
        name="🔮 SPIRITUALISTE (Expert en Reiatsu)",
        value=(
            "**Bonus de base :** SP +20, Crit +3\n"
            "**Talent :** 🟩 Reiatsu instable — 10% chance d'annuler les dégâts\n"
            "**Bonus level-up :** +10 SP, +1 Crit, +1 DEX"
        ),
        inline=False
    )

    embed.add_field(
        name="🦊 HYBRIDE (Shinigami + Hollow)",
        value=(
            "**Bonus de base :** ATK +2, HP max +10, EVA +2\n"
            "**Talent :** 🟤 Instinct Hollow — 5% lifesteal\n"
            "**Bonus level-up :** +2 HP max, +1 ATK, +1 EVA, +1 Crit"
        ),
        inline=False
    )

    # ────────────────────────────────────────────────────────────
    # Boutons interactifs pour choisir la classe
    # ────────────────────────────────────────────────────────────
    class ClassChooseView(View):
        def __init__(self):
            super().__init__(timeout=None)

        async def choose_class(self, interaction, class_name):
            # Sauvegarde la classe choisie dans Supabase
            await supabase.table("rpg_players").update({"class": class_name}).eq("user_id", user_id)
            await interaction.response.edit_message(
                embed=discord.Embed(
                    title="✅ Classe choisie !",
                    description=f"Vous avez choisi la classe **{class_name}**.",
                    color=discord.Color.green()
                ),
                view=None
            )

        @discord.ui.button(label="🛡️ TANK", style=discord.ButtonStyle.primary)
        async def tank(self, interaction: discord.Interaction, button: Button):
            await self.choose_class(interaction, "TANK")

        @discord.ui.button(label="⚔️ BERSERKER", style=discord.ButtonStyle.danger)
        async def berserker(self, interaction: discord.Interaction, button: Button):
            await self.choose_class(interaction, "BERSERKER")

        @discord.ui.button(label="🌀 ASSASSIN", style=discord.ButtonStyle.secondary)
        async def assassin(self, interaction: discord.Interaction, button: Button):
            await self.choose_class(interaction, "ASSASSIN")

        @discord.ui.button(label="🧠 STRATÈGE", style=discord.ButtonStyle.success)
        async def strategist(self, interaction: discord.Interaction, button: Button):
            await self.choose_class(interaction, "STRATEGISTE")

        @discord.ui.button(label="🔮 SPIRITUALISTE", style=discord.ButtonStyle.primary)
        async def spiritualist(self, interaction: discord.Interaction, button: Button):
            await self.choose_class(interaction, "SPIRITUALISTE")

        @discord.ui.button(label="🦊 HYBRIDE", style=discord.ButtonStyle.secondary)
        async def hybrid(self, interaction: discord.Interaction, button: Button):
            await self.choose_class(interaction, "HYBRIDE")

    view = ClassChooseView()

    if is_slash:
        await ctx.followup.send(embed=embed, view=view)
    else:
        await ctx.send(embed=embed, view=view)
