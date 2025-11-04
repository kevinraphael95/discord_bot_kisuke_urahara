# ────────────────────────────────────────────────────────────────────────────────
# 📌 jardin_ui_utils.py — Views et Buttons pour le jardin et l’alchimie
# Objectif : Contient GardenGridView, JardinView et AlchimieView
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
import datetime
from utils.jardin_utils import (
    FLEUR_EMOJIS, FLEUR_SIGNS, FLEUR_VALUES, FLEUR_LIST,
    POTIONS, FERTILIZE_COOLDOWN, pousser_fleurs, couper_fleurs,
    build_garden_embed, build_potions_embed
)
from utils.supabase_client import supabase

# ────────────────────────────────────────────────────────────────────────────────
# 🌿 Views éphémères pour Alchimie et Inventaire
# ────────────────────────────────────────────────────────────────────────────────
class AlchimieEphemereView(discord.ui.View):
    def __init__(self, garden: dict, user_id: int):
        super().__init__(timeout=180)
        self.garden = garden
        self.user_id = user_id

    @discord.ui.button(label="Créer une potion", style=discord.ButtonStyle.green)
    async def create_potion(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Ce n’est pas ton jardin !", ephemeral=True)

        # Exemple simple : ajouter une potion aléatoire
        potion_id, potion_name = random.choice(list(POTIONS.items()))
        self.garden.setdefault("potions", {})
        self.garden["potions"][potion_name] = self.garden["potions"].get(potion_name, 0) + 1

        # Update DB
        supabase.table("gardens").update({"potions": self.garden["potions"]}).eq("user_id", self.user_id).execute()

        await interaction.response.send_message(f"🧪 Tu as créé : {potion_name}", ephemeral=True)


class InventoryEphemereView(discord.ui.View):
    def __init__(self, garden: dict, user_id: int):
        super().__init__(timeout=180)
        self.garden = garden
        self.user_id = user_id

    @discord.ui.button(label="Fermer", style=discord.ButtonStyle.gray)
    async def close_inventory(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Ce n’est pas ton inventaire !", ephemeral=True)
        await interaction.message.delete()


# ────────────────────────────────────────────────────────────────────────────────
# 🌱 GardenGridView et GardenButton
# ────────────────────────────────────────────────────────────────────────────────
class GardenButton(discord.ui.Button):
    def __init__(self, label: str, row: int, custom_id: str):
        super().__init__(label=label, style=discord.ButtonStyle.green, row=row, custom_id=custom_id)

    async def callback(self, interaction: discord.Interaction):
        view: GardenGridView = self.view
        if interaction.user.id != view.user_id:
            return await interaction.response.send_message("❌ Ce jardin n’est pas à toi !", ephemeral=True)

        i, j = map(int, self.custom_id.split("-"))
        current_emoji = view.garden["garden_grid"][i][j]

        if current_emoji == "🌱":
            return await interaction.response.send_message("🪴 Rien à cueillir ici.", ephemeral=True)

        # Chercher le nom de la fleur
        for name, emoji in FLEUR_EMOJIS.items():
            if emoji == current_emoji:
                view.garden["inventory"][name] = view.garden["inventory"].get(name, 0) + 1
                line = list(view.garden["garden_grid"][i])
                line[j] = "🌱"
                view.garden["garden_grid"][i] = "".join(line)
                break

        # Mise à jour dans la base
        supabase.table("gardens").update({
            "garden_grid": view.garden["garden_grid"],
            "inventory": view.garden["inventory"]
        }).eq("user_id", view.user_id).execute()

        self.label = "🌱"
        await interaction.response.edit_message(view=view)

class GardenGridView(discord.ui.View):
    def __init__(self, garden: dict, user_id: int):
        super().__init__(timeout=180)
        self.garden = garden
        self.user_id = user_id

        # Créer les boutons pour chaque case du jardin
        for i, line in enumerate(garden["garden_grid"]):
            for j, emoji in enumerate(line):
                custom_id = f"{i}-{j}"
                self.add_item(GardenButton(label=emoji, row=i, custom_id=custom_id))

        # Bouton Retour à la vue principale
        @discord.ui.button(label="🔙 Retour", style=discord.ButtonStyle.gray)
        async def back_to_main(interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user.id != self.user_id:
                return await interaction.response.send_message("❌ Ce jardin n’est pas à toi !", ephemeral=True)
            main_view = JardinView(self.garden, self.user_id)
            await interaction.response.edit_message(embed=build_garden_embed(self.garden, self.user_id), view=main_view)

# ────────────────────────────────────────────────────────────────────────────────
# 🌱 JardinView — Boutons Jardin principaux (Alchimie & Inventaire éphémères)
# ────────────────────────────────────────────────────────────────────────────────
class JardinView(discord.ui.View):
    def __init__(self, garden: dict, user_id: int):
        super().__init__(timeout=180)
        self.garden = garden
        self.user_id = user_id

    @discord.ui.button(label="🪴 Grille", style=discord.ButtonStyle.green)
    async def show_grid(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Ce jardin n’est pas à toi !", ephemeral=True)
        grid_view = GardenGridView(self.garden, self.user_id)
        await interaction.response.edit_message(
            content="🌾 **Clique sur les fleurs pour les cueillir !**",
            embed=None,
            view=grid_view
        )

    @discord.ui.button(label="💚 Engrais", style=discord.ButtonStyle.green)
    async def fertilize(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Ce jardin n’est pas à toi !", ephemeral=True)
        now = datetime.datetime.now(datetime.timezone.utc)
        last = self.garden.get("last_fertilize")
        if last:
            last_dt = datetime.datetime.fromisoformat(last)
            if now < last_dt + FERTILIZE_COOLDOWN:
                return await interaction.response.send_message("⏳ Engrais en cooldown !", ephemeral=True)
        self.garden["garden_grid"] = pousser_fleurs(self.garden["garden_grid"])
        self.garden["last_fertilize"] = now.isoformat()
        await self.update_garden_db()
        await interaction.response.edit_message(embed=build_garden_embed(self.garden, self.user_id))
    
    @discord.ui.button(label="✂️ Couper", style=discord.ButtonStyle.green)
    async def cut_flowers(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Ce jardin n’est pas à toi !", ephemeral=True)
        self.garden["garden_grid"], self.garden = couper_fleurs(self.garden["garden_grid"], self.garden)
        await self.update_garden_db()
        await interaction.response.edit_message(embed=build_garden_embed(self.garden, self.user_id))

    @discord.ui.button(label="⚗️ Alchimie", style=discord.ButtonStyle.blurple)
    async def open_alchimie(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Ce jardin n’est pas à toi !", ephemeral=True)

        alchimie_view = AlchimieEphemereView(self.garden, self.user_id)
        await interaction.response.send_message(
            "💡 Bienvenue dans l’Alchimie !",
            embed=build_potions_embed(self.garden.get("potions", {})),
            view=alchimie_view,
            ephemeral=True
        )


    @discord.ui.button(label="🎒 Inventaire", style=discord.ButtonStyle.gray)
    async def show_inventory(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Ce jardin n’est pas à toi !", ephemeral=True)

        # Texte fleurs
        fleurs = "\n".join(f"{emoji} {name} x{self.garden['inventory'].get(name,0)}"
                           for name, emoji in FLEUR_EMOJIS.items())

        # Texte potions
        potions = self.garden.get("potions", {})
        potions_text = "\n".join(f"{name} x{qty}" for name, qty in potions.items()) or "Aucune"

        embed = discord.Embed(
            title="🎒 Inventaire",
            description=f"**Fleurs :**\n{fleurs}",
            color=discord.Color.blue()
        )
        embed.add_field(name="🧪 Potions", value=potions_text, inline=False)

        inventory_view = InventoryEphemereView(self.garden, self.user_id)
        await interaction.response.send_message(embed=embed, view=inventory_view, ephemeral=True)


    async def update_garden_db(self):
        supabase.table("gardens").update({
            "garden_grid": self.garden["garden_grid"],
            "inventory": self.garden["inventory"],
            "last_fertilize": self.garden.get("last_fertilize"),
            "argent": self.garden.get("argent", 0),
            "armee": self.garden.get("armee", "")
        }).eq("user_id", self.user_id).execute()
