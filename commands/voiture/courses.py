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
            return await interaction.response.send_message(
                "❌ Tu dois choisir une voiture avant de participer à une course !",
                ephemeral=True
            )

        voiture_choisie = user_data["voiture_choisie"]

        # Récupérer stats voiture (robuste)
        try:
            car_res = supabase.table("voitures_data").select("*").eq("nom", voiture_choisie).execute()
            car_data = car_res.data[0] if car_res.data else None
        except Exception as e:
            print(f"[SUPABASE ERR get car] {e}")
            car_data = None

        if not car_data:
            # fallback stats si introuvable
            stats = {"vitesse_max": 200, "acceleration_0_100": 5.0, "maniabilite": 70, "poids": 1300}
        else:
            stats = car_data.get("stats", {"vitesse_max": 200, "acceleration_0_100": 5.0, "maniabilite": 70, "poids": 1300})

        # Ajout du joueur (unique)
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

        # Mettre à jour l'embed (on édite le message d'origine)
        embed = self.generate_embed()
        try:
            await interaction.response.edit_message(embed=embed, view=self.view)
        except Exception:
            # fallback si edit impossible (rare)
            await interaction.response.send_message(embed=embed, ephemeral=True)

        # Si 4 participants, disable buttons et lancer
        if len(self.race["participants"]) >= 4:
            for child in self.view.children:
                child.disabled = True
            # démarrer la course (on lance coroutine sans bloquer callback)
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
        # Compléter avec des bots si nécessaire
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

        # message initial de la course (on garde ce message pour edits)
        start_msg = await safe_send(channel, "🏎️ **La course commence !** Préparez-vous...")
        await asyncio.sleep(1.2)
        # lancer animation (coroutine)
        await self.run_race(channel, start_msg)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Animation de la course (met à jour UN seul message)
    # ────────────────────────────────────────────────────────────────────────────
    async def run_race(self, channel: discord.abc.Messageable, message):
        track_length = 30
        finished = False
        winner = None

        # boucle d'animation
        while not finished:
            await asyncio.sleep(0.7)
            for p in self.race["participants"]:
                stats = p["stats"]
                avance = self.calculate_advance(stats)
                p["position"] += avance
                if p["position"] >= track_length:
                    p["position"] = track_length
                    if not winner:
                        winner = p
                        finished = True

            track_text = self.render_track(self.race["participants"], track_length)
            try:
                await safe_edit(message, f"🏎️ **Course en cours...**\n{track_text}")
            except Exception:
                # fallback si safe_edit rate, on tente message.edit
                try:
                    await message.edit(content=f"🏎️ **Course en cours...**\n{track_text}")
                except Exception as e:
                    print("[EDIT ERR]", e)

        # fin de la course : message final
        final = f"🏆 **Course terminée !**\nLe gagnant est **{winner['emoji']} {winner['username']}** avec sa **{winner['voiture']}** ! 🎉"
        try:
            await safe_edit(message, final)
        except Exception:
            await message.edit(content=final)

    def render_track(self, participants, track_length):
        lines = []
        for p in participants:
            pos = min(int(p["position"]), track_length)
            # piste affichée: emoji + position (sans nom voiture sur la piste)
            track = f"{p['emoji']} " + "─" * pos + "🚗" + "─" * (track_length - pos) + " |🏁"
            lines.append(track)
        return "\n".join(lines)

    def calculate_advance(self, stats):
        base = stats.get("vitesse_max", 200)
        accel = stats.get("acceleration_0_100", 5)
        maniab = stats.get("maniabilite", 70)
        poids = stats.get("poids", 1300)
        advance = (base / 100) * (10 / accel) * (maniab / 100) * (1200 / poids)
        # aléa limité pour rendre la course incertaine
        return max(1, int(advance * random.uniform(0.8, 1.4)))

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class CourseVoiture(commands.Cog):
    """
    Commande /course_voiture et !course_voiture — Course entre joueurs selon leurs voitures.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="course_voiture",
        description="Lance une course animée entre 4 voitures selon leurs stats."
    )
    @app_commands.checks.cooldown(1, 0.0, key=lambda i: (i.user.id))  # Cooldown à 0 pour tests
    async def slash_course_voiture(self, interaction: discord.Interaction):
        # création de l'objet race (partagé avec le Button)
        race = {
            "host": interaction.user.display_name,
            "participants": [],
            "available_emojis": ["🇦", "🇧", "🇨", "🇩"]
        }
        view = View(timeout=60)
        button = JoinRaceButton(race)
        view.add_item(button)

        # on envoie le message PUBLIC avec view (important)
        try:
            await interaction.response.send_message(embed=button.generate_embed(), view=view)
        except Exception as e:
            # fallback si déjà répondu
            print("[SEND ERR]", e)
            await safe_send(interaction.channel, embed=button.generate_embed(), view=view)

        # gestion du timeout du view : si le view expire et au moins 1 participant -> lancer course
        async def on_timeout():
            # disable children
            for child in view.children:
                child.disabled = True
            # si 1+ participants -> lancer (compléter bots)
            if len(race["participants"]) >= 1:
                # lancer la course via la même instance de bouton (start_race)
                # on crée une instance ad hoc si besoin
                # trouver le JoinRaceButton dans view
                jb = None
                for c in view.children:
                    if isinstance(c, JoinRaceButton):
                        jb = c
                        break
                if jb:
                    try:
                        await jb.start_race(interaction.channel)
                    except Exception as e:
                        print("[TIMEOUT start race err]", e)
                else:
                    # fallback: run a simple race
                    await safe_send(interaction.channel, "⚠️ Impossible de démarrer automatiquement la course (internal).")
            else:
                # personne n'a rejoint
                try:
                    # edit original message to say cancelled
                    msg = await interaction.original_response()
                    await msg.edit(content="❌ Course annulée, personne n'a rejoint.", embed=None, view=view)
                except Exception:
                    await safe_send(interaction.channel, "❌ Course annulée, personne n'a rejoint.")

        # schedule timeout handler
        loop = asyncio.get_event_loop()
        loop.create_task(self._schedule_view_timeout(view, on_timeout))

    # helper to schedule view timeout callback without blocking
    async def _schedule_view_timeout(self, view: View, callback):
        await asyncio.sleep(view.timeout)
        await callback()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX (réutilise slash)
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="course_voiture", aliases=["vcourse"])
    async def prefix_course_voiture(self, ctx: commands.Context):
        # simulate an Interaction-like usage: send a public message with the view
        race = {
            "host": ctx.author.display_name,
            "participants": [],
            "available_emojis": ["🇦", "🇧", "🇨", "🇩"]
        }
        view = View(timeout=60)
        button = JoinRaceButton(race)
        view.add_item(button)
        await safe_send(ctx.channel, embed=button.generate_embed(), view=view)
        # schedule timeout similarly
        loop = asyncio.get_event_loop()
        loop.create_task(self._schedule_view_timeout(view, lambda: button.start_race(ctx.channel) if len(race["participants"])>=1 else safe_send(ctx.channel, "Course annulée.")))

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = CourseVoiture(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Voiture"
    await bot.add_cog(cog)
