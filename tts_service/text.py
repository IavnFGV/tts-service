import re
from pydantic import BaseModel, ConfigDict, Field, field_validator


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


class SynthesizeRequest(BaseModel):
    text: str = Field(...)
    voice_id: str = Field(...)
    speed: float = Field(default=1.0, ge=0.1, le=5.0)

    @field_validator("text")
    def normalize_text_field(cls, value: str) -> str:
        normalized = normalize_text(value)
        if not normalized:
            raise ValueError("text must not be empty")
        return normalized

    @field_validator("voice_id", mode="before")
    def normalize_voice_id(cls, value: str) -> str:
        return value.strip()

    @field_validator("speed")
    def normalize_speed(cls, value: float) -> float:
        return float(value)

    model_config = ConfigDict(extra="forbid")
