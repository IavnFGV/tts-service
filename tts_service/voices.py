from dataclasses import dataclass
from typing import Dict

@dataclass(frozen=True)
class Voice:
    id: str
    label: str
    model_name: str

VOICE_CATALOG: Dict[str, Voice] = {
    "en_US_ljspeech": Voice(
        id="en_US_ljspeech",
        label="English LJSpeech (female)",
        model_name="tts_models/en/ljspeech/tacotron2-DDC",
    ),
    "en_US_ljspeech_vits": Voice(
        id="en_US_ljspeech_vits",
        label="English LJSpeech VITS (female)",
        model_name="tts_models/en/ljspeech/vits",
    ),
    "en_US_ek1": Voice(
        id="en_US_ek1",
        label="English EK1 (male)",
        model_name="tts_models/en/ek1/tacotron2",
    ),
    "en_US_blizzard2013": Voice(
        id="en_US_blizzard2013",
        label="English Blizzard2013 (male)",
        model_name="tts_models/en/blizzard2013/capacitron-t2-c50",
    ),
    "en_US_jenny": Voice(
        id="en_US_jenny",
        label="English Jenny (youthful female)",
        model_name="tts_models/en/jenny/jenny",
    ),
}

class VoiceRegistry:
    def __init__(self, enabled_voice_ids: list[str], default_voice_id: str):
        unknown = [voice_id for voice_id in enabled_voice_ids if voice_id not in VOICE_CATALOG]
        if unknown:
            raise ValueError(f"Unknown voice ids in TTS_ENABLED_VOICE_IDS: {', '.join(unknown)}")

        self.voices = [VOICE_CATALOG[voice_id] for voice_id in enabled_voice_ids]
        self.index = {voice.id: voice for voice in self.voices}

        if default_voice_id not in self.index:
            raise ValueError("TTS_DEFAULT_VOICE_ID must be one of enabled voices")

        self.default_voice_id = default_voice_id

    def get_voice(self, voice_id: str):
        return self.index.get(voice_id)

    def list_serializable(self):
        return [{"id": voice.id, "label": voice.label} for voice in self.voices]
