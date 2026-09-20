"""
🔴 LIVE RECORDER — Main Orchestrator
Surveille TikTok + Instagram 24/7, record les lives, envoie sur Telegram.
"""
import asyncio
import logging
import signal
import sys
from datetime import datetime

from config import TARGETS, POLL_INTERVAL_SEC, INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD
from monitors import tiktok as tiktok_monitor
from monitors import instagram as insta_monitor
from recorder import record_stream
from telegram_sender import send_video, send_notification, resolve_channel_id

# ─── LOGGING ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("live_recorder.log", encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)

# ─── STATE — quels targets sont actuellement en cours de recording ─────────────
_recording_active: set[str] = set()  # "{platform}:{username}"


async def on_recording_complete(filepath: str, label: str) -> None:
    """Callback appelé quand un recording se termine — envoie sur Telegram."""
    ts = datetime.now().strftime("%d/%m/%Y %H:%M")
    caption = (
        f"🎬 <b>Live enregistré !</b>\n"
        f"👤 {label}\n"
        f"🕐 {ts}\n"
        f"✅ Recording complet de A à Z"
    )
    await send_notification(f"📤 Envoi du recording en cours : {label}")
    await send_video(filepath, caption)


async def monitor_target(target: dict) -> None:
    """
    Boucle de surveillance pour un target.
    TikTok → WebSocket instantané.
    Instagram → polling 60s (API pas de websocket dispo).
    """
    platform = target["platform"]
    username = target["username"]
    label    = target["label"]
    key      = f"{platform}:{username}"

    log.info(f"[Monitor] 🚀 Surveillance démarrée pour {label}")

    if platform == "tiktok":
        # ── WebSocket — zéro latence ───────────────────────────────────────
        async def on_live_start(stream_url: str):
            if key in _recording_active:
                log.warning(f"[Monitor] Already recording {label}, skip")
                return
            _recording_active.add(key)
            await send_notification(
                f"🔴 <b>LIVE DÉTECTÉ !</b>\n"
                f"👤 {label}\n"
                f"🎬 Recording lancé instantanément..."
            )
            await record_stream(
                stream_url=stream_url,
                platform=platform,
                username=username,
                on_complete=lambda fp: on_recording_complete(fp, label),
            )
            _recording_active.discard(key)

        await tiktok_monitor.watch_and_notify(username, on_live_start)

    elif platform == "instagram":
        # ── Polling 60s (pas de websocket public pour insta) ──────────────
        while True:
            try:
                if key not in _recording_active:
                    is_live, stream_url = insta_monitor.is_live(
                        username, INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD
                    )
                    if is_live and stream_url:
                        log.info(f"[Monitor] 🔴 LIVE DÉTECTÉ : {label}")
                        _recording_active.add(key)
                        await send_notification(
                            f"🔴 <b>LIVE DÉTECTÉ !</b>\n"
                            f"👤 {label}\n"
                            f"🎬 Recording lancé..."
                        )
                        await record_stream(
                            stream_url=stream_url,
                            platform=platform,
                            username=username,
                            on_complete=lambda fp: on_recording_complete(fp, label),
                        )
                        _recording_active.discard(key)
                    else:
                        log.debug(f"[Monitor] 💤 {label} — pas en live")
            except Exception as e:
                log.error(f"[Monitor] ❌ Erreur pour {label}: {e}", exc_info=True)
                _recording_active.discard(key)

            await asyncio.sleep(POLL_INTERVAL_SEC)


async def main() -> None:
    log.info("=" * 60)
    log.info("🔴 LIVE RECORDER v1.0 — Starting up...")
    log.info("=" * 60)

    # Vérification bot Telegram
    await resolve_channel_id()

    # Lance toutes les surveillances en parallèle
    tasks = [monitor_target(target) for target in TARGETS]

    log.info(f"[Main] 👁️ Surveillance de {len(TARGETS)} target(s)")
    for t in TARGETS:
        log.info(f"       • {t['label']}")

    await asyncio.gather(*tasks)


def handle_shutdown(sig, frame):
    log.info("[Main] 🛑 Shutdown reçu — arrêt propre")
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)
    asyncio.run(main())
