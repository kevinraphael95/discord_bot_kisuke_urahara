# ────────────────────────────────────────────────────────────────────────────────
# 📌 skill.py — Commande interactive /skill et !skill
# Objectif : Afficher et activer la compétence active du joueur
# (Illusionniste, Voleur, Absorbeur, Parieur)
# Catégorie : Reiatsu
# Accès : Tous
# Cooldown : 12h (8h pour Illusionniste)
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
import asyncio
from dateutil import parser
from datetime import datetime, timedelta, timezone
import os
import json
import random
from utils.discord_utils import safe_send, safe_respond
from utils.supabase_client import supabase
from utils.reiatsu_utils import ensure_profile, has_class

# ────────────────────────────────────────────────────────────────────────────────
# 📂 Chargement de la configuration Reiatsu
# ────────────────────────────────────────────────────────────────────────────────
REIATSU_CONFIG_PATH = os.path.join("data", "reiatsu_config.json")

def load_reiatsu_config():
    """Charge la configuration Reiatsu depuis le fichier JSON."""
    try:
        with open(REIATSU_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERREUR JSON] Impossible de charger {REIATSU_CONFIG_PATH} : {e}")
        return {}

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal : Skill
# ────────────────────────────────────────────────────────────────────────────────
class Skill(commands.Cog):
    """Commande /skill et !skill — Active la compétence active du joueur."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config = load_reiatsu_config()
        self.skill_locks = {}

    # ────────────────────────────────────────────────────────────────────────
    # 🏆 Validation de la quête "skill"
    # ────────────────────────────────────────────────────────────────────────
    async def valider_quete_skill(self, user: discord.User, channel=None):
        """Valide la quête 'Première utilisation du skill'."""
        try:
            data = supabase.table("reiatsu").select("quetes, niveau").eq("user_id", user.id).execute()
            if not data.data:
                return

            quetes = data.data[0].get("quetes", [])
            niveau = data.data[0].get("niveau", 1)

            if "skill" in quetes:
                return

            quetes.append("skill")
            new_lvl = niveau + 1
            supabase.table("reiatsu").update({"quetes": quetes, "niveau": new_lvl}).eq("user_id", user.id).execute()

            embed = discord.Embed(
                title="🎯 Quête accomplie !",
                description=f"Bravo **{user.name}** ! Tu as terminé la quête **Première utilisation du skill** 💫\n\n⭐ **Niveau +1 !** (Niveau {new_lvl})",
                color=0xFFD700
            )
            if channel:
                await channel.send(embed=embed)
            else:
                await user.send(embed=embed)
        except Exception as e:
            print(f"[ERREUR validation quête skill] {e}")

    # ────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction interne : activation du skill
    # ────────────────────────────────────────────────────────────────────────
    async def _activate_skill(self, user: discord.User, channel: discord.abc.Messageable):
        if user.id not in self.skill_locks:
            self.skill_locks[user.id] = asyncio.Lock()

        async with self.skill_locks[user.id]:

            player = ensure_profile(user.id, user.name)

            if not has_class(player):
                await safe_send(channel, "❌ Tu n’as pas encore choisi de classe Reiatsu. Utilise `!!classe` pour choisir une classe.")
                return

            classe = player["classe"]

            # 🔸 Suppression du message de la commande pour Illusionniste
            if classe == "Illusionniste" and isinstance(channel, discord.TextChannel):
                try:
                    async for msg in channel.history(limit=5):
                        if msg.author == user and msg.content.lower().startswith("!!skill"):
                            await msg.delete()
                            break
                except Exception:
                    pass

            classe_data = self.config["CLASSES"].get(classe, {})
            base_cd = classe_data.get("Cooldown", 12)

            res = supabase.table("reiatsu").select("last_skilled_at, active_skill, fake_spawn_id, points").eq("user_id", user.id).execute()
            data = res.data[0] if res.data else {}
            last_skill = data.get("last_skilled_at")
            active_skill = data.get("active_skill", False)
            fake_spawn_id = data.get("fake_spawn_id")

            cooldown_text = "✅ Disponible"

            if last_skill:
                try:
                    last_dt = parser.parse(last_skill)
                    if not last_dt.tzinfo:
                        last_dt = last_dt.replace(tzinfo=timezone.utc)
                    next_cd = last_dt + timedelta(hours=8 if classe == "Illusionniste" else base_cd)
                    now_dt = datetime.now(timezone.utc)

                    if now_dt < next_cd:
                        restant = next_cd - now_dt
                        h, m = divmod(int(restant.total_seconds() // 60), 60)
                        cooldown_text = f"⏳ {restant.days}j {h}h{m}m" if restant.days else f"⏳ {h}h{m}m"

                except:
                    pass

            if active_skill:
                cooldown_text = "🌀 En cours"

            # 🔸 Retour d'info si le skill n'est pas dispo
            if cooldown_text != "✅ Disponible":
                embed = discord.Embed(
                    title=f"🎴 Skill de {player.get('username', user.name)}",
                    description=f"**Classe :** {classe}\n**Statut :** {cooldown_text}",
                    color=discord.Color.orange()
                )
                await safe_send(channel, embed=embed)
                return

            update_data = {"last_skilled_at": datetime.utcnow().isoformat()}

            # ───────────── Illusionniste ─────────────
            if classe == "Illusionniste":
                if fake_spawn_id:
                    await safe_send(channel, "⚠️ Tu as déjà un faux Reiatsu actif !")
                    return

                update_data["active_skill"] = True
                supabase.table("reiatsu").update(update_data).eq("user_id", user.id).execute()

                conf_data = supabase.table("reiatsu_config").select("*").eq("guild_id", channel.guild.id).execute()
                if not conf_data.data or not conf_data.data[0].get("channel_id"):
                    await safe_send(channel, "❌ Aucun canal de spawn configuré pour ce serveur.")
                    return

                spawn_channel = self.bot.get_channel(int(conf_data.data[0]["channel_id"]))

                cog = self.bot.get_cog("ReiatsuSpawner")
                if cog:
                    await cog._spawn_message(spawn_channel, guild_id=None, is_fake=True, owner_id=user.id)

                embed = discord.Embed(
                    title="🎭 Skill Illusionniste activé !",
                    description="Un faux Reiatsu est apparu dans le serveur…\nTu ne peux pas l’absorber toi-même.",
                    color=discord.Color.green()
                )
                await safe_send(channel, embed=embed)

                await self.valider_quete_skill(user, channel)
                return

            # ───────────── Voleur ─────────────
            elif classe == "Voleur":
                update_data["active_skill"] = True
                embed = discord.Embed(
                    title="🥷 Skill Voleur activé !",
                    description="Ton prochain vol sera automatiquement **réussi**.",
                    color=discord.Color.purple()
                )
                await safe_send(channel, embed=embed)

                supabase.table("reiatsu").update(update_data).eq("user_id", user.id).execute()
                await self.valider_quete_skill(user, channel)
                return

            # ───────────── Absorbeur ─────────────
            elif classe == "Absorbeur":
                update_data["active_skill"] = True
                embed = discord.Embed(
                    title="🌀 Skill Absorbeur activé !",
                    description="Ton prochain Reiatsu sera automatiquement un **Super Reiatsu**.",
                    color=discord.Color.blue()
                )
                await safe_send(channel, embed=embed)

                supabase.table("reiatsu").update(update_data).eq("user_id", user.id).execute()
                await self.valider_quete_skill(user, channel)
                return

            # ───────────── Parieur (Machine à Sous) ─────────────
            elif classe == "Parieur":
                points = data.get("points", 0)
                mise = 30

                if points < mise:
                    await safe_send(channel, "❌ Tu n'as pas assez de Reiatsu pour parier (30 requis).")
                    return

                symbols = ["💎", "🍀", "🔥", "💀", "🎴", "🌸", "🪙"]

                slots = [random.choice(symbols) for _ in range(3)]
                embed = discord.Embed(
                    title="🎰 Machine à Sous Reiatsu",
                    description=f"{slots[0]} | {slots[1]} | {slots[2]}\n\nLancement...",
                    color=discord.Color.gold()
                )
                embed.set_footer(text=f"Mise : {mise} Reiatsu • Solde : {points}")
                message = await safe_send(channel, embed=embed)

                await asyncio.sleep(1.2)

                for _ in range(3):
                    slots = [random.choice(symbols) for _ in range(3)]
                    embed.description = f"{slots[0]} | {slots[1]} | {slots[2]}\n\nLancement..."
                    await message.edit(embed=embed)
                    await asyncio.sleep(0.5)

                slots = [random.choice(symbols) for _ in range(3)]

                if len(set(slots)) == 1:
                    result_text = "💥 **JACKPOT ! Trois symboles identiques ! +160 Reiatsu !**"
                    gain = 160
                elif len(set(slots)) == 2:
                    result_text = "✨ **Deux symboles identiques ! +100 Reiatsu !**"
                    gain = 100
                else:
                    result_text = "❌ **Perdu !** -30 Reiatsu."
                    gain = -mise

                new_points = max(0, points + gain)
                supabase.table("reiatsu").update({
                    "points": new_points,
                    "last_skilled_at": datetime.utcnow().isoformat()
                }).eq("user_id", user.id).execute()

                embed.description = f"{slots[0]} | {slots[1]} | {slots[2]}\n\n{result_text}"
                embed.color = discord.Color.gold() if gain > 0 else discord.Color.red()
                embed.set_footer(text=f"Mise : {mise} Reiatsu • Solde : {new_points}")
                await message.edit(embed=embed)

                await self.valider_quete_skill(user, channel)
                return

    # ────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────
    @app_commands.command(name="skill", description="Active la compétence de ta classe Reiatsu.")
    @app_commands.checks.cooldown(rate=1, per=5.0, key=lambda i: i.user.id)
    async def slash_skill(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self._activate_skill(interaction.user, interaction.channel)
        await interaction.delete_original_response()

    # ────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────
    @commands.command(name="skill", help="Active la compétence de ta classe Reiatsu.")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_skill(self, ctx: commands.Context):
        await self._activate_skill(ctx.author, ctx.channel)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Skill(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Reiatsu"
    await bot.add_cog(cog)
