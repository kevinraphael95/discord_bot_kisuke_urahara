# ────────────────────────────────────────────────────────────────────────────────
# 📌 game_view.py — Classe de base pour créer des jeux interactifs solo/multi
# Objectif : Fournir une vue universelle avec embed, tentatives, timer et gestion solo/multi
# Catégorie : Jeux
# Accès : Tous
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import discord, asyncio
from utils.discord_utils import safe_send, safe_edit  # ✅ Utilitaires sécurisés

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ Vue principale universelle
# ────────────────────────────────────────────────────────────────────────────────
class GameView:
    """
    Classe de base pour un jeu interactif Discord.
    - Supporte Solo/Multi
    - Gestion des tentatives
    - Embed dynamique
    - Timer automatique
    """
    DEFAULT_TIMEOUT = 120  # Temps par défaut en secondes

    def __init__(self, author_id: int | None = None, multi: bool = False, channel: discord.TextChannel | None = None, timeout: int | None = None):
        self.author_id = author_id
        self.multi = multi
        self.channel = channel
        self.message: discord.Message | None = None
        self.finished: bool = False
        self.start_time: float = asyncio.get_event_loop().time()
        self.attempts: list[dict] = []  # {'user': str, 'value': any}
        self.timeout: int = timeout or self.DEFAULT_TIMEOUT

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Gestion des joueurs
    # ────────────────────────────────────────────────────────────────────────────
    def can_play(self, user_id: int) -> bool:
        """Vérifie si l'utilisateur peut jouer (solo/multi)."""
        if self.multi:
            return True
        return self.author_id is None or user_id == self.author_id

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Historique des tentatives
    # ────────────────────────────────────────────────────────────────────────────
    def add_attempt(self, user: discord.User | str, value) -> None:
        """Ajoute un essai à l'historique."""
        self.attempts.append({"user": str(user), "value": value})

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Embed de base (à surcharger)
    # ────────────────────────────────────────────────────────────────────────────
    def build_embed(self) -> discord.Embed:
        """Construit un embed de base — à surcharger pour chaque jeu."""
        mode_text = "Multi 🌍" if self.multi else "Solo 🧍‍♂️"
        embed = discord.Embed(
            title=f"🎮 Jeu - {mode_text}",
            description="Base GameView, pensez à surcharger build_embed",
            color=discord.Color.orange()
        )
        if self.attempts:
            lines = [f"{a['user']}: {a['value']}" for a in self.attempts]
            embed.add_field(name=f"Essais ({len(self.attempts)})", value="\n".join(lines), inline=False)
        return embed

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Gestion du timer
    # ────────────────────────────────────────────────────────────────────────────
    async def start_timer(self, remove_callback=None):
        """Démarre le timer et termine la partie si le temps est écoulé."""
        await asyncio.sleep(self.timeout)
        if not self.finished:
            self.finished = True
            if self.message:
                await safe_edit(self.message, embed=self.build_embed())
            if remove_callback:
                remove_callback()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Envoi / mise à jour du message principal
    # ────────────────────────────────────────────────────────────────────────────
    async def send_message(self, content: str | None = None, embed: discord.Embed | None = None):
        """Envoie ou met à jour le message principal du jeu."""
        if self.message:
            await safe_edit(self.message, content=content, embed=embed)
        else:
            self.message = await safe_send(self.channel, content=content, embed=embed)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Traitement d'un essai (à surcharger)
    # ────────────────────────────────────────────────────────────────────────────
    async def process_guess(self, user: discord.User, guess) -> tuple[bool, str]:
        """
        Traite une tentative de l'utilisateur.
        Retourne un tuple (success: bool, message: str)
        """
        if self.finished:
            return False, "⚠️ La partie est terminée."
        if not self.can_play(user.id):
            return False, "❌ Vous ne pouvez pas jouer en solo."
        self.add_attempt(user, guess)
        return True, f"{user} a joué `{guess}`"
