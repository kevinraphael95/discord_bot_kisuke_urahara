# ================================================================================
# 📌 logger.py
# Objectif : Capturer les print(), stderr et les logs (module logging) du bot
#            pour les exposer au panel admin
# Catégorie : Système
# Accès : Interne
# Cooldown : Aucun
# ================================================================================

# ================================================================================
# 📦 Imports nécessaires
# ================================================================================
import sys
import logging
from collections import deque
from datetime import datetime

# ================================================================================
# 🗂️ Buffer circulaire des logs
# ================================================================================
# Garde les 500 dernières lignes en mémoire
LOG_BUFFER = deque(maxlen=500)


def _add_entry(message: str):
    """Ajoute une entrée horodatée au buffer si le message n'est pas vide."""
    if message and message.strip():
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"[{timestamp}] {message.rstrip()}"
        LOG_BUFFER.append(entry)


# ================================================================================
# 📝 Classe de capture des flux (stdout / stderr)
# ================================================================================
class LogCapture:
    """Intercepte un flux (stdout ou stderr) pour capturer tout ce qui y est écrit."""

    def __init__(self, original):
        self.original = original

    def write(self, message):
        _add_entry(message)
        self.original.write(message)

    def flush(self):
        self.original.flush()

    # Nécessaire pour rester compatible avec du code qui teste ces attributs
    def isatty(self):
        return getattr(self.original, "isatty", lambda: False)()


# ================================================================================
# 📝 Handler pour le module logging (log.exception, log.error, etc.)
# ================================================================================
class BufferLogHandler(logging.Handler):
    """Pousse chaque log émis via le module `logging` dans LOG_BUFFER."""

    def emit(self, record):
        try:
            message = self.format(record)
            _add_entry(message)
        except Exception:
            # Ne jamais planter l'appli à cause du logging lui-même
            pass


# ================================================================================
# 🚀 Initialisation du logger
# ================================================================================
def init_logger():
    """
    - Remplace sys.stdout ET sys.stderr par des LogCapture (capture les print()
      et les tracebacks/erreurs non catchées écrites sur stderr).
    - Attache un handler au root logger pour capturer tout ce qui passe par
      le module `logging` (log.exception, log.error, log.warning, ...),
      utilisé par exemple dans bot.py (on_app_command_error).
    """
    sys.stdout = LogCapture(sys.stdout)
    sys.stderr = LogCapture(sys.stderr)

    handler = BufferLogHandler()
    handler.setFormatter(logging.Formatter("%(levelname)s [%(name)s] %(message)s"))
    handler.setLevel(logging.INFO)

    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)


# ================================================================================
# 📤 Récupération des logs
# ================================================================================
def get_logs(n=200):
    """Retourne les n dernières lignes de log."""
    return list(LOG_BUFFER)[-n:]
