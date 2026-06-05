from dataclasses import dataclass
from typing import Dict

@dataclass(frozen=True)
class Voice:
    id: str
    label: str
    model_name: str

VOICE_CATALOG: Dict[str, Voice] = {
    "en_US_amy": Voice(
        id="en_US_amy",
        label="American English Amy (female)",
        model_name="en_US-amy-medium",
    ),
    "en_US_lessac": Voice(
        id="en_US_lessac",
        label="American English Lessac (female)",
        model_name="en_US-lessac-medium",
    ),
    "en_US_ryan": Voice(
        id="en_US_ryan",
        label="American English Ryan (male)",
        model_name="en_US-ryan-medium",
    ),
    "en_GB_alba": Voice(
        id="en_GB_alba",
        label="British English Alba (female)",
        model_name="en_GB-alba-medium",
    ),
    "en_GB_alan": Voice(
        id="en_GB_alan",
        label="British English Alan (male)",
        model_name="en_GB-alan-medium",
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
