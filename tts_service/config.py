from __future__ import annotations
import os
from pathlib import Path
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8000
    default_voice_id: str = "en_US_ljspeech"
    enabled_voice_ids: list[str] = ["en_US_ljspeech"]
    voice_dir: Path = Path("./data/voices")
    max_text_length: int = 500
    synthesis_timeout_sec: int = 30
    max_concurrent_synthesis: int = 1
    prefetch_voices_on_start: bool = False

    model_config = SettingsConfigDict(
        env_prefix="TTS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid",
    )

    @field_validator("enabled_voice_ids", mode="before")
    def split_enabled_voice_ids(cls, value):
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("voice_dir", mode="before")
    def normalize_voice_dir(cls, value):
        return Path(value).expanduser().resolve()

    @model_validator(mode="after")
    def validate_voice_settings(self):
        if not self.enabled_voice_ids:
            raise ValueError("TTS_ENABLED_VOICE_IDS must contain at least one voice id")
        if self.default_voice_id not in self.enabled_voice_ids:
            raise ValueError("TTS_DEFAULT_VOICE_ID must be one of enabled voices")

        if not self.voice_dir.exists():
            self.voice_dir.mkdir(parents=True, exist_ok=True)

        return self

settings = Settings()

os.environ.setdefault("TTS_HOME", str(settings.voice_dir))
