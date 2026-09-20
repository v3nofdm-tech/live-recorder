"""
Targets Store 💾
Gère la liste dynamique des comptes à surveiller.
Persisté dans targets.json — survit aux restarts, pas aux redeploys.
"""
import json
import logging
import asyncio
from pathlib import Path
from config import TARGETS as DEFAULT_TARGETS

log = logging.getLogger(__name__)

STORE_PATH = Path("/tmp/targets.json")
_targets: list[dict] = []
_lock = asyncio.Lock()
# callbacks appelés quand un nouveau target est ajouté
_on_add_callbacks: list[callable] = []


def _load() -> list[dict]:
    """Charge depuis le JSON, fallback sur config.py si absent."""
    if STORE_PATH.exists():
        try:
            data = json.loads(STORE_PATH.read_text())
            log.info(f"[Store] {len(data)} target(s) chargés depuis {STORE_PATH}")
            return data
        except Exception as e:
            log.warning(f"[Store] Erreur lecture JSON: {e} — fallback config.py")
    return list(DEFAULT_TARGETS)


def _save() -> None:
    try:
        STORE_PATH.write_text(json.dumps(_targets, indent=2))
    except Exception as e:
        log.error(f"[Store] Erreur sauvegarde: {e}")


def init() -> list[dict]:
    """Charge les targets au démarrage."""
    global _targets
    _targets = _load()
    return _targets


def get_all() -> list[dict]:
    return list(_targets)


async def add_target(platform: str, username: str) -> tuple[bool, str]:
    """
    Ajoute un target dynamiquement.
    Returns (success, message)
    """
    async with _lock:
        # Vérif doublon
        for t in _targets:
            if t["platform"] == platform and t["username"].lower() == username.lower():
                return False, f"@{username} ({platform}) est déjà surveillé !"

        emoji = "🎵" if platform == "tiktok" else "📸"
        label = f"{emoji} {username} ({platform.capitalize()})"
        new_target = {
            "platform": platform,
            "username": username,
            "label": label,
        }
        _targets.append(new_target)
        _save()
        log.info(f"[Store] ✅ Nouveau target ajouté : {label}")

        # Notifie les callbacks (pour lancer la surveillance immédiatement)
        for cb in _on_add_callbacks:
            asyncio.create_task(cb(new_target))

        return True, f"✅ Surveillance lancée pour {label}"


async def remove_target(platform: str, username: str) -> tuple[bool, str]:
    """Retire un target."""
    async with _lock:
        before = len(_targets)
        _targets[:] = [
            t for t in _targets
            if not (t["platform"] == platform and t["username"].lower() == username.lower())
        ]
        if len(_targets) < before:
            _save()
            return True, f"✅ @{username} ({platform}) retiré"
        return False, f"@{username} ({platform}) pas trouvé dans la liste"


def on_target_added(callback: callable) -> None:
    """Enregistre un callback appelé quand un target est ajouté."""
    _on_add_callbacks.append(callback)
