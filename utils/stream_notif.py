# ================================================================================
# 📌 stream_notif.py — Code partagé des notifications Twitch / YouTube
# Objectif : Base de données + client API utilisés à la fois par la task
#            (tasks/stream_alert.py) et les commandes (commands/notif.py)
# Catégorie : 🧠 Utils
# Accès : Interne
# Cooldown : /
# ================================================================================
# 🗄️ Table notif_follows (database/reiatsu.db) :
#   id, guild_id, platform ('twitch'|'youtube'), handle, display, channel_id,
#   role_id, last_id, last_published, fail_count
# ================================================================================

# ================================================================================
# 📦 Imports nécessaires
# ================================================================================
import os
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from urllib.parse import urlparse

import aiohttp

from utils.init_db import get_conn

# ================================================================================
# ⚙️ Paramètres globaux
# ================================================================================
TWITCH_INTERVAL = 60        # secondes entre deux vérifs Twitch
YOUTUBE_INTERVAL = 300      # secondes entre deux vérifs YouTube (RSS, pas de quota)

MAX_FOLLOWS_PER_GUILD = 25  # garde-fou par serveur
YT_MAX_AGE_HOURS = 48       # on n'annonce pas une vidéo plus vieille que ça
YT_MAX_BURST = 3            # max de vidéos annoncées d'un coup pour une chaîne
MAX_FAILS = 20              # échecs d'envoi consécutifs (Forbidden) avant suppression

TOKEN_URL = "https://id.twitch.tv/oauth2/token"
STREAMS_URL = "https://api.twitch.tv/helix/streams"
USERS_URL = "https://api.twitch.tv/helix/users"
YT_FEED_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={}"

TWITCH_PURPLE = 0x9146FF
YOUTUBE_RED = 0xFF0000

# Cookies de consentement : évite la page "avant d'accéder à YouTube" (UE)
YT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    "Cookie": "CONSENT=YES+1; SOCS=CAI",
}
ATOM_NS = {
    "a": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
    "media": "http://search.yahoo.com/mrss/",
}

UC_RE = re.compile(r"UC[\w-]{22}")
TWITCH_LOGIN_RE = re.compile(r"^\w{1,25}$")


# ================================================================================
# 🗄️ Helpers base de données
# ================================================================================
def query(sql: str, args: tuple = ()) -> list[dict]:
    """Exécute une requête et renvoie les lignes sous forme de dicts."""
    conn = get_conn()
    try:
        cur = conn.execute(sql, args)
        rows = []
        if cur.description:
            cols = [c[0] for c in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        conn.commit()
        return rows
    finally:
        conn.close()


def init_table():
    """Crée la table (et migre les anciennes versions). Peut être appelée plusieurs fois."""
    query(
        """
        CREATE TABLE IF NOT EXISTS notif_follows (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id       INTEGER NOT NULL,
            platform       TEXT    NOT NULL,
            handle         TEXT    NOT NULL,
            display        TEXT,
            channel_id     INTEGER NOT NULL,
            role_id        INTEGER,
            last_id        TEXT,
            last_published TEXT,
            fail_count     INTEGER NOT NULL DEFAULT 0,
            UNIQUE (guild_id, platform, handle)
        )
        """
    )
    existing = {r["name"] for r in query("PRAGMA table_info(notif_follows)")}
    if "last_published" not in existing:
        query("ALTER TABLE notif_follows ADD COLUMN last_published TEXT")
    if "fail_count" not in existing:
        query("ALTER TABLE notif_follows ADD COLUMN fail_count INTEGER NOT NULL DEFAULT 0")


def all_follows(platform: str) -> list[dict]:
    return query("SELECT * FROM notif_follows WHERE platform = ?", (platform,))


def set_last(follow_id: int, last_id: str, published: datetime | None = None):
    """Mémorise la dernière annonce (et sa date pour YouTube)."""
    if published is not None:
        query(
            "UPDATE notif_follows SET last_id = ?, last_published = ? WHERE id = ?",
            (str(last_id), published.isoformat(), follow_id),
        )
    else:
        query("UPDATE notif_follows SET last_id = ? WHERE id = ?", (str(last_id), follow_id))


def delete_follow(follow_id: int):
    query("DELETE FROM notif_follows WHERE id = ?", (follow_id,))


def parse_dt(value: str | None) -> datetime:
    try:
        dt = datetime.fromisoformat(value)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return datetime.now(timezone.utc)


def parse_dt_or_none(value: str | None) -> datetime | None:
    try:
        dt = datetime.fromisoformat(value)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


# ================================================================================
# 🌐 Client API (Twitch + YouTube)
# ================================================================================
class StreamClient:
    """Gère la session HTTP, le token Twitch et la lecture des flux YouTube."""

    def __init__(self):
        self.session: aiohttp.ClientSession | None = None
        self.client_id = os.getenv("TWITCH_CLIENT_ID")
        self.client_secret = os.getenv("TWITCH_CLIENT_SECRET")
        self._token: str | None = None
        self._token_expires = 0.0

    @property
    def twitch_ok(self) -> bool:
        return bool(self.client_id and self.client_secret)

    async def start(self):
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15))

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

    # ── Twitch ───────────────────────────────────────────────
    async def _get_token(self, force: bool = False) -> str:
        if not force and self._token and time.time() < self._token_expires - 60:
            return self._token

        async with self.session.post(
            TOKEN_URL,
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "client_credentials",
            },
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()

        self._token = data["access_token"]
        self._token_expires = time.time() + data.get("expires_in", 3600)
        return self._token

    async def _twitch_get(self, url: str, params: list[tuple[str, str]]) -> dict:
        for attempt in range(2):
            token = await self._get_token(force=(attempt == 1))
            headers = {"Client-Id": self.client_id, "Authorization": f"Bearer {token}"}
            async with self.session.get(url, params=params, headers=headers) as resp:
                if resp.status == 401 and attempt == 0:
                    continue  # token expiré/révoqué → on en redemande un
                resp.raise_for_status()
                return await resp.json()
        return {}

    async def twitch_lives(self, logins: list[str]) -> dict[str, dict]:
        """Renvoie {login: stream} pour les chaînes en live (100 max par requête)."""
        lives: dict[str, dict] = {}
        for i in range(0, len(logins), 100):
            chunk = logins[i : i + 100]
            params = [("user_login", l) for l in chunk] + [("first", "100")]
            data = await self._twitch_get(STREAMS_URL, params)
            for s in data.get("data", []):
                if s.get("type") == "live":
                    lives[s["user_login"].lower()] = s
        return lives

    async def twitch_user(self, login: str) -> dict | None:
        data = await self._twitch_get(USERS_URL, [("login", login)])
        users = data.get("data", [])
        return users[0] if users else None

    # ── YouTube ──────────────────────────────────────────────
    async def fetch_feed(self, channel_id: str) -> tuple[str, list[dict]]:
        """Renvoie (nom de la chaîne, vidéos de la plus récente à la plus ancienne)."""
        async with self.session.get(YT_FEED_URL.format(channel_id), headers=YT_HEADERS) as resp:
            resp.raise_for_status()
            text = await resp.text()

        root = ET.fromstring(text)
        name = root.findtext("a:title", default="", namespaces=ATOM_NS)
        entries = []
        for en in root.findall("a:entry", ATOM_NS):
            vid = en.findtext("yt:videoId", namespaces=ATOM_NS)
            if not vid:
                continue
            link = en.find("a:link", ATOM_NS)
            thumb = en.find("media:group/media:thumbnail", ATOM_NS)
            entries.append(
                {
                    "id": vid,
                    "title": en.findtext("a:title", default="Sans titre", namespaces=ATOM_NS),
                    "url": link.get("href") if link is not None else f"https://www.youtube.com/watch?v={vid}",
                    "thumb": thumb.get("url") if thumb is not None else f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg",
                    "published": parse_dt(en.findtext("a:published", namespaces=ATOM_NS)),
                }
            )
        return name, entries

    async def resolve_youtube(self, query_str: str) -> tuple[str, str, list[dict]] | None:
        """Accepte un ID (UC...), un lien /channel/UC..., un @handle ou un lien de chaîne.
        Renvoie (channel_id, nom, vidéos) ou None si introuvable."""
        q = query_str.strip()
        cid = None

        m = UC_RE.search(q)
        if m and (q == m.group(0) or "/channel/" in q):
            cid = m.group(0)
        else:
            if q.startswith("http"):
                url = q
            elif q.startswith("@"):
                url = f"https://www.youtube.com/{q}"
            else:
                url = f"https://www.youtube.com/@{q}"

            host = (urlparse(url).hostname or "").lower()
            if not (host == "youtube.com" or host.endswith(".youtube.com")):
                return None

            try:
                async with self.session.get(url, headers=YT_HEADERS) as resp:
                    if resp.status != 200:
                        return None
                    html = await resp.text()
            except aiohttp.ClientError:
                return None

            m = (
                re.search(r'<link rel="canonical" href="https://www\.youtube\.com/channel/(UC[\w-]{22})"', html)
                or re.search(r'"externalId":"(UC[\w-]{22})"', html)
                or re.search(r'"channelId":"(UC[\w-]{22})"', html)
            )
            if not m:
                return None
            cid = m.group(1)

        try:
            name, entries = await self.fetch_feed(cid)
        except (aiohttp.ClientError, ET.ParseError):
            return None
        return cid, name or cid, entries
