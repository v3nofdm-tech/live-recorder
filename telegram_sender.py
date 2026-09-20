"""
Telegram Sender 📤
Envoie les vidéos sur le canal.
Gère les fichiers < 50MB (send_video) et > 50MB (split ou lien).
"""
import logging
import os
import asyncio
from pathlib import Path
import httpx
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL

log = logging.getLogger(__name__)

BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
MAX_DIRECT_BYTES = 49 * 1024 * 1024  # 49MB pour rester safe


async def send_notification(text: str) -> None:
    """Envoie un message texte simple sur le canal."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(f"{BASE_URL}/sendMessage", json={
            "chat_id": TELEGRAM_CHANNEL,
            "text": text,
            "parse_mode": "HTML",
        })
        if resp.status_code != 200:
            log.error(f"[Telegram] sendMessage fail: {resp.text}")
        else:
            log.info(f"[Telegram] ✉️ Notif envoyée : {text[:60]}")


async def send_video(filepath: str, caption: str) -> None:
    """
    Envoie la vidéo sur le canal Telegram.
    Si > 49MB : split le fichier avec ffmpeg avant d'envoyer.
    """
    path = Path(filepath)
    size = path.stat().st_size
    size_mb = size / 1024 / 1024

    log.info(f"[Telegram] 📤 Envoi de {path.name} ({size_mb:.1f}MB)")

    if size <= MAX_DIRECT_BYTES:
        await _upload_single(filepath, caption)
    else:
        log.info(f"[Telegram] Fichier trop gros ({size_mb:.1f}MB) — split en chunks de 45MB")
        parts = await _split_video(filepath)
        for i, part in enumerate(parts, 1):
            part_caption = f"{caption}\n📦 Partie {i}/{len(parts)}"
            await _upload_single(part, part_caption)
            # Nettoyage après envoi
            try:
                os.remove(part)
            except Exception:
                pass

    # Nettoyage du fichier original
    try:
        os.remove(filepath)
        log.info(f"[Telegram] 🗑️ Fichier local supprimé : {filepath}")
    except Exception as e:
        log.warning(f"[Telegram] Impossible de supprimer {filepath}: {e}")


async def _upload_single(filepath: str, caption: str) -> None:
    """Upload d'un seul fichier vidéo."""
    async with httpx.AsyncClient(timeout=600) as client:  # 10min timeout pour gros fichiers
        with open(filepath, "rb") as f:
            resp = await client.post(
                f"{BASE_URL}/sendVideo",
                data={
                    "chat_id": TELEGRAM_CHANNEL,
                    "caption": caption,
                    "supports_streaming": "true",
                },
                files={"video": (Path(filepath).name, f, "video/mp4")},
            )
        if resp.status_code != 200:
            log.error(f"[Telegram] sendVideo fail: {resp.text}")
        else:
            log.info(f"[Telegram] ✅ Vidéo envoyée avec succès !")


async def _split_video(filepath: str) -> list[str]:
    """
    Split le fichier MP4 en chunks de ~45MB avec ffmpeg (re-encode minimal).
    """
    path = Path(filepath)
    size_mb = path.stat().st_size / 1024 / 1024
    # Durée estimée pour un chunk de 45MB
    # On split par taille de segment de ~45MB
    chunk_size_mb = 45
    n_parts = int(size_mb / chunk_size_mb) + 1
    
    # D'abord on récupère la durée totale
    probe_cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", str(filepath)
    ]
    proc = await asyncio.create_subprocess_exec(
        *probe_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()

    import json
    info = json.loads(stdout)
    total_duration = float(info["format"]["duration"])
    segment_duration = total_duration / n_parts

    parts = []
    for i in range(n_parts):
        start = i * segment_duration
        out = str(path.parent / f"{path.stem}_part{i+1}.mp4")
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start),
            "-i", str(filepath),
            "-t", str(segment_duration),
            "-c", "copy",  # pas de re-encode, rapide
            out
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()
        if Path(out).exists():
            parts.append(out)

    return parts


async def resolve_channel_id() -> None:
    """Vérifie que le bot peut poster sur le canal (diagnostic au démarrage)."""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{BASE_URL}/getMe")
        if resp.status_code == 200:
            me = resp.json()["result"]
            log.info(f"[Telegram] ✅ Bot connecté : @{me['username']}")
        else:
            log.error(f"[Telegram] ❌ Token invalide : {resp.text}")
