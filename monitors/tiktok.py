"""
TikTok Live Monitor 🎵
Utilise TikTokLive pour détecter si un user est en live,
puis streamlink pour recorder en qualité max.
"""
import asyncio
import logging
from TikTokLive import TikTokLiveClient
from TikTokLive.events import ConnectEvent, DisconnectEvent, LiveEndEvent

log = logging.getLogger(__name__)


async def is_live(username: str) -> bool:
    """Check rapide si le user tiktok est en live."""
    try:
        client = TikTokLiveClient(unique_id=f"@{username}")
        return await client.is_live()
    except Exception as e:
        log.warning(f"[TikTok] Erreur check live pour @{username}: {e}")
        return False


def get_stream_url(username: str) -> str:
    """Retourne l'URL streamlink-compatible pour un live TikTok."""
    return f"https://www.tiktok.com/@{username}/live"
