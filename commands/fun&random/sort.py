# ────────────────────────────────────────────────────────────────────────────────
# sorting.py — Visualisation d'algorithmes de tri /sorting et !sorting
# Objectif : Visualiser différents algorithmes de tri en temps réel dans Discord
# Catégorie : Fun
# Accès : Tous
# Cooldown : 1 utilisation / 10 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
import random
import asyncio
from discord import app_commands
from discord.ext import commands
from utils.discord_utils import safe_send, safe_respond
from utils.algorithms import algorithms as all_algos  # ✅ Import des algorithmes

# ────────────────────────────────────────────────────────────────────────────────
# Visualisation des barres
# ────────────────────────────────────────────────────────────────────────────────
def render_bars(data, highlight_indices=None, max_length=None):
    """
    Génère une représentation visuelle des barres pour Discord.
    highlight_indices : liste des indices des colonnes en cours de déplacement (orange)
    """
    if highlight_indices is None:
        highlight_indices = []
    if max_length is None:
        max_length = len(data)  # 12 pour ton cas, au moins autant que de barres
    max_val = max(data)
    lines = []
    for i, n in enumerate(data):
        # utilisation de round pour éviter les doublons visuels
        height = round((n / max_val) * max_length)
        if height < 1:
            height = 1  # au moins 1 bloc pour les petites valeurs
        if i in highlight_indices:
            bar = "🟥" * height
        else:
            bar = "⬜" * height
        lines.append(bar)
    return "\n".join(lines)

# ────────────────────────────────────────────────────────────────────────────────
# Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class Sorting(commands.Cog):
    """Commande /sorting et !sorting — Visualise un algorithme de tri en temps réel"""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # On récupère la description depuis algo.desc si elle existe
        self.algorithms = {
            name: {"func": func, "desc": getattr(func, "desc", "Description à compléter")}
            for name, func in all_algos.items()
        }

    async def visualize_sorting(self, channel_or_interaction, algorithm_name: str):
        algo_info = self.algorithms[algorithm_name]
        data = list(range(1, 13))
        random.shuffle(data)
        algo = algo_info["func"]
        delay = 0.25
        msg = None
        iteration = 0

        async def send(embed):
            nonlocal msg
            if isinstance(channel_or_interaction, discord.Interaction):
                if msg:
                    await msg.edit(embed=embed)
                else:
                    msg = await safe_respond(channel_or_interaction, embed=embed)
            else:
                if msg:
                    await msg.edit(embed=embed)
                else:
                    msg = await safe_send(channel_or_interaction, embed=embed)

        # première étape
        embed = discord.Embed(
            title=f"🔄 {algorithm_name} — En cours...",
            description=f"{algo_info['desc']}\n```\n{render_bars(data)}\n```",
            color=discord.Color.blurple()
        )
        await send(embed)

        # visualisation dynamique
        async for step, highlight in algo(data.copy()):
            iteration += 1
            await asyncio.sleep(delay)
            embed = discord.Embed(
                title=f"🔄 {algorithm_name} — Étape {iteration}",
                description=f"{algo_info['desc']}\n```\n{render_bars(step, highlight)}\n```",
                color=discord.Color.orange()
            )
            await send(embed)

        # résultat final
        sorted_data = sorted(data)
        embed = discord.Embed(
            title=f"✅ {algorithm_name} terminé !",
            description=f"{algo_info['desc']}\n```\n{render_bars(sorted_data)}\n```",
            color=discord.Color.green()
        )
        embed.add_field(name="🧮 Itérations totales", value=f"{iteration}", inline=False)
        await send(embed)

    # ────────────────────────────────────────────────────────────────────────────
    # Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(name="sorting",description="Visualise un algorithme de tri en temps réel.")
    @app_commands.describe(algorithme="Trie 12 barres en longueurs différentes selon un algorithme.")
    @app_commands.checks.cooldown(1, 10.0, key=lambda i: i.user.id)
    async def slash_sorting(self, interaction: discord.Interaction, algorithme: str = None):
        await self.handle_sorting(interaction, algorithme)

    # ────────────────────────────────────────────────────────────────────────────
    # Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="sorting", aliases=["sort"], help="Trie 12 barres en longueurs différentes selon un algorithme.")
    @commands.cooldown(1, 10.0, commands.BucketType.user)
    async def prefix_sorting(self, ctx: commands.Context, *, algorithme: str = None):
        await self.handle_sorting(ctx.channel, algorithme)

    # ────────────────────────────────────────────────────────────────────────────
    # Gestion logique commune
    # ────────────────────────────────────────────────────────────────────────────
    async def handle_sorting(self, channel_or_interaction, algorithme: str = None):
        algos_list = sorted(self.algorithms.keys())
        algo_dict = {str(i + 1): name for i, name in enumerate(algos_list)}

        if not algorithme:
            embed = discord.Embed(
                title="🎨 Visualisation d'algorithmes de tri",
                description="Choisis un algorithme avec son **numéro**, son **nom**, ou tape `random` pour un aléatoire.",
                color=discord.Color.blurple()
            )
            embed.add_field(
                name="📚 Algorithmes disponibles",
                value="\n".join([f"**{i+1}.** {name}" for i, name in enumerate(algos_list)]),
                inline=False
            )
            embed.set_footer(text="Exemples : /sorting 3 | /sorting Bubble Sort | /sorting random")
            if isinstance(channel_or_interaction, discord.Interaction):
                await safe_respond(channel_or_interaction, embed=embed)
            else:
                await safe_send(channel_or_interaction, embed=embed)
            return

        algorithme = algorithme.strip().lower()
        if algorithme == "random":
            algo_name = random.choice(algos_list)
        elif algorithme.isdigit() and algorithme in algo_dict:
            algo_name = algo_dict[algorithme]
        else:
            matched = next((name for name in algos_list if name.lower() == algorithme), None)
            if not matched:
                algos_str = "\n".join([f"**{i+1}.** {name}" for i, name in enumerate(algos_list)])
                err = discord.Embed(
                    title="❌ Algorithme inconnu",
                    description=f"Choisis un algorithme valide :\n\n{algos_str}",
                    color=discord.Color.red()
                )
                if isinstance(channel_or_interaction, discord.Interaction):
                    await safe_respond(channel_or_interaction, embed=err)
                else:
                    await safe_send(channel_or_interaction, embed=err)
                return
            algo_name = matched

        await self.visualize_sorting(channel_or_interaction, algo_name)

# ────────────────────────────────────────────────────────────────────────────────
# Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = Sorting(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Fun&Random"
    await bot.add_cog(cog)
