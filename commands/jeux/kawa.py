# ────────────────────────────────────────────────────────────────────────────────
# 📌 entrainement_cerebral.py — Commande /cerebral et !cerebral
# Objectif : Lancer 5 mini-jeux aléatoires style Professeur Kawashima avec score arcade
# Catégorie : Jeux
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands
from discord import app_commands
import random
import time
import inspect
import asyncio
import json
import logging

from utils import kawashima_games
from utils.init_db import get_conn

log = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────────────────────────
# 🗄️ Accès base de données locale
# ────────────────────────────────────────────────────────────────────────────────

def db_save_score(user_id: int, username: str, score: int):
    """Enregistre un score Kawashima dans la table kawashima_scores."""
    try:
        conn   = get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO kawashima_scores (user_id, username, score, timestamp)
            VALUES (?, ?, ?, ?)
        """, (user_id, username, score, int(time.time())))
        conn.commit()
        conn.close()
    except Exception as e:
        log.exception("[cerebral] Erreur sauvegarde score SQLite : %s", e)

def db_get_leaderboard(limit: int = 10) -> list[dict]:
    """Récupère les meilleurs scores globaux."""
    try:
        conn   = get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT username, MAX(score) as score
            FROM kawashima_scores
            GROUP BY user_id
            ORDER BY score DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        conn.close()
        return [{"username": r[0], "score": r[1]} for r in rows]
    except Exception as e:
        log.exception("[cerebral] Erreur lecture leaderboard SQLite : %s", e)
        return []

def db_valider_quete(user_id: int) -> int | None:
    """
    Vérifie si la quête 'entrainement' est déjà validée pour l'utilisateur.
    Si non, l'ajoute et incrémente le niveau.
    Retourne le nouveau niveau si la quête vient d'être validée, sinon None.
    """
    try:
        conn   = get_conn()
        cursor = conn.cursor()

        cursor.execute("SELECT quetes, niveau FROM reiatsu WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()

        if not row:
            conn.close()
            return None

        quetes = json.loads(row[0] or "[]")
        niveau = row[1] or 1

        if "entrainement" in quetes:
            conn.close()
            return None

        quetes.append("entrainement")
        new_lvl = niveau + 1
        cursor.execute(
            "UPDATE reiatsu SET quetes = ?, niveau = ? WHERE user_id = ?",
            (json.dumps(quetes), new_lvl, user_id)
        )
        conn.commit()
        conn.close()
        return new_lvl

    except Exception as e:
        log.exception("[cerebral] Erreur validation quête SQLite : %s", e)
        return None

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────

class EntrainementCerebral(commands.Cog):
    """Mode arcade — Entraînement cérébral avec classement global."""

    def __init__(self, bot: commands.Bot):
        self.bot             = bot
        self.minijeux        = []
        self.active_sessions = set()

        for name, func in inspect.getmembers(kawashima_games, inspect.iscoroutinefunction):
            if not name.startswith("_"):
                emoji = getattr(func, "emoji", "🎮")
                titre = getattr(func, "title", func.__name__.replace("_", " ").title())
                self.minijeux.append((f"{emoji} {titre}", func))

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction interne — validation de la quête
    # ────────────────────────────────────────────────────────────────────────────
    async def _valider_quete(
        self,
        user:            discord.User | discord.Member,
        total_score:     int,
        channel:         discord.abc.Messageable | None  = None,
        ctx_or_inter:    discord.Interaction | commands.Context | None = None
    ):
        """Valide la quête 'entrainement' si score >= 5000 et envoie un embed de félicitations."""
        if total_score < 5000:
            return

        new_lvl = db_valider_quete(user.id)
        if new_lvl is None:
            return

        embed = discord.Embed(
            title="🎉 Quête accomplie !",
            description=(
                f"Bravo **{user.display_name}** ! Tu as terminé la quête **Entraînement cérébral** 🏆\n\n"
                f"⭐ **Niveau +1 !** (Niveau {new_lvl})"
            ),
            color=0xFFD700
        )

        try:
            if channel:
                await channel.send(embed=embed)
            elif isinstance(ctx_or_inter, discord.Interaction):
                if not ctx_or_inter.response.is_done():
                    await ctx_or_inter.response.send_message(embed=embed)
                else:
                    await ctx_or_inter.followup.send(embed=embed)
            else:
                await user.send(embed=embed)
        except Exception as e:
            log.exception("[cerebral] Erreur envoi embed quête : %s", e)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(
        name="entrainementcerebral",
        aliases=["ec", "kawashima", "k"],
        help="Entraînement cérébral composé de 5 mini-jeux."
    )
    async def cerebral_cmd(self, ctx: commands.Context, arg: str = ""):
        if arg.lower() == "top":
            await self.show_leaderboard(ctx)
        elif arg.lower() in ["m", "multi"]:
            await self.run_arcade(ctx, multiplayer=True)
        else:
            await self.run_arcade(ctx)

    @cerebral_cmd.error
    async def cerebral_cmd_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ Attends encore {error.retry_after:.1f}s.")
        else:
            log.exception("[!cerebral] Erreur non gérée : %s", error)
            await ctx.send("❌ Une erreur est survenue.")

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="cerebral",
        description="Entraînement cérébral composé de 5 mini-jeux."
    )
    async def cerebral_slash(self, interaction: discord.Interaction, arg: str = ""):
        await interaction.response.defer()
        if arg.lower() == "top":
            await self.show_leaderboard(interaction)
        elif arg.lower() in ["m", "multi"]:
            await self.run_arcade(interaction, multiplayer=True)
        else:
            await self.run_arcade(interaction)

    @cerebral_slash.error
    async def cerebral_slash_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.followup.send(f"⏳ Attends encore {error.retry_after:.1f}s.", ephemeral=True)
        else:
            log.exception("[/cerebral] Erreur non gérée : %s", error)
            await interaction.followup.send("❌ Une erreur est survenue.", ephemeral=True)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Lancement du mode arcade
    # ────────────────────────────────────────────────────────────────────────────
    async def run_arcade(self, ctx_or_interaction, multiplayer=False):
        guild    = getattr(ctx_or_interaction, "guild", None)
        guild_id = guild.id if guild else None

        if guild_id and guild_id in self.active_sessions:
            msg = "⚠️ Un entraînement cérébral est déjà en cours sur ce serveur."
            if isinstance(ctx_or_interaction, discord.Interaction):
                return await ctx_or_interaction.followup.send(msg, ephemeral=True)
            return await ctx_or_interaction.send(msg)

        if guild_id:
            self.active_sessions.add(guild_id)

        try:
            if isinstance(ctx_or_interaction, discord.Interaction):
                send  = ctx_or_interaction.followup.send
                users = [ctx_or_interaction.user]
            else:
                send  = ctx_or_interaction.send
                users = [ctx_or_interaction.author]

            total_score  = {}
            results      = {}
            title_mode   = "Mode Multijoueur" if multiplayer else "Mode Arcade"
            ready_users  = []

            description_text = (
                f"{'🔹 Mode Multijoueur : entre 2 et 10 joueurs.' if multiplayer else ''}\n"
                "Tu vas affronter 5 mini-jeux rapides pour tester ton cerveau.\n"
                "Appuie sur le bouton ci-dessous quand tu es prêt à commencer."
            )

            start_embed = discord.Embed(
                title=f"🧠 Entraînement cérébral — {title_mode}",
                description=description_text,
                color=discord.Color.blurple()
            )

            class ReadyButton(discord.ui.View):
                def __init__(self):
                    super().__init__(timeout=30)
                    self.ready_event = asyncio.Event()
                    self.clicked     = False

                @discord.ui.button(label="🟢 Je suis prêt !", style=discord.ButtonStyle.success)
                async def ready(self, interaction: discord.Interaction, button: discord.ui.Button):
                    if multiplayer:
                        if interaction.user in ready_users:
                            return await interaction.response.send_message("✅ Tu es déjà prêt !", ephemeral=True)
                        if len(ready_users) >= 10:
                            return await interaction.response.send_message("🚫 Maximum 10 joueurs atteint.", ephemeral=True)
                        ready_users.append(interaction.user)
                        participants = ", ".join([u.name for u in ready_users])
                        embed = discord.Embed(
                            title=f"🧠 Entraînement cérébral — {title_mode}",
                            description=f"Participants prêts : {participants}\n\nAppuyez sur le bouton pour rejoindre (30s restantes)...",
                            color=discord.Color.blurple()
                        )
                        await interaction.response.edit_message(embed=embed, view=self)
                    else:
                        if interaction.user != users[0]:
                            return await interaction.response.send_message("🚫 Ce n'est pas ton entraînement.", ephemeral=True)
                        button.disabled = True
                        button.label    = "✅ C'est parti !"
                        try:
                            await interaction.response.edit_message(view=self)
                        except discord.InteractionResponded:
                            await interaction.message.edit(view=self)
                        self.clicked = True
                        self.ready_event.set()

                async def on_timeout(self):
                    if not self.clicked:
                        for child in self.children:
                            child.disabled = True
                            child.label    = "⏰ Temps écoulé"
                        self.ready_event.set()

            view      = ReadyButton()
            msg_start = await send(embed=start_embed, view=view)
            await view.ready_event.wait()

            if not multiplayer and not view.clicked:
                timeout_embed = discord.Embed(
                    title="⏰ Temps écoulé",
                    description="Personne n'a cliqué à temps. Relance la commande pour rejouer !",
                    color=discord.Color.red()
                )
                return await msg_start.edit(embed=timeout_embed, view=None)

            if multiplayer:
                if len(ready_users) < 2:
                    cancel_embed = discord.Embed(
                        title="❌ Pas assez de joueurs",
                        description="Il faut au moins **2 joueurs** pour lancer la partie.",
                        color=discord.Color.red()
                    )
                    return await msg_start.edit(embed=cancel_embed, view=None)
                view.clicked = True
                for child in view.children:
                    child.disabled = True
                    child.label    = "✅ Partie en cours"
                await msg_start.edit(view=view)

            random.shuffle(self.minijeux)
            selected_games = self.minijeux[:5]
            active_players = ready_users if multiplayer else users

            for index, (name, game) in enumerate(selected_games, start=1):
                game_embed = discord.Embed(
                    title=f"🧩 Mini-jeu {index} — {name}",
                    description=(
                        "Le plus rapide à donner la bonne réponse gagne !"
                        if multiplayer
                        else f"{users[0].mention}, c'est ton tour !"
                    ),
                    color=discord.Color.blurple()
                )
                msg_game = await send(embed=game_embed)
                start    = time.time()

                if multiplayer:
                    def check(m):
                        return m.author in active_players and m.channel == msg_game.channel
                    winner = None
                    try:
                        while True:
                            msg     = await self.bot.wait_for("message", check=check, timeout=25)
                            success = await game(msg_game, game_embed, lambda: msg.author.id, self.bot, msg_override=msg)
                            if success:
                                winner = msg.author
                                break
                    except asyncio.TimeoutError:
                        winner = None

                    elapsed = round(time.time() - start, 2)
                    if winner:
                        score = 1000 + max(0, 500 - int(elapsed * 25))
                        total_score[winner.id] = total_score.get(winner.id, 0) + score
                        results.setdefault(winner.id, []).append((index, name, True, elapsed, score))
                        result_embed = discord.Embed(
                            title=f"🏆 {winner.name} a trouvé la bonne réponse !",
                            description=f"⏱️ Temps : `{elapsed}s`\n🏅 Score : `{score}` pts",
                            color=discord.Color.green()
                        )
                    else:
                        result_embed = discord.Embed(
                            title="❌ Personne n'a trouvé la bonne réponse",
                            description="Essayez d'être plus rapides au prochain mini-jeu !",
                            color=discord.Color.red()
                        )
                    await send(embed=result_embed)

                else:
                    get_user_id = lambda: users[0].id
                    success     = await game(msg_game, game_embed, get_user_id, self.bot)
                    elapsed     = round(time.time() - start, 2)
                    score       = (1000 + max(0, 500 - int(elapsed * 25))) if success else 0
                    total_score[users[0].id] = total_score.get(users[0].id, 0) + score
                    results.setdefault(users[0].id, []).append((index, name, success, elapsed, score))
                    result_embed = discord.Embed(
                        title=f"🎯 Résultat — {name} ({users[0].name})",
                        description=(
                            f"{'✅ Réussi' if success else '❌ Raté'}\n"
                            f"⏱️ Temps : `{elapsed}s`\n"
                            f"🏅 Score : `{score}` pts"
                        ),
                        color=discord.Color.green() if success else discord.Color.red()
                    )
                    await send(embed=result_embed)

                await asyncio.sleep(1.5)

            # ─── Résultats finaux ─────────────────────────────────────────────
            for player in active_players:
                if player.id not in total_score:
                    continue

                player_results = results[player.id]
                results_text   = "\n".join(
                    f"**Jeu {i}** {'✅' if s else '❌'} {name}{f' — {t}s' if s else ''}"
                    for i, name, s, t, _ in player_results
                )
                total = total_score[player.id]

                if total >= 5000:
                    rank = "🧠 Génie cérébral"
                elif total >= 3500:
                    rank = "🤓 Bonne forme mentale"
                elif total >= 2000:
                    rank = "🙂 Correct"
                else:
                    rank = "😴 En veille..."

                final_embed = discord.Embed(
                    title=f"🏁 Résultats — {player.name}",
                    description=(
                        f"**Résultats des 5 jeux :**\n{results_text}\n\n"
                        f"**Score total :** `{total:,}` pts\n"
                        f"**Niveau cérébral :** {rank}"
                    ),
                    color=discord.Color.gold()
                )
                await send(embed=final_embed)

                # ─── Sauvegarde score solo ─────────────────────────────────
                if not multiplayer:
                    db_save_score(player.id, player.name, total)

                # ─── Validation quête ──────────────────────────────────────
                await self._valider_quete(
                    player,
                    total,
                    channel=getattr(ctx_or_interaction, "channel", None),
                    ctx_or_inter=ctx_or_interaction
                )

        finally:
            if guild_id:
                self.active_sessions.discard(guild_id)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Classement global
    # ────────────────────────────────────────────────────────────────────────────
    async def show_leaderboard(self, ctx_or_interaction):
        embed   = discord.Embed(
            title="🏆 Entraînement cérébral — Top 10",
            description="Voici le classement global des meilleurs scores !",
            color=discord.Color.gold()
        )
        entries  = db_get_leaderboard(10)
        top_text = "\n".join(
            f"**{i+1}.** {entry['username']} — `{entry['score']:,}` pts"
            for i, entry in enumerate(entries)
        ) or "*Aucun score enregistré pour le moment*"

        embed.add_field(name="Top 10", value=top_text, inline=False)

        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.followup.send(embed=embed)
        else:
            await ctx_or_interaction.send(embed=embed)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = EntrainementCerebral(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Jeux"
    await bot.add_cog(cog)
