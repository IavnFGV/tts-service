from __future__ import annotations
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from .config import settings
from .synth import SynthesizerAdapter
from .text import SynthesizeRequest
from .voices import VoiceRegistry

logger = logging.getLogger("tts_service")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("TTS service starting on %s:%s", settings.host, settings.port)
    logger.info("Configured voices: %s", [voice.id for voice in registry.voices])
    if settings.prefetch_voices_on_start:
        logger.info("Prefetching all configured voices on startup")
        await asyncio.to_thread(synthesizer.prefetch_models)
    yield


app = FastAPI(title="Internal TTS Service", version="0.1.0", lifespan=lifespan)
registry = VoiceRegistry(settings.enabled_voice_ids, settings.default_voice_id)
synthesizer = SynthesizerAdapter(settings, registry)


class VoicesResponse(BaseModel):
    default_voice_id: str
    voices: list[dict[str, str]]


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    first_error = exc.errors()[0] if exc.errors() else {}
    detail = first_error.get("msg", "validation error")
    return JSONResponse(status_code=400, content={"detail": detail})


@app.get("/voices", response_model=VoicesResponse)
async def get_voices() -> dict[str, object]:
    return {
        "default_voice_id": registry.default_voice_id,
        "voices": registry.list_serializable(),
    }


@app.post("/v1/synthesize")
async def synthesize(request: SynthesizeRequest) -> Response:
    if len(request.text) > settings.max_text_length:
        raise HTTPException(
            status_code=400,
            detail=f"text length must be at most {settings.max_text_length} characters",
        )

    if registry.get_voice(request.voice_id) is None:
        raise HTTPException(status_code=400, detail="unknown voice_id")

    try:
        logger.info(
            "Synthesis requested voice=%s text_length=%s",
            request.voice_id,
            len(request.text),
        )
        audio_bytes = await synthesizer.synthesize_ogg(request.text, request.voice_id)
        return Response(content=audio_bytes, media_type="audio/ogg")
    except asyncio.TimeoutError:
        logger.exception("Synthesis timed out for voice=%s", request.voice_id)
        raise HTTPException(status_code=500, detail="synthesis timeout")
    except Exception as exc:
        logger.exception("Synthesis failed for voice=%s", request.voice_id)
        raise HTTPException(status_code=500, detail="synthesis failed")
