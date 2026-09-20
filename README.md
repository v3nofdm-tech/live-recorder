# 🔴 Live Recorder

Bot de surveillance 24/7 qui détecte les lives TikTok/Instagram et les enregistre intégralement pour les envoyer sur Telegram.

## Features

- ✅ Détection automatique de live TikTok + Instagram
- ✅ Recording de A à Z (peu importe l'heure)
- ✅ Envoi automatique sur canal Telegram
- ✅ Gestion des gros fichiers (auto-split si > 49MB)
- ✅ Multi-comptes extensible
- ✅ Deploy Railway 24/7

## Structure

```
live-recorder/
├── main.py              # Orchestrateur principal
├── config.py            # Config & targets
├── recorder.py          # Recording avec streamlink
├── telegram_sender.py   # Envoi Telegram
├── monitors/
│   ├── tiktok.py        # Détection live TikTok
│   └── instagram.py     # Détection live Instagram
├── Dockerfile
├── railway.toml
└── .env.example
```

## Deploy Railway

1. Push ce repo sur GitHub
2. Créer un nouveau projet Railway → "Deploy from GitHub repo"
3. Ajouter les variables d'environnement dans Railway → Variables :
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHANNEL`
   - `INSTAGRAM_USERNAME` (quand t'as le compte)
   - `INSTAGRAM_PASSWORD`
4. Railway build + deploy automatiquement via le Dockerfile

## Ajouter un nouveau target

Dans `config.py`, ajoute une entrée dans `TARGETS` :

```python
{
    "platform": "tiktok",   # ou "instagram"
    "username": "autrecompte",
    "label": "🎵 Autre Compte",
},
```

C'est tout.
