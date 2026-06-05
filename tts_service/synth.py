from __future__ import annotations
import asyncio
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict

import numpy as np
import torch
from TTS.api import TTS

from .audio import convert_wav_to_ogg
from .config import Settings
from .voices import VoiceRegistry, Voice

# Ensure torch can safely load Coqui checkpoints that require numpy scalar support.
# This is needed for newer PyTorch versions when weights_only loading is active.
try:
    torch.serialization.add_safe_globals([np.core.multiarray.scalar])
except Exception:
    pass


class SynthesizerAdapter:
    def __init__(self, settings: Settings, registry: VoiceRegistry):
        self.settings = settings
        self.registry = registry
        self.semaphore = asyncio.Semaphore(settings.max_concurrent_synthesis)
        self.tts_clients: Dict[str, TTS] = {}
        self.executor = ThreadPoolExecutor(max_workers=settings.max_concurrent_synthesis)

    async def synthesize_ogg(self, text: str, voice_id: str) -> bytes:
        voice = self.registry.get_voice(voice_id)
        if voice is None:
            raise ValueError("unknown voice")

        async with self.semaphore:
            loop = asyncio.get_running_loop()
            return await asyncio.wait_for(
                loop.run_in_executor(self.executor, self._render, voice, text),
                timeout=self.settings.synthesis_timeout_sec,
            )

    def _render(self, voice: Voice, text: str) -> bytes:
        os.environ.setdefault("TTS_HOME", str(self.settings.voice_dir))
        tts = self._get_tts(voice)

        with tempfile.TemporaryDirectory() as tmpdir:
            wav_path = Path(tmpdir) / "output.wav"
            ogg_path = Path(tmpdir) / "output.ogg"
            tts.tts_to_file(text=text, file_path=str(wav_path))
            convert_wav_to_ogg(wav_path, ogg_path)
            return ogg_path.read_bytes()

    def _get_tts(self, voice: Voice) -> TTS:
        if voice.id not in self.tts_clients:
            self.tts_clients[voice.id] = self._load_tts(voice)
        return self.tts_clients[voice.id]

    def _load_tts(self, voice: Voice) -> TTS:
        os.environ.setdefault("TTS_HOME", str(self.settings.voice_dir))
        return TTS(model_name=voice.model_name, progress_bar=False, gpu=False)

    def prefetch_models(self) -> None:
        for voice in self.registry.voices:
            self._get_tts(voice)
