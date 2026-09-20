"""
Bot Commands 🤖 — Interface stylée
Écoute les commandes Telegram via long-polling getUpdates.

Commandes :
  /addtt [pseudo]   — ajoute un compte TikTok
  /addig [pseudo]   — ajoute un compte Instagram
  /rmtt  [pseudo]   — retire un compte TikTok
  /rmig  [pseudo]   — retire un compte Instagram
  /list             — liste tous les targets actifs
  /status           — état du bot en temps réel
  /help             — aide
"""
import asyncio
import logging
import httpx
from datetime import datetime, timezone
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL
import targets_store
import recorder as rec_module

log = logging.getLogger(__name__)
BASE = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# Stats globales du bot
_stats = {
    "started_at": datetime.now(timezone.utc),
    "recordings_done": 0,
    "recordings_active": 0,
}

# Référence vers le set _recording_active du main (injecté au démarrage)
_recording_active_ref: set | None = None


def inject_recording_state(recording_active: set) -> None:
    """Injecte la référence du state de recording pour les stats."""
    global _recording_active_ref
    _recording_active_ref = recording_active


def increment_done() -> None:
    _stats["recordings_done"] += 1


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def _uptime() -> str:
    delta = datetime.now(timezone.utc) - _stats["started_at"]
    h, rem = divmod(int(delta.total_seconds()), 3600)
    m, s   = divmod(rem, 60)
    if h > 0:
        return f"{h}h {m}m"
    elif m > 0:
        return f"{m}m {s}s"
    return f"{s}s"


async def _send(chat_id: int | str, text: str, reply_markup: dict | None = None) -> None:
    payload = {
        "chat_id":    chat_id,
        "text":       text,
        "parse_mode": "HTML",
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    async with httpx.AsyncClient(timeout=10) as c:
        await c.post(f"{BASE}/sendMessage", json=payload)


async def _edit(chat_id: int | str, message_id: int, text: str) -> None:
    async with httpx.AsyncClient(timeout=10) as c:
        await c.post(f"{BASE}/editMessageText", json={
            "chat_id":    chat_id,
            "message_id": message_id,
            "text":       text,
            "parse_mode": "HTML",
        })


async def _send_and_get_id(chat_id: int | str, text: str) -> int | None:
    """Envoie un message et retourne son message_id."""
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.post(f"{BASE}/sendMessage", json={
            "chat_id":    chat_id,
            "text":       text,
            "parse_mode": "HTML",
        })
        data = r.json()
        if data.get("ok"):
            return data["result"]["message_id"]
    return None


# ─── HANDLERS ─────────────────────────────────────────────────────────────────

async def _cmd_add(chat_id: int, platform: str, username: str) -> None:
    emoji = "🎵" if platform == "tiktok" else "📸"
    platform_name = "TikTok" if platform == "tiktok" else "Instagram"

    # Message d'attente animé
    mid = await _send_and_get_id(chat_id,
        f"⏳ <b>Ajout en cours...</b>\n"
        f"{emoji} <code>@{username}</code> sur {platform_name}"
    )

    ok, result_msg = await targets_store.add_target(platform, username)

    if ok:
        detection = "WebSocket temps réel ⚡" if platform == "tiktok" else "Polling 10s 🔄"
        text = (
            f"{'✅' if ok else '❌'} <b>Target ajouté !</b>\n"
            f"{'─' * 28}\n"
            f"{emoji}  <b>@{username}</b>\n"
            f"🌐  {platform_name}\n"
            f"📡  Détection : {detection}\n"
            f"🔴  Surveillance active maintenant\n"
            f"{'─' * 28}\n"
            f"<i>Le prochain live sera capturé de A à Z</i>"
        )
    else:
        text = (
            f"⚠️ <b>Déjà en surveillance</b>\n"
            f"{'─' * 28}\n"
            f"{emoji}  <code>@{username}</code> est déjà dans la liste\n\n"
            f"Tape /list pour voir tous les targets actifs"
        )

    if mid:
        await _edit(chat_id, mid, text)
    else:
        await _send(chat_id, text)


async def _cmd_remove(chat_id: int, platform: str, username: str) -> None:
    emoji = "🎵" if platform == "tiktok" else "📸"
    platform_name = "TikTok" if platform == "tiktok" else "Instagram"

    ok, _ = await targets_store.remove_target(platform, username)

    if ok:
        text = (
            f"🗑️ <b>Target retiré</b>\n"
            f"{'─' * 28}\n"
            f"{emoji}  <code>@{username}</code>\n"
            f"🌐  {platform_name}\n"
            f"⏹️  Surveillance stoppée"
        )
    else:
        text = (
            f"❌ <b>Introuvable</b>\n"
            f"{'─' * 28}\n"
            f"{emoji}  <code>@{username}</code> n'est pas dans la liste\n\n"
            f"Tape /list pour voir les targets actifs"
        )
    await _send(chat_id, text)


async def _cmd_list(chat_id: int) -> None:
    targets = targets_store.get_all()

    if not targets:
        await _send(chat_id,
            "📋 <b>Aucun target en surveillance</b>\n\n"
            "Utilise /addtt ou /addig pour en ajouter"
        )
        return

    active_keys = _recording_active_ref or set()
    tiktok_targets  = [t for t in targets if t["platform"] == "tiktok"]
    insta_targets   = [t for t in targets if t["platform"] == "instagram"]

    lines = [f"📋 <b>Targets actifs</b> ({len(targets)} total)\n"]

    if tiktok_targets:
        lines.append("🎵 <b>TikTok</b> — <i>WebSocket ⚡</i>")
        for t in tiktok_targets:
            key    = f"tiktok:{t['username']}"
            status = "🔴 EN LIVE" if key in active_keys else "👁️ En attente"
            lines.append(f"  ├─ @{t['username']}  {status}")
        lines.append("")

    if insta_targets:
        lines.append("📸 <b>Instagram</b> — <i>Polling 10s 🔄</i>")
        for t in insta_targets:
            key    = f"instagram:{t['username']}"
            status = "🔴 EN LIVE" if key in active_keys else "👁️ En attente"
            lines.append(f"  ├─ @{t['username']}  {status}")

    await _send(chat_id, "\n".join(lines))


async def _cmd_status(chat_id: int) -> None:
    targets     = targets_store.get_all()
    active_keys = _recording_active_ref or set()
    active_recs = [k for k in active_keys]
    uptime      = _uptime()

    status_icon = "🟢" if not active_recs else "🔴"
    rec_status  = f"🎬 {len(active_recs)} recording(s) en cours" if active_recs else "💤 Aucun live en ce moment"

    lines = [
        f"{status_icon} <b>LIVE RECORDER — Status</b>",
        f"{'─' * 30}",
        f"⏱️  Uptime : <b>{uptime}</b>",
        f"👁️  Targets : <b>{len(targets)}</b> surveillés",
        f"🎬  Recordings terminés : <b>{_stats['recordings_done']}</b>",
        f"",
        f"{rec_status}",
    ]

    if active_recs:
        for k in active_recs:
            plat, user = k.split(":", 1)
            emoji = "🎵" if plat == "tiktok" else "📸"
            lines.append(f"  └─ {emoji} @{user} ({plat})")

    lines += [
        f"",
        f"{'─' * 30}",
        f"<i>Bot opérationnel 24/7 sur Railway 🚀</i>",
    ]

    await _send(chat_id, "\n".join(lines))


async def _cmd_stop(chat_id: int, args: list[str]) -> None:
    active = rec_module.get_active()

    if not args:
        if not active:
            await _send(chat_id,
                "ℹ️ <b>Aucun recording en cours</b>\n\n"
                "Usage : <code>/stop tiktok:pseudo</code>\n"
                "ou <code>/stopall</code> pour tout stopper"
            )
            return
        lines = ["🎬 <b>Recordings en cours — lequel stopper ?</b>\n"]
        for key in active:
            plat, user = key.split(":", 1)
            emoji = "🎵" if plat == "tiktok" else "📸"
            lines.append(f"  • <code>/stop {key}</code>  {emoji} @{user}")
        lines.append("\n<i>Copie-colle la commande pour stopper</i>")
        await _send(chat_id, "\n".join(lines))
        return

    key = args[0].lower()
    if len(args) == 2:
        key = f"{args[0].lower()}:{args[1].lower()}"

    mid = await _send_and_get_id(chat_id, f"⏳ <b>Arrêt du recording...</b>\n<i>Patiente jusqu'à 5s</i>")
    ok  = await rec_module.stop_recording(key)
    plat, user = key.split(":", 1) if ":" in key else ("?", key)
    emoji = "🎵" if plat == "tiktok" else "📸"

    text = (
        f"🛑 <b>Recording stoppé</b>\n"
        f"{'─' * 28}\n"
        f"{emoji}  <code>@{user}</code>\n"
        f"📤  Upload en cours...\n"
        f"{'─' * 28}\n"
        f"<i>La vidéo arrive dans quelques instants</i>"
    ) if ok else (
        f"❌ <b>Aucun recording actif</b>\n"
        f"{'─' * 28}\n"
        f"<code>{key}</code> n'est pas en cours\n\n"
        f"Tape /stop pour voir les recordings actifs"
    )

    if mid:
        await _edit(chat_id, mid, text)
    else:
        await _send(chat_id, text)


async def _cmd_stopall(chat_id: int) -> None:
    active = rec_module.get_active()
    if not active:
        await _send(chat_id, "ℹ️ <b>Aucun recording en cours</b>")
        return

    mid = await _send_and_get_id(chat_id, f"⏳ <b>Arrêt de {len(active)} recording(s)...</b>")
    stopped = []
    for key in list(active.keys()):
        if await rec_module.stop_recording(key):
            stopped.append(key)

    lines = [f"🛑 <b>{len(stopped)} recording(s) stoppés</b>", f"{'─' * 28}"]
    for key in stopped:
        plat, user = key.split(":", 1)
        emoji = "🎵" if plat == "tiktok" else "📸"
        lines.append(f"  {emoji} @{user}")
    lines += [f"{'─' * 28}", "<i>Les vidéos arrivent sur le canal 📤</i>"]

    if mid:
        await _edit(chat_id, mid, "\n".join(lines))
    else:
        await _send(chat_id, "\n".join(lines))


async def _cmd_help(chat_id: int) -> None:
    await _send(chat_id,
        "🤖 <b>LIVE RECORDER — Commandes</b>\n"
        f"{'─' * 32}\n\n"
        "➕ <b>Ajouter un target</b>\n"
        "  /addtt <code>[pseudo]</code>  — TikTok 🎵\n"
        "  /addig <code>[pseudo]</code>  — Instagram 📸\n\n"
        "➖ <b>Retirer un target</b>\n"
        "  /rmtt <code>[pseudo]</code>   — TikTok 🎵\n"
        "  /rmig <code>[pseudo]</code>   — Instagram 📸\n\n"
        "🛑 <b>Stopper un recording</b>\n"
        "  /stop <code>[platform:pseudo]</code>  — Stoppe + upload\n"
        "  /stopall  — Stoppe tout\n\n"
        "📋 <b>Infos</b>\n"
        "  /list    — Tous les targets + statut live\n"
        "  /status  — État du bot (uptime, recordings)\n"
        "  /help    — Cette aide\n\n"
        f"{'─' * 32}\n"
        "⚡ TikTok = WebSocket temps réel\n"
        "🔄 Instagram = Polling toutes les 10s"
    )


# ─── DISPATCHER ───────────────────────────────────────────────────────────────

async def _handle_update(update: dict) -> None:
    msg = update.get("message") or update.get("channel_post")
    if not msg:
        return

    chat_id   = msg["chat"]["id"]
    chat_user = msg["chat"].get("username", "")
    text      = msg.get("text", "").strip()

    if not text.startswith("/"):
        return

    allowed = str(chat_id) == str(TELEGRAM_CHANNEL) or f"@{chat_user}" == TELEGRAM_CHANNEL
    if not allowed:
        log.warning(f"[Bot] Commande ignorée — chat non autorisé : {chat_id}")
        return

    parts = text.split()
    cmd   = parts[0].lower().split("@")[0]
    args  = parts[1:]

    log.info(f"[Bot] ⌨️  Commande : {cmd} {args}")

    if cmd == "/addtt":
        if not args:
            await _send(chat_id, "❌ Usage : <code>/addtt pseudo_tiktok</code>")
        else:
            await _cmd_add(chat_id, "tiktok", args[0])

    elif cmd == "/addig":
        if not args:
            await _send(chat_id, "❌ Usage : <code>/addig pseudo_instagram</code>")
        else:
            await _cmd_add(chat_id, "instagram", args[0])

    elif cmd == "/rmtt":
        if not args:
            await _send(chat_id, "❌ Usage : <code>/rmtt pseudo_tiktok</code>")
        else:
            await _cmd_remove(chat_id, "tiktok", args[0])

    elif cmd == "/rmig":
        if not args:
            await _send(chat_id, "❌ Usage : <code>/rmig pseudo_instagram</code>")
        else:
            await _cmd_remove(chat_id, "instagram", args[0])

    elif cmd == "/stop":
        await _cmd_stop(chat_id, args)

    elif cmd == "/stopall":
        await _cmd_stopall(chat_id)

    elif cmd == "/list":
        await _cmd_list(chat_id)

    elif cmd == "/status":
        await _cmd_status(chat_id)

    elif cmd == "/help" or cmd == "/start":
        await _cmd_help(chat_id)


# ─── POLLING LOOP ─────────────────────────────────────────────────────────────

async def poll_commands() -> None:
    offset = 0
    log.info("[Bot] 🤖 Command listener démarré")

    async with httpx.AsyncClient(timeout=35) as client:
        while True:
            try:
                resp = await client.get(f"{BASE}/getUpdates", params={
                    "offset":          offset,
                    "timeout":         30,
                    "allowed_updates": ["message", "channel_post"],
                })
                data = resp.json()

                if not data.get("ok"):
                    log.warning(f"[Bot] getUpdates error: {data}")
                    await asyncio.sleep(5)
                    continue

                for update in data.get("result", []):
                    offset = update["update_id"] + 1
                    asyncio.create_task(_handle_update(update))

            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"[Bot] Erreur polling: {e}")
                await asyncio.sleep(5)
