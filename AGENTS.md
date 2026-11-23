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

## Deploy and security updates
- Push to `main` -> `.github/workflows/deploy.yml`: tests + `pip-audit`, then
  on the VPS `docker compose build --pull` + `up --wait` in
  `/opt/dockge/stacks/tts-service`. Also weekly (Mon 02:17 UTC) and manually.
- `SECURITY_REFRESH` (a timestamp per build) re-runs the `apt-get upgrade`
  layer every time; keep it, or the build cache hides Debian fixes.
- The `infra-vps.fix*` labels in `docker-compose.yml` let the infra-vps
  security report offer a Telegram "🔧 Fix" button that runs this deploy
  workflow (see infra-vps `docs/security-updates.md`). Dependabot PRs are
  auto-merged when tests pass.
