import pytest

from tts_service.text import SynthesizeRequest, normalize_text


def test_normalize_text_trims_and_collapses_whitespace():
    raw = "  hello   world\n this  is  spaced "
    normalized = normalize_text(raw)
    assert normalized == "hello world this is spaced"


def test_synthesize_request_defaults_speed_to_one():
    request = SynthesizeRequest(text="hello", voice_id=" voice ")
    assert request.voice_id == "voice"
    assert request.speed == 1.0


@pytest.mark.parametrize("speed", [0.1, 1.0, 5.0])
def test_synthesize_request_accepts_speed_in_range(speed: float):
    request = SynthesizeRequest(text="hello", voice_id="voice", speed=speed)
    assert request.speed == speed
