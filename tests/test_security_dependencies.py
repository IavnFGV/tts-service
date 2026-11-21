from pathlib import Path

import nacl


def test_pynacl_uses_patched_release():
    assert tuple(int(part) for part in nacl.__version__.split(".")) >= (1, 6, 2)


def test_docker_context_excludes_runtime_secrets():
    root = Path(__file__).resolve().parents[1]
    patterns = set((root / ".dockerignore").read_text().splitlines())
    assert {".env", ".env.*", ".git", "data"} <= patterns
    assert "!.env.example" in patterns
