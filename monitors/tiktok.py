"""
TikTok Live Monitor 🎵 — WebSocket mode
Au lieu de poller toutes les 60s, on se connecte en mode "waiting"
et TikTok notifie instantanément quand le live démarre.
Zéro latence, zéro secondes perdues.
"""
import asyncio
import logging
from TikTokLive import TikTokLiveClient
from TikTokLive.events import ConnectEvent, DisconnectEvent

log = logging.getLogger(__name__)


async def watch_and_notify(username: str, on_live_start: callable) -> None:
    """
    Se connecte en mode persistant au compte TikTok.
    Dès que le live démarre → appelle on_live_start(stream_url) instantanément.
    Si le live n'est pas actif, TikTokLive attend en background et notifie au démarrage.
    Boucle infinie — se reconnecte automatiquement après chaque live.
    """
    while True:
        client = TikTokLiveClient(unique_id=username)

        @client.on(ConnectEvent)
        async def on_connect(event: ConnectEvent):
            stream_url = get_stream_url(username)
            log.info(f"[TikTok] 🔴 LIVE DÉTECTÉ EN TEMPS RÉEL : @{username}")
            await on_live_start(stream_url)

        @client.on(DisconnectEvent)
        async def on_disconnect(event: DisconnectEvent):
            log.info(f"[TikTok] 🔕 Live terminé pour @{username} — reconnexion en attente")

        try:
            log.info(f"[TikTok] 👁️ Connexion WebSocket en attente pour @{username}...")
            # fetch_room_id_on_connect=True : attend que le live démarre si pas encore actif
            await client.connect(fetch_room_id_on_connect=True)
        except Exception as e:
            log.warning(f"[TikTok] Reconnexion dans 30s (erreur: {e})")
            await asyncio.sleep(30)


async def is_live(username: str) -> bool:
    """Check one-shot si le user est en live (utilisé au démarrage pour vérif initiale)."""
    try:
        client = TikTokLiveClient(unique_id=username)
        return await client.is_live()
    except Exception as e:
        log.warning(f"[TikTok] Erreur check live pour @{username}: {e}")
        return False


def get_stream_url(username: str) -> str:
    """URL streamlink-compatible pour un live TikTok."""
    return f"https://www.tiktok.com/@{username}/live"
