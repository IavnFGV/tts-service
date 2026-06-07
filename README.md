# Internal TTS Service

Standalone internal TTS microservice for local speech synthesis.

## What it does
- Exposes internal HTTP endpoints: `/healthz`, `/voices`, `/v1/synthesize`
- Accepts text and a configured voice id
- Optionally accepts a playback speed coefficient from `0.1` to `5.0`
- Synthesizes speech locally with Piper
- Returns final audio as `audio/ogg` (Opus)

## Start locally
1. Install dependencies:
   ```bash
   python -m pip install -r requirements.txt
   ```
2. Run service:
   ```bash
   python -m tts_service
   ```

## Start with Docker Compose
1. Build and start the service:
   ```bash
   docker compose up --build
   ```
2. The service will be available on `http://0.0.0.0:8000`.

## Deployment
This repository includes a GitHub Actions deployment workflow at `.github/workflows/deploy.yml`.
It runs tests, then deploys to a VPS over SSH using `docker compose up -d --build`.

On the target host, the workflow expects:
- a `.env` file present in the checked-out service directory
- Docker and Docker Compose installed
- a writable host directory for persisted voices at `/srv/services/tts/voices`

Secrets required by the workflow:
- `VPS_HOST`
- `VPS_USER`
- `VPS_PORT`
- `VPS_SSH_KEY`

## CPU-only operation
This service is configured to run on CPU only and does not require a GPU device.

For a low-resource VPS like `2 vCPU / 4 GB RAM`, keep `TTS_MAX_CONCURRENT_SYNTHESIS=1` and use short text inputs. That is the safest configuration for reliable operation.

## Configuration
Use `.env` or environment variables. See `.env.example`.

## Architecture decisions
- FastAPI for a small internal HTTP API
- Piper for local model-based synthesis
- `ffmpeg` for WAV-to-OGG/Opus conversion
- voice catalog is fixed and validated; unknown voice ids fail closed
- concurrency limited by `TTS_MAX_CONCURRENT_SYNTHESIS`
- Piper model downloads are persisted under `TTS_VOICE_DIR`

## Available voices
The service ships with five English Piper voices:
- `en_US_amy` — American English Amy (female)
- `en_US_lessac` — American English Lessac (female)
- `en_US_ryan` — American English Ryan (male)
- `en_GB_alba` — British English Alba (female)
- `en_GB_alan` — British English Alan (male)

Use `/voices` to discover them at runtime and pass `voice_id` to `/v1/synthesize`.

## Synthesis request
`POST /v1/synthesize` accepts JSON with:
- `text` — required, normalized and length-limited text input
- `voice_id` — required, must match one of the configured voices
- `speed` — optional playback speed coefficient from `0.1` to `5.0`; defaults to `1.0`

Example request:

```json
{
  "text": "Hello world",
  "voice_id": "en_US_amy",
  "speed": 1.25
}
```

When `speed` is omitted, the service uses `1.0`.
Internally this is translated to Piper's `length_scale` as `1.0 / speed`, so values above `1.0` speak faster and values below `1.0` speak slower.

## GitHub secrets helper
If you want to load multiple GitHub Actions secrets into a repository from one file, use:

```bash
python scripts/gh_set_repo_secrets.py owner/repo scripts/github-secrets.example --dry-run
export GITHUB_TOKEN=github_pat_or_fine_grained_token
python scripts/gh_set_repo_secrets.py owner/repo path/to/secrets.txt
```

File format:

```text
VPS_HOST=203.0.113.10
VPS_USER=deploy
VPS_PORT=22
VPS_SSH_KEY<<EOF
-----BEGIN OPENSSH PRIVATE KEY-----
...
-----END OPENSSH PRIVATE KEY-----
EOF
```

The script uses the GitHub REST API directly. Set `GITHUB_TOKEN` or `GH_TOKEN` before running it.
