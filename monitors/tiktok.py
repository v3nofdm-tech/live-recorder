"""
TikTok Live Monitor 🎵
Utilise TikTokLive v7 pour détecter si un user est en live,
puis streamlink pour recorder en qualité max.
"""
import asyncio
import logging
from TikTokLive import TikTokLiveClient
from TikTokLive.client.web.web_settings import WebDefaults

log = logging.getLogger(__name__)


async def is_live(username: str) -> bool:
    """Check rapide si le user tiktok est en live (API v7)."""
    try:
        client = TikTokLiveClient(unique_id=username)
        # v7: fetch_room_id_on_connect vérifie le statut live
        result = await client.is_live()
        return result
    except Exception as e:
        log.warning(f"[TikTok] Erreur check live pour @{username}: {e}")
        return False


def get_stream_url(username: str) -> str:
    """Retourne l'URL streamlink-compatible pour un live TikTok."""
    return f"https://www.tiktok.com/@{username}/live"
