# ────────────────────────────────────────────────────────────────────────────────
# 📌 gpt.py — Commande /gpt et !!gpt : Chat libre avec GPT-OSS (Cloud NVIDIA)
# Objectif : Permettre une conversation libre avec le modèle GPT-OSS hébergé sur le cloud NVIDIA.
# Catégorie : Fun&Random
# Accès : Tous
# Cooldown : 1 utilisation / 4 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
import asyncio
from utils.discord_utils import safe_send, safe_respond  # ✅ Utilitaires sécurisés
from utils.gpt_oss_client import get_simple_response     # 🔗 Client GPT-OSS

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class GPTChat(commands.Cog):
    """
    Commande /gpt et !!gpt — conversation libre avec le modèle GPT-OSS (Cloud NVIDIA)
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH : /gpt <message>
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(name="gpt",description="Chat libre avec le modèle GPT-OSS (Cloud NVIDIA)")
    @app_commands.describe(prompt="Message ou question à envoyer au modèle.")
    @app_commands.checks.cooldown(1, 4.0, key=lambda i: i.user.id)
    async def slash_gpt(self, interaction: discord.Interaction, prompt: str):
        """Commande slash — conversation libre avec GPT-OSS"""
        await self._handle_gpt_request(interaction=interaction, prompt=prompt)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX : !!gpt <message>
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="gpt", help="Chat libre avec le modèle GPT-OSS (Cloud NVIDIA)")
    @commands.cooldown(1, 4.0, commands.BucketType.user)
    async def prefix_gpt(self, ctx: commands.Context, *, prompt: str = None):
        """Commande préfixe — conversation libre avec GPT-OSS"""
        if not prompt:
            await safe_send(
                ctx.channel,
                embed=self._build_embed(
                    "💭 **Utilisation :**",
                    "Tape simplement `!!gpt <ton message>` pour discuter avec le modèle.\n"
                    "Exemple : `!!gpt explique-moi le Bankai d’Ichigo`"
                )
            )
            return
        await self._handle_gpt_request(ctx=ctx, prompt=prompt)

    # ────────────────────────────────────────────────────────────────────────────
    # ⚙️ Traitement principal de la requête GPT
    # ────────────────────────────────────────────────────────────────────────────
    async def _handle_gpt_request(self, ctx: commands.Context = None, interaction: discord.Interaction = None, prompt: str = None):
        """Gère la logique commune entre la commande slash et préfixe"""
        user = (ctx.author if ctx else interaction.user)

        # ─────────────── Limite de longueur du prompt ───────────────
        if len(prompt) > 90:
            msg = (
                f"⚠️ Ton message dépasse la limite de **90 caractères**.\n"
                f"({len(prompt)} actuellement)"
            )
            await self._send(ctx, interaction, "⚠️ **Trop long !**", msg)
            return

        try:
            # 🔄 Exécution du modèle sur un thread asynchrone
            response = await asyncio.to_thread(get_simple_response, prompt)

            # ─────────────── Vérifications de sécurité ───────────────
            if not response or response.startswith("⚠️"):
                response = "⚠️ Réponse vide ou erreur du modèle."
            elif len(response) > 500:
                response = response[:500].rstrip() + "…"

        except Exception as e:
            print(f"[Erreur GPT Commande] {e}")
            await self._send(ctx, interaction, "⚠️ **Erreur :**", "Impossible de contacter le modèle pour le moment.")
            return

        # ✅ Envoi de la réponse finale
        await self._send(
            ctx,
            interaction,
            f"💬 **Réponse à {user.display_name} :**",
            response
        )

    # ────────────────────────────────────────────────────────────────────────────
    # 🪶 Méthodes utilitaires internes
    # ────────────────────────────────────────────────────────────────────────────
    async def _send(self, ctx: commands.Context, interaction: discord.Interaction, title: str, description: str):
        """Envoi automatique selon le type d’appel (slash ou prefix)"""
        embed = self._build_embed(title, description)
        if interaction:
            await safe_respond(interaction, embed=embed)
        elif ctx:
            await safe_send(ctx.channel, embed=embed)

    def _build_embed(self, title: str, description: str) -> discord.Embed:
        """Construit un embed propre et uniforme"""
        if not description:
            description = "⚠️ Aucune donnée à afficher."
        elif len(description) > 4000:
            description = description[:4000] + "\n\n…(contenu tronqué)"

        embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Color.blurple()
        )
        embed.set_footer(text="GPT-OSS NVIDIA • Cloud")
        return embed

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = GPTChat(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Fun&Random"
    await bot.add_cog(cog)
