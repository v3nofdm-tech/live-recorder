"""
🔴 LIVE RECORDER — Main Orchestrator v2
- TikTok : WebSocket instantané (0ms latence)
- Instagram : polling 10s (max 10s perdues — meilleur possible sans WS)
- Commandes bot : /addtt /addig /rmtt /rmig /list
- Targets dynamiques : hot-add sans redeploy
"""
import asyncio
import logging
import signal
import sys
from datetime import datetime

from config import INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD, INSTA_POLL_INTERVAL
from monitors import tiktok as tiktok_monitor
from monitors import instagram as insta_monitor
from recorder import record_stream
from telegram_sender import send_video, send_notification, resolve_channel_id
import targets_store
import bot_commands

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

# ─── STATE ─────────────────────────────────────────────────────────────────────
_recording_active: set[str] = set()


async def on_recording_complete(filepath: str, label: str) -> None:
    ts = datetime.now().strftime("%d/%m/%Y %H:%M")
    caption = (
        f"🎬 <b>Live enregistré !</b>\n"
        f"👤 {label}\n"
        f"🕐 {ts}\n"
        f"✅ Recording complet de A à Z"
    )
    await send_notification(f"📤 Envoi du recording en cours : {label}")
    await send_video(filepath, caption)


# ─── TIKTOK — WebSocket instantané ────────────────────────────────────────────

async def monitor_tiktok(target: dict) -> None:
    username = target["username"]
    label    = target["label"]
    key      = f"tiktok:{username}"

    log.info(f"[TikTok] 👁️ WebSocket en attente pour {label}")

    async def on_live_start(stream_url: str):
        if key in _recording_active:
            return
        _recording_active.add(key)
        await send_notification(
            f"🔴 <b>LIVE DÉTECTÉ !</b>\n"
            f"👤 {label}\n"
            f"🎬 Recording lancé instantanément..."
        )
        await record_stream(
            stream_url=stream_url,
            platform="tiktok",
            username=username,
            on_complete=lambda fp: on_recording_complete(fp, label),
        )
        _recording_active.discard(key)

    await tiktok_monitor.watch_and_notify(username, on_live_start)


# ─── INSTAGRAM — Polling 10s (meilleur possible sans WebSocket public) ─────────

async def monitor_instagram(target: dict) -> None:
    username = target["username"]
    label    = target["label"]
    key      = f"instagram:{username}"

    log.info(f"[Instagram] 👁️ Polling 10s démarré pour {label}")

    while True:
        try:
            if key not in _recording_active:
                is_live, stream_url = insta_monitor.is_live(
                    username, INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD
                )
                if is_live and stream_url:
                    log.info(f"[Instagram] 🔴 LIVE DÉTECTÉ : {label}")
                    _recording_active.add(key)
                    await send_notification(
                        f"🔴 <b>LIVE DÉTECTÉ !</b>\n"
                        f"👤 {label}\n"
                        f"🎬 Recording lancé..."
                    )
                    await record_stream(
                        stream_url=stream_url,
                        platform="instagram",
                        username=username,
                        on_complete=lambda fp: on_recording_complete(fp, label),
                    )
                    _recording_active.discard(key)
                else:
                    log.debug(f"[Instagram] 💤 {label} — pas en live")
        except Exception as e:
            log.error(f"[Instagram] ❌ Erreur {label}: {e}", exc_info=True)
            _recording_active.discard(key)

        await asyncio.sleep(INSTA_POLL_INTERVAL)


# ─── DISPATCHER ───────────────────────────────────────────────────────────────

async def start_monitor(target: dict) -> None:
    """Lance la surveillance pour un target selon sa plateforme."""
    if target["platform"] == "tiktok":
        asyncio.create_task(monitor_tiktok(target))
    elif target["platform"] == "instagram":
        asyncio.create_task(monitor_instagram(target))


# ─── MAIN ─────────────────────────────────────────────────────────────────────

async def main() -> None:
    log.info("=" * 60)
    log.info("🔴 LIVE RECORDER v2.0 — Starting up...")
    log.info("=" * 60)

    # Vérification bot Telegram
    await resolve_channel_id()

    # Charge les targets (config.py + targets.json si existant)
    targets_store.init()

    # Quand un target est ajouté via /addtt ou /addig → lance la surveillance direct
    targets_store.on_target_added(start_monitor)

    # Lance la surveillance pour tous les targets initiaux
    targets = targets_store.get_all()
    log.info(f"[Main] 👁️ Surveillance de {len(targets)} target(s)")
    for t in targets:
        log.info(f"       • {t['label']}")
        await start_monitor(t)

    # Lance le listener de commandes Telegram en parallèle
    asyncio.create_task(bot_commands.poll_commands())

    # Boucle infinie — les tasks tournent en background
    await asyncio.Event().wait()


def handle_shutdown(sig, frame):
    log.info("[Main] 🛑 Shutdown — arrêt propre")
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)
    asyncio.run(main())
