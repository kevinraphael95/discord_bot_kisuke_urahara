# ────────────────────────────────────────────────────────────────────────────────
# 📌 quincy_hollow_shinigami.py — Quincy / Hollow / Shinigami (Pierre/Feuille/Ciseaux)
# Objectif : Jouer à Quincy 🏹 / Hollow 👹 / Shinigami ⚔️ en vs Bot ou vs Joueur
# Catégorie : Bleach
# Accès : Tous
# Cooldown : 1 utilisation / 5 secondes / utilisateur
# Notes :
#  - Slash + préfixe sont disponibles.
#  - Mode sans adversaire -> vs Bot (immédiat).
#  - Mode avec adversaire -> envoi d'un défi; l'adversaire peut accepter/decliner.
#  - Tous les boutons sont protégés : seul le joueur concerné peut cliquer sur ses boutons.
#  - Utilise safe_send / safe_respond pour envoyer les réponses (comme dans ton template).
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord
from discord import app_commands
from discord.ext import commands
import random
from typing import Optional

from utils.discord_utils import safe_send, safe_respond  # ✅ Utilitaires sécurisés

# ────────────────────────────────────────────────────────────────────────────────
# 🧰 Constantes & utilitaires
# ────────────────────────────────────────────────────────────────────────────────
CHOICES = ["quincy", "hollow", "shinigami"]
EMOJI = {"quincy": "🏹", "hollow": "👹", "shinigami": "⚔️"}

def determine_winner(player_choice: str, opponent_choice: str) -> str:
    """
    Détermine le gagnant :
    Quincy > Hollow
    Hollow > Shinigami
    Shinigami > Quincy
    Retour : "joueur", "adversaire", "egal"
    """
    if player_choice == opponent_choice:
        return "egal"
    wins = {
        "quincy": "hollow",
        "hollow": "shinigami",
        "shinigami": "quincy"
    }
    return "joueur" if wins[player_choice] == opponent_choice else "adversaire"

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Views & Buttons (gestion des interactions)
# ────────────────────────────────────────────────────────────────────────────────
class ChoiceButton(discord.ui.Button):
    def __init__(self, label: str, choice: str, owner_id: int):
        super().__init__(style=discord.ButtonStyle.primary, label=f"{EMOJI[choice]} {label}", custom_id=f"choice:{owner_id}:{choice}")
        self.choice_key = choice
        self.owner_id = owner_id

    async def callback(self, interaction: discord.Interaction):
        view: "DuelView" = self.view  # type: ignore
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("❌ Ce bouton n'est pas pour toi.", ephemeral=True)
            return

        # si déjà choisi, informer
        if view.choices.get(self.owner_id) is not None:
            await interaction.response.send_message("✅ Tu as déjà choisi.", ephemeral=True)
            return

        view.choices[self.owner_id] = self.choice_key
        # désactiver les boutons du joueur qui a choisi (pour feedback instantané)
        for child in view.children:
            if isinstance(child, ChoiceButton) and child.owner_id == self.owner_id:
                child.disabled = True

        # met à jour le message pour montrer progression
        await interaction.response.edit_message(embed=view.progress_embed(), view=view)

        # si les deux ont choisi -> calculer résultat
        if len(view.choices) == 2 and all(k in view.choices for k in (view.challenger_id, view.opponent_id)):
            await view.finish_game(interaction)

class AcceptDeclineButton(discord.ui.Button):
    def __init__(self, accept: bool, challenger_id: int, opponent_id: int):
        label = "✅ Accepter" if accept else "❌ Décliner"
        style = discord.ButtonStyle.success if accept else discord.ButtonStyle.danger
        custom_id = f"challenge:{opponent_id}:{'accept' if accept else 'decline'}"
        super().__init__(style=style, label=label, custom_id=custom_id)
        self.accept = accept
        self.challenger_id = challenger_id
        self.opponent_id = opponent_id

    async def callback(self, interaction: discord.Interaction):
        view: "ChallengeView" = self.view  # type: ignore
        # seul l'adversaire peut accepter/decliner
        if interaction.user.id != self.opponent_id:
            await interaction.response.send_message("❌ Seul l'adversaire invité peut accepter ou refuser.", ephemeral=True)
            return

        if not self.accept:
            # decliné
            embed = discord.Embed(
                title="DÉFI REFUSÉ ❌",
                description=f"<@{self.opponent_id}> a refusé le défi de <@{self.challenger_id}>.",
                color=0xFF4D4D
            )
            await interaction.response.edit_message(embed=embed, view=None)
            return

        # accepté -> lancer duel en éditant le message pour remplacer par la vue de duel
        duel_view = DuelView(view.bot, view.challenger_id, view.opponent_id, view.channel)
        embed = duel_view.start_embed()
        await interaction.response.edit_message(embed=embed, view=duel_view)

class ChallengeView(discord.ui.View):
    def __init__(self, bot: commands.Bot, challenger_id: int, opponent_id: int, channel: discord.TextChannel, timeout: float = 60.0):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.challenger_id = challenger_id
        self.opponent_id = opponent_id
        self.channel = channel
        self.add_item(AcceptDeclineButton(True, challenger_id, opponent_id))
        self.add_item(AcceptDeclineButton(False, challenger_id, opponent_id))

class DuelView(discord.ui.View):
    def __init__(self, bot: commands.Bot, challenger_id: int, opponent_id: int, channel: discord.TextChannel, timeout: float = 120.0):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.challenger_id = challenger_id
        self.opponent_id = opponent_id
        self.channel = channel
        self.choices: dict[int, Optional[str]] = { }  # user_id -> choice_key

        # boutons pour challenger
        self.add_item(ChoiceButton("Quincy", "quincy", challenger_id))
        self.add_item(ChoiceButton("Hollow", "hollow", challenger_id))
        self.add_item(ChoiceButton("Shinigami", "shinigami", challenger_id))
        # séparateur visuel (non interactif)
        self.add_item(discord.ui.Button(style=discord.ButtonStyle.secondary, label="—", disabled=True))
        # boutons pour opponent
        self.add_item(ChoiceButton("Quincy", "quincy", opponent_id))
        self.add_item(ChoiceButton("Hollow", "hollow", opponent_id))
        self.add_item(ChoiceButton("Shinigami", "shinigami", opponent_id))

    def start_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="⚔️ Défi Quincy / Hollow / Shinigami",
            description=f"<@{self.challenger_id}> **vs** <@{self.opponent_id}>\n\nChacun clique sur ses boutons pour choisir.",
            color=0x2F3136
        )
        embed.add_field(name="Choix", value=f"{EMOJI['quincy']} Quincy — {EMOJI['hollow']} Hollow — {EMOJI['shinigami']} Shinigami", inline=False)
        embed.set_footer(text="Tu as 120s pour choisir. Les boutons sont réservés à chaque joueur.")
        return embed

    def progress_embed(self) -> discord.Embed:
        # montre qui a déjà choisi
        c1 = "✅" if self.choices.get(self.challenger_id) else "⏳"
        c2 = "✅" if self.choices.get(self.opponent_id) else "⏳"
        embed = discord.Embed(
            title="⌛ En attente des choix...",
            description=f"<@{self.challenger_id}> {c1}\n<@{self.opponent_id}> {c2}",
            color=0x7289DA
        )
        return embed

    async def finish_game(self, interaction: discord.Interaction):
        # récupère les choix
        ch_choice = self.choices[self.challenger_id]
        op_choice = self.choices[self.opponent_id]

        result = determine_winner(ch_choice, op_choice)
        if result == "egal":
            title = "ÉGALITÉ 🤝"
            desc = f"{EMOJI[ch_choice]} {ch_choice.capitalize()} vs {EMOJI[op_choice]} {op_choice.capitalize()} — Personne ne gagne."
            color = 0x95A5A6
        elif result == "joueur":
            title = "VICTOIRE 🎉"
            desc = f"<@{self.challenger_id}> gagne !\n{EMOJI[ch_choice]} {ch_choice.capitalize()} bat {EMOJI[op_choice]} {op_choice.capitalize()}."
            color = 0x57F287
        else:
            title = "DÉFAITE 😵"
            desc = f"<@{self.opponent_id}> gagne !\n{EMOJI[op_choice]} {op_choice.capitalize()} bat {EMOJI[ch_choice]} {ch_choice.capitalize()}."
            color = 0xED4245

        embed = discord.Embed(title=title, description=desc, color=color)
        embed.add_field(name="Choix", value=f"<@{self.challenger_id}> → {EMOJI[ch_choice]} {ch_choice.capitalize()}\n<@{self.opponent_id}> → {EMOJI[op_choice]} {op_choice.capitalize()}", inline=False)

        # désactiver tous les boutons et éditer le message final
        for child in self.children:
            child.disabled = True
        try:
            await interaction.message.edit(embed=embed, view=self)
        except Exception:
            # fallback si message non éditable
            await safe_send(self.channel, embed=embed)
        self.stop()

    async def on_timeout(self):
        # timeout -> si quelqu'un n'a pas joué
        desc = ""
        if self.choices.get(self.challenger_id) and not self.choices.get(self.opponent_id):
            desc = f"<@{self.opponent_id}> n'a pas choisi à temps. <@{self.challenger_id}> gagne par forfait."
            color = 0x57F287
        elif self.choices.get(self.opponent_id) and not self.choices.get(self.challenger_id):
            desc = f"<@{self.challenger_id}> n'a pas choisi à temps. <@{self.opponent_id}> gagne par forfait."
            color = 0x57F287
        else:
            desc = "Temps écoulé : aucun des joueurs n'a choisi."
            color = 0x95A5A6

        embed = discord.Embed(title="⌛ Duel terminé (timeout)", description=desc, color=color)
        # désactiver boutons si possible
        for child in self.children:
            child.disabled = True
        # essaie d'éditer le message original si possible
        try:
            # interaction non disponible ici ; on garde le dernier message dans channel
            # pour simplicité on envoie un nouveau message de fin
            await safe_send(self.channel, embed=embed)
        except Exception:
            pass
        self.stop()

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class QuincyHollowShinigami(commands.Cog):
    """
    Commande /quincy_hollow_shinigami et !quincy_hollow_shinigami — Quincy / Hollow / Shinigami
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="shifumi",
        description="Joue à Quincy 🏹 / Hollow 👹 / Shinigami ⚔️ — précisez un adversaire pour défier."
    )
    @app_commands.describe(opponent="Mentionner un membre pour le défier (optionnel).")
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def slash_quincy_hollow_shinigami(self, interaction: discord.Interaction, opponent: Optional[discord.Member] = None):
        """Commande slash sécurisée"""
        author = interaction.user
        channel = interaction.channel if isinstance(interaction.channel, discord.TextChannel) else None

        # mode vs bot si pas d'adversaire ou si adversaire est le bot lui-même
        if opponent is None or opponent.bot:
            # vs BOT
            embed = discord.Embed(
                title="🎮 Quincy / Hollow / Shinigami — VS BOT",
                description=f"{EMOJI['quincy']} Quincy — {EMOJI['hollow']} Hollow — {EMOJI['shinigami']} Shinigami\nChoisis ton camp en cliquant un bouton.",
                color=0x2F3136
            )
            # view pour joueur unique : 3 boutons
            view = discord.ui.View(timeout=30.0)
            # callback closures
            async def make_choice(inter: discord.Interaction, choice_key: str):
                player_choice = choice_key
                bot_choice = random.choice(CHOICES)
                result = determine_winner(player_choice, bot_choice)
                if result == "egal":
                    title = "ÉGALITÉ 🤝"
                    desc = f"Tu as choisi {EMOJI[player_choice]} **{player_choice.capitalize()}**.\nLe bot a choisi {EMOJI[bot_choice]} **{bot_choice.capitalize()}**."
                    color = 0x95A5A6
                elif result == "joueur":
                    title = "VICTOIRE 🎉"
                    desc = f"Tu as choisi {EMOJI[player_choice]} **{player_choice.capitalize()}**.\nLe bot a choisi {EMOJI[bot_choice]} **{bot_choice.capitalize()}**.\n\nTu gagnes !"
                    color = 0x57F287
                else:
                    title = "DÉFAITE 😵"
                    desc = f"Tu as choisi {EMOJI[player_choice]} **{player_choice.capitalize()}**.\nLe bot a choisi {EMOJI[bot_choice]} **{bot_choice.capitalize()}**.\n\nTu perds."
                    color = 0xED4245

                res_embed = discord.Embed(title=title, description=desc, color=color)
                res_embed.set_footer(text=f"{author.display_name} vs Bot")
                # désactiver view
                for c in view.children:
                    c.disabled = True
                try:
                    await inter.response.edit_message(embed=res_embed, view=view)
                except Exception:
                    await safe_send(channel or author, embed=res_embed)

            # construction des boutons
            class _TmpButton(discord.ui.Button):
                def __init__(self, choice_key: str):
                    super().__init__(style=discord.ButtonStyle.primary, label=f"{EMOJI[choice_key]} {choice_key.capitalize()}", custom_id=f"solo:{author.id}:{choice_key}")
                    self.choice_key = choice_key
                async def callback(self, inter: discord.Interaction):
                    if inter.user.id != author.id:
                        await inter.response.send_message("❌ Ce duel est réservé à l'auteur.", ephemeral=True)
                        return
                    await make_choice(inter, self.choice_key)

            view.add_item(_TmpButton("quincy"))
            view.add_item(_TmpButton("hollow"))
            view.add_item(_TmpButton("shinigami"))

            await safe_respond(interaction, embed=embed, view=view)
            return

        # MODE vs JOUEUR (opponent est un Member et non bot)
        if opponent.id == author.id:
            await safe_respond(interaction, "❌ Tu ne peux pas te défier toi-même.", ephemeral=True)
            return

        # créer message de défi avec Accept/Decline
        embed = discord.Embed(
            title="⚔️ Défi Quincy / Hollow / Shinigami",
            description=f"<@{author.id}> a défié <@{opponent.id}> !\n<@{opponent.id}>, acceptez-vous ?",
            color=0xFFA500
        )
        embed.set_footer(text="Le défi expirera dans 60s.")
        view = ChallengeView(self.bot, author.id, opponent.id, channel=interaction.channel)  # type: ignore

        await safe_respond(interaction, embed=embed, view=view)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="shifumi", aliases = ["pfc"], help="Joue à Quincy 🏹 / Hollow 👹 / Shinigami ⚔️.")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def prefix_quincy_hollow_shinigami(self, ctx: commands.Context, member: Optional[discord.Member] = None):
        """Commande préfixe simple sécurisée — usage: !quincy_hollow_shinigami [@membre]"""
        author = ctx.author
        channel = ctx.channel

        # vs bot si pas d'argument ou si mentionne un bot
        if member is None or member.bot:
            embed = discord.Embed(
                title="🎮 Quincy / Hollow / Shinigami — VS BOT",
                description=f"{EMOJI['quincy']} Quincy — {EMOJI['hollow']} Hollow — {EMOJI['shinigami']} Shinigami\nChoisis ton camp en cliquant un bouton.",
                color=0x2F3136
            )
            view = discord.ui.View(timeout=30.0)

            async def make_choice_prefix(inter: discord.Interaction, choice_key: str):
                player_choice = choice_key
                bot_choice = random.choice(CHOICES)
                result = determine_winner(player_choice, bot_choice)
                if result == "egal":
                    title = "ÉGALITÉ 🤝"
                    desc = f"Tu as choisi {EMOJI[player_choice]} **{player_choice.capitalize()}**.\nLe bot a choisi {EMOJI[bot_choice]} **{bot_choice.capitalize()}**."
                    color = 0x95A5A6
                elif result == "joueur":
                    title = "VICTOIRE 🎉"
                    desc = f"Tu as choisi {EMOJI[player_choice]} **{player_choice.capitalize()}**.\nLe bot a choisi {EMOJI[bot_choice]} **{bot_choice.capitalize()}**.\n\nTu gagnes !"
                    color = 0x57F287
                else:
                    title = "DÉFAITE 😵"
                    desc = f"Tu as choisi {EMOJI[player_choice]} **{player_choice.capitalize()}**.\nLe bot a choisi {EMOJI[bot_choice]} **{bot_choice.capitalize()}**.\n\nTu perds."
                    color = 0xED4245

                res_embed = discord.Embed(title=title, description=desc, color=color)
                res_embed.set_footer(text=f"{author.display_name} vs Bot")
                for c in view.children:
                    c.disabled = True
                try:
                    await inter.response.edit_message(embed=res_embed, view=view)
                except Exception:
                    await safe_send(channel, embed=res_embed)

            class _TmpButtonP(discord.ui.Button):
                def __init__(self, choice_key: str):
                    super().__init__(style=discord.ButtonStyle.primary, label=f"{EMOJI[choice_key]} {choice_key.capitalize()}", custom_id=f"solo_p:{author.id}:{choice_key}")
                    self.choice_key = choice_key
                async def callback(self, inter: discord.Interaction):
                    if inter.user.id != author.id:
                        await inter.response.send_message("❌ Ce duel est réservé à l'auteur.", ephemeral=True)
                        return
                    await make_choice_prefix(inter, self.choice_key)

            view.add_item(_TmpButtonP("quincy"))
            view.add_item(_TmpButtonP("hollow"))
            view.add_item(_TmpButtonP("shinigami"))

            await safe_send(channel, embed=embed, view=view)
            return

        # vs joueur (member fourni)
        if member.id == author.id:
            await safe_send(channel, "❌ Tu ne peux pas te défier toi-même.")
            return

        embed = discord.Embed(
            title="⚔️ Défi Quincy / Hollow / Shinigami",
            description=f"<@{author.id}> a défié <@{member.id}> !\n<@{member.id}>, acceptez-vous ?",
            color=0xFFA500
        )
        embed.set_footer(text="Le défi expirera dans 60s.")
        view = ChallengeView(self.bot, author.id, member.id, channel=channel)
        await safe_send(channel, embed=embed, view=view)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = QuincyHollowShinigami(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Bleach"
    await bot.add_cog(cog)
