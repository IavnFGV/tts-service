from __future__ import annotations

import asyncio
import tempfile
import wave
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict

from piper.config import SynthesisConfig
from piper.download_voices import download_voice
from piper.voice import PiperVoice

from .audio import convert_wav_to_ogg
from .config import Settings
from .voices import VoiceRegistry, Voice


class SynthesizerAdapter:
    def __init__(self, settings: Settings, registry: VoiceRegistry):
        self.settings = settings
        self.registry = registry
        self.semaphore = asyncio.Semaphore(settings.max_concurrent_synthesis)
        self.voices: Dict[str, PiperVoice] = {}
        self.executor = ThreadPoolExecutor(max_workers=settings.max_concurrent_synthesis)

    async def synthesize_ogg(self, text: str, voice_id: str, speed: float = 1.0) -> bytes:
        voice = self.registry.get_voice(voice_id)
        if voice is None:
            raise ValueError("unknown voice")

        async with self.semaphore:
            loop = asyncio.get_running_loop()
            return await asyncio.wait_for(
                loop.run_in_executor(self.executor, self._render, voice, text, speed),
                timeout=self.settings.synthesis_timeout_sec,
            )

    def _render(self, voice: Voice, text: str, speed: float) -> bytes:
        piper_voice = self._get_voice(voice)
        syn_config = self._build_synthesis_config(piper_voice, speed)
        with tempfile.TemporaryDirectory() as tmpdir:
            wav_path = Path(tmpdir) / "output.wav"
            ogg_path = Path(tmpdir) / "output.ogg"
            with wave.open(str(wav_path), "wb") as wav_file:
                piper_voice.synthesize_wav(text, wav_file, syn_config=syn_config)
            convert_wav_to_ogg(wav_path, ogg_path)
            return ogg_path.read_bytes()

    def _build_synthesis_config(self, voice: PiperVoice, speed: float) -> SynthesisConfig:
        return SynthesisConfig(
            length_scale=1.0 / speed,
            noise_scale=voice.config.noise_scale,
            noise_w_scale=voice.config.noise_w_scale,
        )

    def _get_voice(self, voice: Voice) -> PiperVoice:
        if voice.id not in self.voices:
            self.voices[voice.id] = self._load_voice(voice)
        return self.voices[voice.id]

    def _load_voice(self, voice: Voice) -> PiperVoice:
        self.settings.voice_dir.mkdir(parents=True, exist_ok=True)
        download_voice(voice.model_name, self.settings.voice_dir)
        model_path = self.settings.voice_dir / f"{voice.model_name}.onnx"
        return PiperVoice.load(model_path)

    def prefetch_models(self) -> None:
        for voice in self.registry.voices:
            self._get_voice(voice)
