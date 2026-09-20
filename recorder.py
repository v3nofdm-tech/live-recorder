"""
Recorder 🎬
Utilise streamlink + ffmpeg pour capturer un live de A à Z.
Lance en subprocess, bloque jusqu'à la fin du live.
"""
import os
import subprocess
import logging
import asyncio
from datetime import datetime
from pathlib import Path
from config import RECORDINGS_DIR, STREAMLINK_QUALITY

log = logging.getLogger(__name__)


def _make_output_path(platform: str, username: str) -> Path:
    """Génère un chemin de fichier propre avec timestamp."""
    out_dir = Path(RECORDINGS_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{platform}_{username}_{ts}.mp4"
    return out_dir / filename


async def record_stream(
    stream_url: str,
    platform: str,
    username: str,
    on_complete: callable,
) -> None:
    """
    Lance streamlink pour recorder le live complet.
    Appelle on_complete(filepath) quand le live se termine.
    
    Args:
        stream_url: URL du live (tiktok page URL ou instagram dash URL)
        platform: "tiktok" ou "instagram"
        username: nom du user (pour le nom de fichier)
        on_complete: callback async appelé avec le path du fichier fini
    """
    output_path = _make_output_path(platform, username)
    log.info(f"[Recorder] 🎬 Début recording {platform}/@{username} → {output_path}")

    cmd = [
        "streamlink",
        "--retry-streams", "10",          # retry si stream coupe brièvement
        "--retry-max", "999",              # on insiste, c'est un live
        "--retry-open", "10",
        "--hls-live-restart",              # reprend si HLS restart
        "--output", str(output_path),
        stream_url,
        STREAMLINK_QUALITY,
    ]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        # Lit stderr en live pour les logs
        async def _drain_stderr():
            async for line in proc.stderr:
                decoded = line.decode("utf-8", errors="replace").strip()
                if decoded:
                    log.debug(f"[streamlink] {decoded}")

        await asyncio.gather(proc.wait(), _drain_stderr())

        if output_path.exists() and output_path.stat().st_size > 0:
            log.info(f"[Recorder] ✅ Recording terminé : {output_path} ({output_path.stat().st_size // 1024 // 1024}MB)")
            await on_complete(str(output_path))
        else:
            log.warning(f"[Recorder] ⚠️ Fichier vide ou absent après recording : {output_path}")

    except Exception as e:
        log.error(f"[Recorder] Erreur recording : {e}")
