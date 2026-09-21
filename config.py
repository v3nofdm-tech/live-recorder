"""
Config central — touches ici pour changer les targets/creds.
Les secrets sensibles passent par les ENV VARS (Railway les gère).
"""
import os

# ─── TELEGRAM ────────────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8592571510:AAEjgYKD0Vxddr35d5Y-DNGN5MbMXpZq4VM")
TELEGRAM_CHANNEL   = os.getenv("TELEGRAM_CHANNEL", "@livev3No")  # ou le chat_id numérique

# ─── TARGETS ─────────────────────────────────────────────────────────────────
# Ajoute autant d'entrées que tu veux ici, c'est tout !
TARGETS = [
    # TikTok
    {"platform": "tiktok", "username": "sosamann777", "label": "🎵 sosamann777 (TikTok)"},
    {"platform": "tiktok", "username": "keeqaid0", "label": "🎵 keeqaid0 (TikTok)"},
    {"platform": "tiktok", "username": "xyy1itee", "label": "🎵 xyy1itee (TikTok)"},
    # Instagram
    {"platform": "instagram", "username": "sosamann777", "label": "📸 sosamann777 (Instagram)"},
    {"platform": "instagram", "username": "keeqaid", "label": "📸 keeqaid (Instagram)"},
    {"platform": "instagram", "username": "beewaba", "label": "📸 beewaba (Instagram)"},
    {"platform": "instagram", "username": "sakigagnoa", "label": "📸 sakigagnoa (Instagram)"},
    {"platform": "instagram", "username": "63wog", "label": "📸 63wog (Instagram)"},
    {"platform": "instagram", "username": "63kluf", "label": "📸 63kluf (Instagram)"},
]

# ─── INSTAGRAM CREDS (à remplir plus tard) ───────────────────────────────────
INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME", "")
INSTAGRAM_PASSWORD = os.getenv("INSTAGRAM_PASSWORD", "")

# ─── RECORDING ───────────────────────────────────────────────────────────────
RECORDINGS_DIR     = os.getenv("RECORDINGS_DIR", "/tmp/recordings")
POLL_INTERVAL_SEC      = int(os.getenv("POLL_INTERVAL_SEC", "60"))   # Instagram poll (fallback)
INSTA_POLL_INTERVAL    = int(os.getenv("INSTA_POLL_INTERVAL", "10"))  # Instagram: check toutes les 10s
MAX_FILE_SIZE_MB   = 2000  # Telegram limite bot = 2GB avec local server, 50MB sinon

# ─── QUALITY ─────────────────────────────────────────────────────────────────
# best = qualité max, sinon "720p", "480p", etc.
STREAMLINK_QUALITY = "best"
