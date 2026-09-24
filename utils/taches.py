# ================================================================================
# 📌 utils/taches.py — Mini-jeux interactifs pour le bot
# Objectif : Mini-jeux interactifs affichés dynamiquement dans un embed unique
# ================================================================================

# ================================================================================
# 📦 Imports nécessaires
# ================================================================================
import discord
import random
import asyncio

# ================================================================================
# 🔹 Mini-jeux interactifs
# ================================================================================

async def lancer_emoji(interaction, embed, update_embed, num):
    pool = ["💀", "🌀", "🔥", "🌪️", "🌟", "🍥", "🍡", "🧊", "❄️", "💨"]
    sequence = random.sample(pool, 3)
    autres = [e for e in pool if e not in sequence]
    mix = sequence + random.sample(autres, 2)
    random.shuffle(mix)

    view = discord.ui.View(timeout=120)
    view.reponses = []

    class EmojiButton(discord.ui.Button):
        def __init__(self, emoji):
            super().__init__(style=discord.ButtonStyle.secondary, emoji=emoji)
            self.emoji_val = emoji

        async def callback(self, inter_button):
            if inter_button.user != interaction.user:
                return await inter_button.response.send_message("❌ Ce bouton n'est pas pour toi.", ephemeral=True)
            await inter_button.response.defer()
            if len(self.view.reponses) < len(sequence) and self.emoji_val == sequence[len(self.view.reponses)]:
                self.view.reponses.append(self.emoji_val)
                if len(self.view.reponses) == len(sequence):
                    self.view.stop()
            else:
                self.view.reponses.clear()

    for e in mix:
        view.add_item(EmojiButton(e))

    embed.set_field_at(0 if embed.fields else None,
                       name=f"Épreuve {num}",
                       value=f"🔁 Reproduis : {' → '.join(sequence)}",
                       inline=False)

    await update_embed(embed)
    await interaction.edit_original_response(embed=embed, view=view)
    await view.wait()

    success = view.reponses == sequence
    embed.set_field_at(0, name=f"Épreuve {num}", value="✅ Séquence réussie" if success else "❌ Échec", inline=False)
    await update_embed(embed)
    return success


async def lancer_reflexe(interaction, embed, update_embed, num):
    compte = ["5️⃣", "4️⃣", "3️⃣", "2️⃣", "1️⃣"]

    view = discord.ui.View(timeout=30)
    view.reponses = []

    class ReflexeButton(discord.ui.Button):
        def __init__(self, emoji):
            super().__init__(style=discord.ButtonStyle.secondary, emoji=emoji)
            self.emoji_val = emoji

        async def callback(self, inter_button):
            if inter_button.user != interaction.user:
                return await inter_button.response.send_message("❌ Ce bouton n'est pas pour toi.", ephemeral=True)
            await inter_button.response.defer()
            if len(self.view.reponses) < len(compte) and self.emoji_val == compte[len(self.view.reponses)]:
                self.view.reponses.append(self.emoji_val)
                if len(self.view.reponses) == len(compte):
                    self.view.stop()
            else:
                self.view.reponses.clear()

    for e in compte:
        view.add_item(ReflexeButton(e))

    embed.set_field_at(0 if embed.fields else None,
                       name=f"Épreuve {num}",
                       value="🕒 Clique dans l’ordre : `5️⃣ 4️⃣ 3️⃣ 2️⃣ 1️⃣`",
                       inline=False)

    await update_embed(embed)
    await interaction.edit_original_response(embed=embed, view=view)
    await view.wait()

    success = view.reponses == compte
    embed.set_field_at(0, name=f"Épreuve {num}", value="⚡ Réflexe réussi" if success else "❌ Échec", inline=False)
    await update_embed(embed)
    return success


async def lancer_fleche(interaction, embed, update_embed, num):
    fleches = ["⬅️", "⬆️", "⬇️", "➡️"]
    sequence = [random.choice(fleches) for _ in range(5)]

    embed.set_field_at(0 if embed.fields else None,
                       name=f"Épreuve {num}",
                       value=f"🧭 Mémorise : `{' '.join(sequence)}` (5 s)",
                       inline=False)
    await update_embed(embed)
    await asyncio.sleep(5)

    view = discord.ui.View(timeout=60)
    view.reponses = []

    class FlecheButton(discord.ui.Button):
        def __init__(self, emoji):
            super().__init__(style=discord.ButtonStyle.secondary, emoji=emoji)
            self.emoji_val = emoji

        async def callback(self, inter_button):
            if inter_button.user != interaction.user:
                return await inter_button.response.send_message("❌ Ce bouton n'est pas pour toi.", ephemeral=True)
            await inter_button.response.defer()
            if len(self.view.reponses) < len(sequence) and self.emoji_val == sequence[len(self.view.reponses)]:
                self.view.reponses.append(self.emoji_val)
                if len(self.view.reponses) == len(sequence):
                    self.view.stop()
            else:
                self.view.reponses.clear()

    for e in fleches:
        view.add_item(FlecheButton(e))

    embed.set_field_at(0, name=f"Épreuve {num}", value="🔁 Reproduis la séquence avec les boutons ci-dessous :", inline=False)
    await update_embed(embed)
    await interaction.edit_original_response(embed=embed, view=view)
    await view.wait()

    success = view.reponses == sequence
    embed.set_field_at(0, name=f"Épreuve {num}", value="✅ Séquence fléchée réussie" if success else "❌ Échec", inline=False)
    await update_embed(embed)
    return success


# ================================================================================
# 🔁 Lancer 3 épreuves aléatoires
# ================================================================================
TACHES = [lancer_emoji, lancer_reflexe, lancer_fleche]

async def lancer_3_taches(interaction, embed, update_embed):
    selection = random.sample(TACHES, 3)
    success_global = True

    for i, tache in enumerate(selection):
        field_name = f"Épreuve {i+1}"
        if not embed.fields:
            embed.add_field(name=field_name, value="Préparation...", inline=False)
        else:
            embed.set_field_at(0, name=field_name, value="🔹 En cours...", inline=False)
        await update_embed(embed)

        try:
            result = await tache(interaction, embed, update_embed, i+1)
        except Exception:
            result = False

        success_global = success_global and result
        embed.set_field_at(0, name=field_name, value="✅ Réussie" if result else "❌ Échec", inline=False)
        await update_embed(embed)
        await asyncio.sleep(1)

    return success_global
