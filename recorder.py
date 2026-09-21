"""
Recorder 🎬
Utilise streamlink + ffmpeg pour capturer un live de A à Z.
Lance en subprocess, bloque jusqu'à la fin du live.
Supporte /stop pour couper proprement et déclencher l'upload.
"""
import logging
import asyncio
from datetime import datetime
from pathlib import Path
from config import RECORDINGS_DIR, STREAMLINK_QUALITY

log = logging.getLogger(__name__)

# Registry des process actifs : key → asyncio.subprocess.Process
# key = "platform:username"
_active_procs: dict[str, asyncio.subprocess.Process] = {}


def _make_output_path(platform: str, username: str) -> Path:
    """Génère un chemin de fichier propre avec timestamp."""
    out_dir = Path(RECORDINGS_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return out_dir / f"{platform}_{username}_{ts}.mp4"


def get_active() -> dict[str, asyncio.subprocess.Process]:
    """Retourne les recordings en cours."""
    return dict(_active_procs)


async def stop_recording(key: str) -> bool:
    """
    Coupe proprement un recording en cours.
    Attend jusqu'à 5s que le process soit enregistré (race condition fix).
    Returns True si un process a été killé.
    """
    # Attend max 5s que le process apparaisse (peut être en train de démarrer)
    for _ in range(10):
        if key in _active_procs:
            break
        await asyncio.sleep(0.5)

    proc = _active_procs.get(key)
    if proc is None:
        return False

    log.info(f"[Recorder] 🛑 Stop manuel : {key}")
    try:
        proc.terminate()  # SIGTERM → streamlink flush le fichier proprement
        await asyncio.sleep(2)
        if proc.returncode is None:
            proc.kill()
    except Exception as e:
        log.warning(f"[Recorder] Erreur stop : {e}")
    return True


async def record_stream(
    stream_url: str,
    platform: str,
    username: str,
    on_complete: callable,
) -> None:
    """
    Lance streamlink pour recorder le live complet.
    Appelle on_complete(filepath) quand le live se termine (naturellement ou via /stop).
    """
    key         = f"{platform}:{username}"
    output_path = _make_output_path(platform, username)
    raw_path = output_path.with_suffix(".ts")
    log.info(f"[Recorder] 🔴 Début recording {platform}/@{username} -> {raw_path}")

    cmd = [
        "streamlink",
        "--retry-streams", "10",
        "--retry-max",    "999",
        "--retry-open",   "10",
        "--hls-live-restart",
        "--output", str(raw_path),
        stream_url,
        STREAMLINK_QUALITY,
    ]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _active_procs[key] = proc

        async def _drain_stderr():
            async for line in proc.stderr:
                decoded = line.decode("utf-8", errors="replace").strip()
                if decoded:
                    log.debug(f"[streamlink] {decoded}")

        await asyncio.gather(proc.wait(), _drain_stderr())

    except Exception as e:
        log.error(f"[Recorder] Erreur recording : {e}")
    finally:
        _active_procs.pop(key, None)

    if raw_path.exists() and raw_path.stat().st_size > 0:
        log.info(f"[Recorder] 🔧 Remuxing en MP4 propre pour VLC/Telegram...")
        # Remux propre pour corriger l'entête MP4 et le codec
        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-i", str(raw_path),
            "-c", "copy",
            "-movflags", "faststart",
            str(output_path)
        ]
        remux_proc = await asyncio.create_subprocess_exec(
            *ffmpeg_cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        await remux_proc.wait()
        
        if output_path.exists() and output_path.stat().st_size > 1024:
            # Remux a réussi et le fichier n'est pas vide (>1KB)
            try:
                raw_path.unlink()
            except:
                pass
            size_mb = output_path.stat().st_size / 1024 / 1024
            log.info(f"[Recorder] ✅ Recording terminé & propre : {output_path} ({size_mb:.1f}MB)")
            await on_complete(str(output_path))
        else:
            # Remux a échoué (souvent à cause d'un flux corrompu) - on envoie le raw
            log.warning(f"[Recorder] ⚠️ Echec du remuxing ffmpeg, fallback sur le fichier brut")
            if output_path.exists():
                try:
                    output_path.unlink()
                except:
                    pass
            size_mb = raw_path.stat().st_size / 1024 / 1024
            log.info(f"[Recorder] ✅ Recording terminé (BRUT) : {raw_path} ({size_mb:.1f}MB)")
            await on_complete(str(raw_path))
    else:
        log.warning(f"[Recorder] 👻 Fichier vide ou absent : {raw_path}")
