"""
Instagram Live Monitor 📸
Utilise instagrapi pour détecter un live en cours.
Nécessite un compte Instagram connecté (creds dans .env).
"""
import logging
from instagrapi import Client as InstaClient

log = logging.getLogger(__name__)

_client: InstaClient | None = None


def get_client(username: str, password: str) -> InstaClient:
    """Singleton client Instagram — login une fois, réutilise la session."""
    global _client
    if _client is None:
        _client = InstaClient()
        try:
            _client.load_settings("insta_session.json")
            _client.login(username, password)
            _client.dump_settings("insta_session.json")
            log.info("[Instagram] Login OK")
        except Exception as e:
            log.error(f"[Instagram] Login fail: {e}")
            _client = None
    return _client


def is_live(username: str, ig_user: str, ig_pass: str) -> tuple[bool, str | None]:
    """
    Vérifie si username est en live Instagram.
    Returns (is_live: bool, stream_url: str | None)
    """
    if not ig_user or not ig_pass:
        log.warning("[Instagram] Pas de creds — skip check Instagram")
        return False, None

    try:
        cl = get_client(ig_user, ig_pass)
        if cl is None:
            return False, None

        user_id = cl.user_id_from_username(username)
        user_info = cl.user_info(user_id)

        if user_info.live_broadcasting:
            # Récupère le broadcast en cours
            broadcasts = cl.user_broadcasts(user_id)
            if broadcasts:
                broadcast = broadcasts[0]
                stream_url = broadcast.dash_playback_url or broadcast.stream_url
                log.info(f"[Instagram] 🔴 @{username} est EN LIVE ! URL: {stream_url}")
                return True, stream_url

    except Exception as e:
        log.warning(f"[Instagram] Erreur check live @{username}: {e}")

    return False, None
