# ────────────────────────────────────────────────────────────────────────────────
# 📌 test_kawashima.py — Tester un mini-jeu par numéro ou tous les jeux
# Objectif : Lister tous les mini-jeux, paginer si nécessaire et les tester facilement
# Catégorie : Admin
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import asyncio
import inspect

import discord
from discord import app_commands
from discord.ext import commands

from utils import kawashima_games
from utils.discord_utils import safe_send, safe_edit, safe_interact

# ────────────────────────────────────────────────────────────────────────────────
# ⚙️ Constantes
# ────────────────────────────────────────────────────────────────────────────────
PAGE_SIZE    = 10
GAME_TIMEOUT = 30

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────

class TestKawashima(commands.Cog):
    """
    Commandes /testgame et !testgame — Tester un mini-jeu Kawashima via numéro,
    ou tous les jeux via 'all', avec pagination si nécessaire.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.games = {}
        for name, func in inspect.getmembers(kawashima_games, inspect.iscoroutinefunction):
            if not name.startswith("_"):
                title = getattr(func, "title", func.__name__)
                self.games[title] = func
        self.sorted_titles = sorted(self.games.keys())

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(name="testgame",description="Tester un mini-jeu via son numéro ou 'all' pour tous.")
    @app_commands.checks.cooldown(rate=1, per=5.0, key=lambda i: i.user.id)
    async def slash_testgame(self, interaction: discord.Interaction, choix: str = None):
        await safe_interact(interaction, "Chargement du quizz...", ephemeral=True)
        await self.run_game(interaction, choix)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="testgame",aliases=["tg"],help="Tester un mini-jeu via son numéro ou 'all'.")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_testgame(self, ctx: commands.Context, choix: str = None):
        await self.run_game(ctx, choix)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction interne commune
    # ────────────────────────────────────────────────────────────────────────────
    async def run_game(self, ctx_or_interaction, choix: str | int = None):
        """Affiche la liste paginée, lance un mini-jeu ou tous les jeux ('all')."""
        if isinstance(ctx_or_interaction, discord.Interaction):
            send = lambda *a, **kw: safe_send(ctx_or_interaction.channel, *a, **kw)
            user = ctx_or_interaction.user
        else:
            send = lambda *a, **kw: safe_send(ctx_or_interaction, *a, **kw)
            user = ctx_or_interaction.author

        # ─── Option ALL ───
        if isinstance(choix, str) and choix.lower() == "all":
            results = []
            for i, title in enumerate(self.sorted_titles, start=1):
                game_func = self.games[title]
                embed     = discord.Embed(
                    title=f"🧪 Mini-jeu {i}/{len(self.sorted_titles)} : {title}",
                    description="Réponds dans le chat pour jouer !",
                    color=discord.Color.blurple()
                )
                game_msg = await send(embed=embed)
                try:
                    success = await asyncio.wait_for(
                        game_func(game_msg, embed, lambda: user.id, self.bot),
                        timeout=GAME_TIMEOUT
                    )
                    if not success:
                        results.append(f"{i}. {title} — ⏱ Pas répondu ou annulé, arrêt immédiat")
                        break
                    results.append(f"{i}. {title} — ✅ Bien joué")
                except asyncio.TimeoutError:
                    results.append(f"{i}. {title} — ⏱ Pas répondu, arrêt immédiat")
                    break
                except Exception as e:
                    results.append(f"{i}. {title} — ⚠️ Erreur : {e}")
                    break
                await asyncio.sleep(1)

            summary_embed = discord.Embed(
                title="📊 Résultat de tous les mini-jeux",
                description="\n".join(results),
                color=discord.Color.gold()
            )
            return await send(embed=summary_embed)

        # ─── Pagination si aucun choix ───
        if choix is None:
            pages = [
                self.sorted_titles[i:i + PAGE_SIZE]
                for i in range(0, len(self.sorted_titles), PAGE_SIZE)
            ]

            class PageView(discord.ui.View):
                def __init__(self):
                    super().__init__(timeout=60)
                    self.page = 0

                @discord.ui.button(label="⬅️", style=discord.ButtonStyle.secondary)
                async def prev(self, interaction: discord.Interaction, button: discord.ui.Button):
                    if interaction.user != user:
                        return await safe_interact(interaction, "❌ Ce menu ne t'est pas destiné.", ephemeral=True)
                    self.page = (self.page - 1) % len(pages)
                    await self.update(interaction)

                @discord.ui.button(label="➡️", style=discord.ButtonStyle.secondary)
                async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
                    if interaction.user != user:
                        return await safe_interact(interaction, "❌ Ce menu ne t'est pas destiné.", ephemeral=True)
                    self.page = (self.page + 1) % len(pages)
                    await self.update(interaction)

                async def update(self, interaction: discord.Interaction):
                    page_text = "\n".join(
                        f"{i + 1 + self.page * PAGE_SIZE}. {title}"
                        for i, title in enumerate(pages[self.page])
                    )
                    embed = discord.Embed(
                        title=f"🧪 Liste des mini-jeux — Page {self.page + 1}/{len(pages)}",
                        description=page_text,
                        color=discord.Color.blurple()
                    )
                    await safe_edit(interaction.message, embed=embed, view=self)

            page_view = PageView()
            page_text = "\n".join(f"{i + 1}. {title}" for i, title in enumerate(pages[0]))
            embed = discord.Embed(
                title=f"🧪 Liste des mini-jeux — Page 1/{len(pages)}",
                description=page_text,
                color=discord.Color.blurple()
            )
            return await send(embed=embed, view=page_view)

        # ─── Vérification numéro ───
        if not str(choix).isdigit() or not 1 <= int(choix) <= len(self.sorted_titles):
            return await send(f"⚠️ Numéro invalide ! Choisis entre **1** et **{len(self.sorted_titles)}**, ou 'all'.")

        # ─── Lancer le mini-jeu choisi ───
        game_name = self.sorted_titles[int(choix) - 1]
        game_func = self.games[game_name]

        embed    = discord.Embed(
            title=f"🧪 Mini-jeu : {game_name}",
            description="Réponds dans le chat pour jouer !",
            color=discord.Color.blurple()
        )
        game_msg = await send(embed=embed)

        try:
            success = await asyncio.wait_for(
                game_func(game_msg, embed, lambda: user.id, self.bot),
                timeout=GAME_TIMEOUT
            )
            if not success:
                result_text = "⏱ Pas répondu, mini-jeu annulé"
                color       = discord.Color.orange()
            else:
                result_text = "✅ Bien joué !"
                color       = discord.Color.green()
        except asyncio.TimeoutError:
            result_text = "⏱ Pas répondu, mini-jeu annulé"
            color       = discord.Color.orange()
        except Exception as e:
            result_text = f"⚠️ Erreur : {e}"
            color       = discord.Color.orange()

        result_embed = discord.Embed(
            title=f"Résultat — {game_name}",
            description=result_text,
            color=color
        )
        await send(embed=result_embed)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = TestKawashima(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Admin"
    await bot.add_cog(cog)
