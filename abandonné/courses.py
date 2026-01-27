# ────────────────────────────────────────────────────────────────────────────────
# 📌 course_voiture.py — Mini-jeu de course de voitures avec stats dynamiques
# Objectif : Course animée basée sur les voitures choisies par les joueurs
# Catégorie : Voiture
# Accès : Tous
# Cooldown : 0 (désactivé pour tests)
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button
import random
import asyncio
from utils.discord_utils import safe_send, safe_respond, safe_edit
from utils.supabase_client import supabase

# ────────────────────────────────────────────────────────────────────────────────
# 🎮 Classe du bouton pour rejoindre la course
# ────────────────────────────────────────────────────────────────────────────────
class JoinRaceButton(Button):
    def __init__(self, race):
        super().__init__(label="🚗 Rejoindre la course", style=discord.ButtonStyle.green)
        self.race = race

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)

        # Récupération sûre des données utilisateur (Supabase)
        try:
            res = supabase.table("voitures_users").select("*").eq("user_id", user_id).execute()
            user_data = res.data[0] if res.data else None
        except Exception as e:
            print(f"[SUPABASE ERR get user] {e}")
            return await interaction.response.send_message("⚠️ Erreur base de données.", ephemeral=True)

        if not user_data or not user_data.get("voiture_choisie"):
            print(f"[DEBUG] {interaction.user} n'a pas de voiture choisie.")
            # Pour tests — voiture par défaut
            user_data = {"voiture_choisie": "Ferrari Test"}

        voiture_choisie = user_data["voiture_choisie"]

        # Récupérer stats voiture
        try:
            car_res = supabase.table("voitures_data").select("*").eq("nom", voiture_choisie).execute()
            car_data = car_res.data[0] if car_res.data else None
        except Exception as e:
            print(f"[SUPABASE ERR get car] {e}")
            car_data = None

        if not car_data:
            stats = {"vitesse_max": 200, "acceleration_0_100": 5.0, "maniabilite": 70, "poids": 1300}
        else:
            stats = car_data.get("stats", {"vitesse_max": 200, "acceleration_0_100": 5.0, "maniabilite": 70, "poids": 1300})

        # Ajout du joueur
        if user_id not in [p["user_id"] for p in self.race["participants"]]:
            if not self.race["available_emojis"]:
                return await interaction.response.send_message("❌ Course pleine.", ephemeral=True)
            emoji = self.race["available_emojis"].pop(0)
            self.race["participants"].append({
                "user_id": user_id,
                "username": interaction.user.display_name,
                "voiture": voiture_choisie,
                "stats": stats,
                "emoji": emoji,
                "position": 0,
                "is_bot": False
            })

        # Mettre à jour l'embed
        embed = self.generate_embed()
        try:
            await interaction.response.edit_message(embed=embed, view=self.view)
        except Exception:
            await interaction.response.send_message(embed=embed, ephemeral=True)

        # Si 4 participants, démarrer automatiquement
        if len(self.race["participants"]) >= 4:
            for child in self.view.children:
                child.disabled = True
            await interaction.edit_original_response(view=None)
            asyncio.create_task(self.start_race(interaction.channel))

    def generate_embed(self):
        embed = discord.Embed(
            title="🏁 Course de voitures en préparation",
            description=f"Hôte : **{self.race.get('host', 'inconnu')}** — Clique sur **🚗 Rejoindre la course** pour participer !",
            color=discord.Color.blue()
        )
        if self.race["participants"]:
            desc = "\n".join(f"{p['emoji']} {p['username']} — {p['voiture']}" for p in self.race["participants"])
        else:
            desc = "Aucun participant pour l’instant..."
        embed.add_field(name="Participants", value=desc, inline=False)
        embed.set_footer(text="Max 4 participants — la course démarre automatiquement.")
        return embed

    async def start_race(self, channel: discord.abc.Messageable):
        # Ajouter des bots si moins de 4 joueurs
        bot_pool = ["Bot-Kenzo", "Bot-Ryo", "Bot-Mika", "Bot-Aya", "Bot-Luna"]
        while len(self.race["participants"]) < 4 and self.race["available_emojis"]:
            emoji = self.race["available_emojis"].pop(0)
            bot_name = bot_pool.pop(0) if bot_pool else f"Bot{random.randint(1,99)}"
            voiture = random.choice(["Ferrari F40", "McLaren F1", "Peugeot Oxia"])
            stats = {
                "vitesse_max": random.randint(220, 360),
                "acceleration_0_100": random.uniform(2.5, 5.0),
                "maniabilite": random.randint(60, 90),
                "poids": random.randint(1100, 1600)
            }
            self.race["participants"].append({
                "user_id": f"bot_{emoji}",
                "username": bot_name,
                "voiture": voiture,
                "stats": stats,
                "emoji": emoji,
                "position": 0,
                "is_bot": True
            })

        start_msg = await safe_send(channel, "🏎️ **La course commence !** Préparez-vous...")
        await asyncio.sleep(2.0)
        await self.run_race(channel, start_msg)

    async def run_race(self, channel: discord.abc.Messageable, message):
        track_length = 25  # plus court = plus lisible
        finished = False
        winner = None

        # Tous les participants partent de 0
        for p in self.race["participants"]:
            p["position"] = 0

        while not finished:
            await asyncio.sleep(1.2)  # ⏳ rythme plus lent pour suspense
            for p in self.race["participants"]:
                stats = p["stats"]
                avance = self.calculate_advance(stats)
                p["position"] += avance
                if p["position"] >= track_length and not winner:
                    p["position"] = track_length
                    winner = p
                    finished = True

            track_text = self.render_track(self.race["participants"], track_length)
            sorted_p = sorted(self.race["participants"], key=lambda x: -x["position"])
            leaderboard = "\n".join(
                f"{i+1}. {p['emoji']} {p['username']} ({p['voiture']})"
                for i, p in enumerate(sorted_p)
            )

            try:
                await safe_edit(message, f"🏎️ **Course en cours...**\n{track_text}\n\n**Classement provisoire :**\n{leaderboard}")
            except Exception as e:
                print("[EDIT ERR]", e)

        final = f"🏆 **Course terminée !**\nLe gagnant est **{winner['emoji']} {winner['username']}** avec sa **{winner['voiture']}** ! 🎉"
        try:
            await safe_edit(message, final)
        except Exception:
            await message.edit(content=final)

    def render_track(self, participants, track_length):
        lines = []
        for p in participants:
            pos = min(int(p["position"]), track_length)
            track = f"{p['emoji']} " + "─" * pos + "🚗" + "─" * (track_length - pos) + " |🏁"
            lines.append(track)
        return "\n".join(lines)

    def calculate_advance(self, stats):
        base = stats.get("vitesse_max", 200)
        accel = stats.get("acceleration_0_100", 5)
        maniab = stats.get("maniabilite", 70)
        poids = stats.get("poids", 1300)
        # ⚙️ Avancement réduit pour créer du suspense
        advance = (base / 250) * (10 / accel) * (maniab / 100) * (1200 / poids)
        return max(1, round(advance * random.uniform(0.8, 2.0)))

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class CourseVoiture(commands.Cog):
    """Commande /course_voiture et !course_voiture — Course entre joueurs selon leurs voitures."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="course_voiture", description="Lance une course animée entre 4 voitures selon leurs stats.")
    @app_commands.checks.cooldown(1, 0.0, key=lambda i: (i.user.id))
    async def slash_course_voiture(self, interaction: discord.Interaction):
        race = {"host": interaction.user.display_name, "participants": [], "available_emojis": ["🇦", "🇧", "🇨", "🇩"]}
        view = View(timeout=60)
        button = JoinRaceButton(race)
        view.add_item(button)

        await interaction.response.send_message(embed=button.generate_embed(), view=view)

        async def on_timeout():
            for child in view.children:
                child.disabled = True
            if len(race["participants"]) >= 1:
                jb = next((c for c in view.children if isinstance(c, JoinRaceButton)), None)
                if jb:
                    await jb.start_race(interaction.channel)
                else:
                    await safe_send(interaction.channel, "⚠️ Impossible de démarrer automatiquement la course (internal).")
            else:
                msg = await interaction.original_response()
                await msg.edit(content="❌ Course annulée, personne n'a rejoint.", embed=None, view=view)

        view.on_timeout = on_timeout

    @commands.command(name="course_voiture", aliases=["vcourse"])
    async def prefix_course_voiture(self, ctx: commands.Context):
        race = {"host": ctx.author.display_name, "participants": [], "available_emojis": ["🇦", "🇧", "🇨", "🇩"]}
        view = View(timeout=60)
        button = JoinRaceButton(race)
        view.add_item(button)
        await safe_send(ctx.channel, embed=button.generate_embed(), view=view)
        view.on_timeout = lambda: button.start_race(ctx.channel) if len(race["participants"]) >= 1 else safe_send(ctx.channel, "Course annulée.")

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = CourseVoiture(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Voiture"
    await bot.add_cog(cog)
