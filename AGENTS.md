# Internal TTS Service Agent

## Purpose
Standalone internal TTS service for converting text into `audio/ogg` using a local model.

## How to start
- Install Python dependencies: `python -m pip install -r requirements.txt`
- Run the service: `python -m tts_service`
- The service listens on `TTS_HOST:TTS_PORT` and exposes `/healthz`, `/voices`, and `/v1/synthesize`

## Why this design
- no external monolith dependencies
- no external database required
- strict validation for voice ids and text length
- output is always `audio/ogg` to match service contract
- local voice cache is persisted under `TTS_VOICE_DIR`
- concurrency is limited so the service is safe for a single VPS container

## Notes
This service is designed as a low-maintenance internal utility. It is not meant to become a full feature platform, but the structure allows quick fixes and future additions without coupling to client domains.
