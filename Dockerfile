# 🐳 Dockerfile — Live Recorder
# Python + streamlink + ffmpeg dans une image propre

FROM python:3.11-slim

LABEL maintainer="v3no"
LABEL description="Instagram + TikTok Live Recorder → Telegram"

# Install ffmpeg + streamlink deps système
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Deps Python en premier (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Code source
COPY . .

# Dossier recordings
RUN mkdir -p /tmp/recordings

# Variable d'env pour le dossier de recordings
ENV RECORDINGS_DIR=/tmp/recordings

# Lance le bot
CMD ["python", "main.py"]
