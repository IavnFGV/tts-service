from tts_service.text import normalize_text


def test_normalize_text_trims_and_collapses_whitespace():
    raw = "  hello   world\n this  is  spaced "
    normalized = normalize_text(raw)
    assert normalized == "hello world this is spaced"
