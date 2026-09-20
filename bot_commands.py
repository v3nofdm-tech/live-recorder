"""
Bot Commands 🤖
Écoute les commandes Telegram via long-polling getUpdates.
Pas de dépendance extra — juste httpx.

Commandes disponibles :
  /addtt [pseudo]   — ajoute un compte TikTok
  /addig [pseudo]   — ajoute un compte Instagram
  /rmtt  [pseudo]   — retire un compte TikTok
  /rmig  [pseudo]   — retire un compte Instagram
  /list             — liste tous les targets actifs
"""
import asyncio
import logging
import httpx
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL
import targets_store

log = logging.getLogger(__name__)
BASE = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# Seul le canal autorisé peut envoyer des commandes
ALLOWED_CHAT = TELEGRAM_CHANNEL  # "@livev3No"


async def _reply(chat_id: int | str, text: str) -> None:
    async with httpx.AsyncClient(timeout=10) as c:
        await c.post(f"{BASE}/sendMessage", json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
        })


async def _handle_update(update: dict) -> None:
    """Parse et dispatch une update Telegram."""
    msg = update.get("message") or update.get("channel_post")
    if not msg:
        return

    chat_id   = msg["chat"]["id"]
    chat_user = msg["chat"].get("username", "")
    text      = msg.get("text", "").strip()

    if not text.startswith("/"):
        return

    # Sécurité : seul le canal autorisé
    allowed = str(chat_id) == str(ALLOWED_CHAT) or f"@{chat_user}" == ALLOWED_CHAT
    if not allowed:
        log.warning(f"[Bot] Commande ignorée de chat non autorisé: {chat_id}")
        return

    parts    = text.split()
    cmd      = parts[0].lower().split("@")[0]  # ignore @botname suffix
    args     = parts[1:]

    log.info(f"[Bot] Commande reçue : {cmd} {args}")

    # ── /addtt [pseudo] ───────────────────────────────────────────────────
    if cmd == "/addtt":
        if not args:
            await _reply(chat_id, "❌ Usage : <code>/addtt pseudo_tiktok</code>")
            return
        ok, msg_text = await targets_store.add_target("tiktok", args[0])
        await _reply(chat_id, msg_text)

    # ── /addig [pseudo] ───────────────────────────────────────────────────
    elif cmd == "/addig":
        if not args:
            await _reply(chat_id, "❌ Usage : <code>/addig pseudo_instagram</code>")
            return
        ok, msg_text = await targets_store.add_target("instagram", args[0])
        await _reply(chat_id, msg_text)

    # ── /rmtt [pseudo] ────────────────────────────────────────────────────
    elif cmd == "/rmtt":
        if not args:
            await _reply(chat_id, "❌ Usage : <code>/rmtt pseudo_tiktok</code>")
            return
        ok, msg_text = await targets_store.remove_target("tiktok", args[0])
        await _reply(chat_id, msg_text)

    # ── /rmig [pseudo] ────────────────────────────────────────────────────
    elif cmd == "/rmig":
        if not args:
            await _reply(chat_id, "❌ Usage : <code>/rmig pseudo_instagram</code>")
            return
        ok, msg_text = await targets_store.remove_target("instagram", args[0])
        await _reply(chat_id, msg_text)

    # ── /list ─────────────────────────────────────────────────────────────
    elif cmd == "/list":
        targets = targets_store.get_all()
        if not targets:
            await _reply(chat_id, "📋 Aucun target en surveillance.")
            return
        lines = ["📋 <b>Targets actifs :</b>"]
        for t in targets:
            lines.append(f"  • {t['label']}")
        await _reply(chat_id, "\n".join(lines))

    # ── /help ─────────────────────────────────────────────────────────────
    elif cmd == "/help":
        await _reply(chat_id,
            "🤖 <b>Commandes disponibles :</b>\n\n"
            "/addtt [pseudo] — Ajouter TikTok\n"
            "/addig [pseudo] — Ajouter Instagram\n"
            "/rmtt [pseudo]  — Retirer TikTok\n"
            "/rmig [pseudo]  — Retirer Instagram\n"
            "/list           — Voir tous les targets\n"
        )


async def poll_commands() -> None:
    """
    Long-polling getUpdates — écoute les commandes en temps réel.
    Tourne en parallèle du monitoring.
    """
    offset = 0
    log.info("[Bot] 🤖 Écoute des commandes démarrée")

    async with httpx.AsyncClient(timeout=35) as client:
        while True:
            try:
                resp = await client.get(f"{BASE}/getUpdates", params={
                    "offset": offset,
                    "timeout": 30,
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
