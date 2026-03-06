# ────────────────────────────────────────────────────────────────────────────────
# 📌 quincy_hollow_shinigami.py — Quincy / Hollow / Shinigami (Pierre/Feuille/Ciseaux)
# Objectif : Jouer à Quincy 🏹 / Hollow 👹 / Shinigami ⚔️ en vs Bot ou vs Joueur
# Catégorie : Bleach
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import random
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from utils.discord_utils import safe_send, safe_respond, safe_interact, safe_edit

# ────────────────────────────────────────────────────────────────────────────────
# 🧰 Constantes & utilitaires
# ────────────────────────────────────────────────────────────────────────────────
CHOICES = ["quincy", "hollow", "shinigami"]
EMOJI   = {"quincy": "🏹", "hollow": "👹", "shinigami": "⚔️"}

def determine_winner(player_choice: str, opponent_choice: str) -> str:
    """
    Quincy > Hollow | Hollow > Shinigami | Shinigami > Quincy.
    Retourne : 'joueur', 'adversaire', 'egal'.
    """
    if player_choice == opponent_choice:
        return "egal"
    wins = {"quincy": "hollow", "hollow": "shinigami", "shinigami": "quincy"}
    return "joueur" if wins[player_choice] == opponent_choice else "adversaire"

def build_result_embed(player_choice: str, bot_choice: str, result: str, footer: str) -> discord.Embed:
    """Construit l'embed de résultat vs bot."""
    base = f"Tu as choisi {EMOJI[player_choice]} **{player_choice.capitalize()}**.\nLe bot a choisi {EMOJI[bot_choice]} **{bot_choice.capitalize()}**."
    if result == "egal":
        title, desc, color = "ÉGALITÉ 🤝", base, 0x95A5A6
    elif result == "joueur":
        title, desc, color = "VICTOIRE 🎉", base + "\n\nTu gagnes !", 0x57F287
    else:
        title, desc, color = "DÉFAITE 😵", base + "\n\nTu perds.", 0xED4245
    embed = discord.Embed(title=title, description=desc, color=color)
    embed.set_footer(text=footer)
    return embed

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ UI — Bouton de choix vs bot
# ────────────────────────────────────────────────────────────────────────────────

class SoloChoiceButton(discord.ui.Button):
    def __init__(self, choice_key: str, author_id: int):
        super().__init__(
            style=discord.ButtonStyle.primary,
            label=f"{EMOJI[choice_key]} {choice_key.capitalize()}",
            custom_id=f"solo:{author_id}:{choice_key}"
        )
        self.choice_key = choice_key
        self.author_id  = author_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            return await safe_respond(interaction, "❌ Ce duel est réservé à l'auteur.", ephemeral=True)

        bot_choice = random.choice(CHOICES)
        result     = determine_winner(self.choice_key, bot_choice)
        footer     = f"{interaction.user.display_name} vs Bot"
        embed      = build_result_embed(self.choice_key, bot_choice, result, footer)

        for child in self.view.children:
            child.disabled = True
        await safe_interact(interaction, embed=embed, view=self.view, edit=True)
        self.view.stop()

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ UI — Bouton de choix en duel
# ────────────────────────────────────────────────────────────────────────────────

class ChoiceButton(discord.ui.Button):
    def __init__(self, choice_key: str, owner_id: int):
        super().__init__(
            style=discord.ButtonStyle.primary,
            label=f"{EMOJI[choice_key]} {choice_key.capitalize()}",
            custom_id=f"choice:{owner_id}:{choice_key}"
        )
        self.choice_key = choice_key
        self.owner_id   = owner_id

    async def callback(self, interaction: discord.Interaction):
        view: DuelView = self.view
        if interaction.user.id != self.owner_id:
            return await safe_respond(interaction, "❌ Ce bouton n'est pas pour toi.", ephemeral=True)
        if view.choices.get(self.owner_id) is not None:
            return await safe_respond(interaction, "✅ Tu as déjà choisi.", ephemeral=True)

        view.choices[self.owner_id] = self.choice_key
        for child in view.children:
            if isinstance(child, ChoiceButton) and child.owner_id == self.owner_id:
                child.disabled = True

        await safe_interact(interaction, embed=view.progress_embed(), view=view, edit=True)

        if len(view.choices) == 2 and all(k in view.choices for k in (view.challenger_id, view.opponent_id)):
            await view.finish_game(interaction)

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ UI — Bouton accepter/décliner
# ────────────────────────────────────────────────────────────────────────────────

class AcceptDeclineButton(discord.ui.Button):
    def __init__(self, accept: bool, challenger_id: int, opponent_id: int):
        label     = "✅ Accepter" if accept else "❌ Décliner"
        style     = discord.ButtonStyle.success if accept else discord.ButtonStyle.danger
        custom_id = f"challenge:{opponent_id}:{'accept' if accept else 'decline'}"
        super().__init__(style=style, label=label, custom_id=custom_id)
        self.accept        = accept
        self.challenger_id = challenger_id
        self.opponent_id   = opponent_id

    async def callback(self, interaction: discord.Interaction):
        view: ChallengeView = self.view
        if interaction.user.id != self.opponent_id:
            return await safe_respond(interaction, "❌ Seul l'adversaire invité peut accepter ou refuser.", ephemeral=True)

        if not self.accept:
            embed = discord.Embed(
                title="DÉFI REFUSÉ ❌",
                description=f"<@{self.opponent_id}> a refusé le défi de <@{self.challenger_id}>.",
                color=0xFF4D4D
            )
            await safe_interact(interaction, embed=embed, view=None, edit=True)
            return

        duel_view = DuelView(view.bot, view.challenger_id, view.opponent_id, view.channel)
        await safe_interact(interaction, embed=duel_view.start_embed(), view=duel_view, edit=True)


class ChallengeView(discord.ui.View):
    def __init__(self, bot: commands.Bot, challenger_id: int, opponent_id: int, channel, timeout: float = 60.0):
        super().__init__(timeout=timeout)
        self.bot           = bot
        self.challenger_id = challenger_id
        self.opponent_id   = opponent_id
        self.channel       = channel
        self.add_item(AcceptDeclineButton(True,  challenger_id, opponent_id))
        self.add_item(AcceptDeclineButton(False, challenger_id, opponent_id))

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ UI — Vue de duel joueur vs joueur
# ────────────────────────────────────────────────────────────────────────────────

class DuelView(discord.ui.View):
    def __init__(self, bot: commands.Bot, challenger_id: int, opponent_id: int, channel, timeout: float = 120.0):
        super().__init__(timeout=timeout)
        self.bot           = bot
        self.challenger_id = challenger_id
        self.opponent_id   = opponent_id
        self.channel       = channel
        self.choices: dict[int, Optional[str]] = {}
        self.message       = None

        for choice in CHOICES:
            self.add_item(ChoiceButton(choice, challenger_id))
        self.add_item(discord.ui.Button(style=discord.ButtonStyle.secondary, label="—", disabled=True))
        for choice in CHOICES:
            self.add_item(ChoiceButton(choice, opponent_id))

    def start_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="⚔️ Défi Quincy / Hollow / Shinigami",
            description=f"<@{self.challenger_id}> **vs** <@{self.opponent_id}>\n\nChacun clique sur ses boutons pour choisir.",
            color=0x2F3136
        )
        embed.add_field(name="Choix", value=" — ".join(f"{EMOJI[c]} {c.capitalize()}" for c in CHOICES), inline=False)
        embed.set_footer(text="Tu as 120s pour choisir. Les boutons sont réservés à chaque joueur.")
        return embed

    def progress_embed(self) -> discord.Embed:
        c1 = "✅" if self.choices.get(self.challenger_id) else "⏳"
        c2 = "✅" if self.choices.get(self.opponent_id) else "⏳"
        return discord.Embed(
            title="⌛ En attente des choix...",
            description=f"<@{self.challenger_id}> {c1}\n<@{self.opponent_id}> {c2}",
            color=0x7289DA
        )

    async def finish_game(self, interaction: discord.Interaction):
        ch_choice = self.choices[self.challenger_id]
        op_choice = self.choices[self.opponent_id]
        result    = determine_winner(ch_choice, op_choice)

        if result == "egal":
            title = "ÉGALITÉ 🤝"
            desc  = f"{EMOJI[ch_choice]} {ch_choice.capitalize()} vs {EMOJI[op_choice]} {op_choice.capitalize()} — Personne ne gagne."
            color = 0x95A5A6
        elif result == "joueur":
            title = "VICTOIRE 🎉"
            desc  = f"<@{self.challenger_id}> gagne !\n{EMOJI[ch_choice]} {ch_choice.capitalize()} bat {EMOJI[op_choice]} {op_choice.capitalize()}."
            color = 0x57F287
        else:
            title = "DÉFAITE 😵"
            desc  = f"<@{self.opponent_id}> gagne !\n{EMOJI[op_choice]} {op_choice.capitalize()} bat {EMOJI[ch_choice]} {ch_choice.capitalize()}."
            color = 0xED4245

        embed = discord.Embed(title=title, description=desc, color=color)
        embed.add_field(
            name="Choix",
            value=f"<@{self.challenger_id}> → {EMOJI[ch_choice]} {ch_choice.capitalize()}\n<@{self.opponent_id}> → {EMOJI[op_choice]} {op_choice.capitalize()}",
            inline=False
        )
        for child in self.children:
            child.disabled = True
        await safe_edit(interaction.message, embed=embed, view=self)
        self.stop()

    async def on_timeout(self):
        has_ch = self.choices.get(self.challenger_id)
        has_op = self.choices.get(self.opponent_id)
        if has_ch and not has_op:
            desc  = f"<@{self.opponent_id}> n'a pas choisi à temps. <@{self.challenger_id}> gagne par forfait."
            color = 0x57F287
        elif has_op and not has_ch:
            desc  = f"<@{self.challenger_id}> n'a pas choisi à temps. <@{self.opponent_id}> gagne par forfait."
            color = 0x57F287
        else:
            desc  = "Temps écoulé : aucun des joueurs n'a choisi."
            color = 0x95A5A6

        embed = discord.Embed(title="⌛ Duel terminé (timeout)", description=desc, color=color)
        for child in self.children:
            child.disabled = True
        await safe_send(self.channel, embed=embed)
        self.stop()

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────

class QuincyHollowShinigami(commands.Cog):
    """
    Commandes /shifumi et !shifumi — Quincy / Hollow / Shinigami.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Fonction interne commune
    # ────────────────────────────────────────────────────────────────────────────
    def _build_vs_bot_view(self, author_id: int) -> tuple[discord.Embed, discord.ui.View]:
        embed = discord.Embed(
            title="🎮 Quincy / Hollow / Shinigami — VS BOT",
            description=" — ".join(f"{EMOJI[c]} {c.capitalize()}" for c in CHOICES) + "\nChoisis ton camp en cliquant un bouton.",
            color=0x2F3136
        )
        view = discord.ui.View(timeout=30.0)
        for choice in CHOICES:
            view.add_item(SoloChoiceButton(choice, author_id))
        return embed, view

    def _build_challenge_view(self, challenger_id: int, opponent_id: int, channel) -> tuple[discord.Embed, ChallengeView]:
        embed = discord.Embed(
            title="⚔️ Défi Quincy / Hollow / Shinigami",
            description=f"<@{challenger_id}> a défié <@{opponent_id}> !\n<@{opponent_id}>, acceptez-vous ?",
            color=0xFFA500
        )
        embed.set_footer(text="Le défi expirera dans 60s.")
        view = ChallengeView(self.bot, challenger_id, opponent_id, channel=channel)
        return embed, view

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(name="shifumi",description="Joue à Quincy 🏹 / Hollow 👹 / Shinigami ⚔️ — précisez un adversaire pour défier.")
    @app_commands.describe(opponent="Mentionner un membre pour le défier (optionnel).")
    @app_commands.checks.cooldown(rate=1, per=5.0, key=lambda i: i.user.id)
    async def slash_quincy_hollow_shinigami(self, interaction: discord.Interaction, opponent: Optional[discord.Member] = None):
        if opponent is None or opponent.bot:
            embed, view = self._build_vs_bot_view(interaction.user.id)
            await safe_respond(interaction, embed=embed, view=view)
            return

        if opponent.id == interaction.user.id:
            return await safe_respond(interaction, "❌ Tu ne peux pas te défier toi-même.", ephemeral=True)

        embed, view = self._build_challenge_view(interaction.user.id, opponent.id, interaction.channel)
        await safe_respond(interaction, embed=embed, view=view)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="shifumi",aliases=["sfm", "pfc"],help="Joue à Quincy 🏹 / Hollow 👹 / Shinigami ⚔️.")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_quincy_hollow_shinigami(self, ctx: commands.Context, member: Optional[discord.Member] = None):
        if member is None or member.bot:
            embed, view = self._build_vs_bot_view(ctx.author.id)
            await safe_send(ctx.channel, embed=embed, view=view)
            return

        if member.id == ctx.author.id:
            return await safe_send(ctx.channel, "❌ Tu ne peux pas te défier toi-même.")

        embed, view = self._build_challenge_view(ctx.author.id, member.id, ctx.channel)
        await safe_send(ctx.channel, embed=embed, view=view)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = QuincyHollowShinigami(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Bleach"
    await bot.add_cog(cog)
