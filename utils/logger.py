# ────────────────────────────────────────────────────────────────────────────────
# 📌 logger.py
# Objectif : Capturer les print() du bot et les exposer au panel admin
# ────────────────────────────────────────────────────────────────────────────────

import sys
from collections import deque
from datetime import datetime

# Buffer circulaire : garde les 500 dernières lignes de log
LOG_BUFFER = deque(maxlen=500)


class LogCapture:
    """Intercepte stdout pour capturer tous les print()."""

    def __init__(self, original):
        self.original = original

    def write(self, message):
        if message.strip():
            timestamp = datetime.now().strftime("%H:%M:%S")
            entry = f"[{timestamp}] {message.rstrip()}"
            LOG_BUFFER.append(entry)
        self.original.write(message)

    def flush(self):
        self.original.flush()


def init_logger():
    """Remplace sys.stdout par le LogCapture."""
    sys.stdout = LogCapture(sys.stdout)


def get_logs(n=200):
    """Retourne les n dernières lignes de log."""
    return list(LOG_BUFFER)[-n:]
