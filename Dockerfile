# syntax=docker/dockerfile:1.7
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Debian security fixes land here before the upstream python image is rebuilt.
# SECURITY_REFRESH (a timestamp, set by the deploy workflow) re-runs this layer
# on every deploy, so the build cache never hides a fix.
ARG SECURITY_REFRESH=0
RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && apt-get install -y --no-install-recommends ffmpeg espeak-ng \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install --upgrade "pip>=26.3,<27" "setuptools>=78.1.1,<81" \
    && python -m pip install -r requirements.txt

COPY . .
RUN mkdir -p /data/voices

EXPOSE 8000
ENTRYPOINT ["python", "-m", "tts_service"]
