#!/usr/bin/env python3
"""
Upload GitHub Actions repository secrets from a local key/value file.

Quick start:
1. Create a GitHub personal access token with repository "Secrets" permission.
2. Export the token before running the script:
   export GITHUB_TOKEN=your_token_here
   or:
   export GITHUB_TOKEN=$(cat token)
3. Prepare a secrets file:
   VPS_HOST=203.0.113.10
   VPS_USER=deploy
   VPS_PORT=22
   VPS_SSH_KEY<<EOF
   -----BEGIN OPENSSH PRIVATE KEY-----
   ...
   -----END OPENSSH PRIVATE KEY-----
   EOF
4. Validate the file without uploading:
   python scripts/gh_set_repo_secrets.py owner/repo path/to/secrets.txt --dry-run
5. Upload secrets to the repository:
   python scripts/gh_set_repo_secrets.py owner/repo path/to/secrets.txt

Notes:
- "owner/repo" means the GitHub repository path, for example "IavnFGV/tts-service".
- Multiline values must use the KEY<<MARKER ... MARKER form.
- The script reads GITHUB_TOKEN first, then GH_TOKEN.
- For real uploads, install dependencies first:
  python -m pip install -r requirements.txt
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


def parse_secret_map(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    lines = text.splitlines()
    index = 0

    while index < len(lines):
        raw_line = lines[index]
        line = raw_line.strip()
        index += 1

        if not line or line.startswith("#"):
            continue

        if "<<" in raw_line:
            key_part, marker_part = raw_line.split("<<", 1)
            key = key_part.strip()
            marker = marker_part.strip()
            if not key:
                raise ValueError(f"Invalid secret key in line: {raw_line!r}")
            if not marker:
                raise ValueError(f"Missing multiline marker for key {key!r}")

            value_lines: list[str] = []
            while index < len(lines) and lines[index] != marker:
                value_lines.append(lines[index])
                index += 1

            if index >= len(lines):
                raise ValueError(f"Missing closing marker {marker!r} for key {key!r}")

            result[key] = "\n".join(value_lines)
            index += 1
            continue

        if "=" not in raw_line:
            raise ValueError(f"Expected KEY=value or KEY<<MARKER, got: {raw_line!r}")

        key, value = raw_line.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"Invalid secret key in line: {raw_line!r}")

        result[key] = value

    return result


def get_token() -> str | None:
    return os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")


def github_request(url: str, token: str, method: str = "GET", data: dict | None = None) -> dict:
    request_data = None
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "tts-service-secret-uploader",
    }

    if data is not None:
        request_data = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url, data=request_data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(request) as response:
            body = response.read()
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API {method} {url} failed: {exc.code} {details}") from exc

    if not body:
        return {}
    return json.loads(body.decode("utf-8"))


def get_repo_public_key(repo: str, token: str) -> tuple[str, str]:
    payload = github_request(
        f"https://api.github.com/repos/{repo}/actions/secrets/public-key",
        token,
    )
    return payload["key_id"], payload["key"]


def encrypt_secret(public_key_b64: str, value: str) -> str:
    try:
        from nacl import encoding, public
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "PyNaCl is not installed. Run `python -m pip install -r requirements.txt` "
            "or `python -m pip install PyNaCl` before uploading secrets."
        ) from exc

    public_key = public.PublicKey(public_key_b64.encode("utf-8"), encoding.Base64Encoder())
    sealed_box = public.SealedBox(public_key)
    encrypted = sealed_box.encrypt(value.encode("utf-8"))
    return base64.b64encode(encrypted).decode("utf-8")


def set_secret(repo: str, token: str, public_key_id: str, public_key_b64: str, key: str, value: str) -> None:
    encrypted_value = encrypt_secret(public_key_b64, value)
    github_request(
        f"https://api.github.com/repos/{repo}/actions/secrets/{key}",
        token,
        method="PUT",
        data={
            "encrypted_value": encrypted_value,
            "key_id": public_key_id,
        },
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read a key/value secrets map file and upload secrets to a GitHub repository via the GitHub API."
    )
    parser.add_argument("repo", help="Repository in owner/name format.")
    parser.add_argument("secrets_file", help="Path to the secrets map file.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and print secret names without uploading them.",
    )
    args = parser.parse_args()

    secrets_path = Path(args.secrets_file)
    if not secrets_path.is_file():
        print(f"Secrets file not found: {secrets_path}", file=sys.stderr)
        return 1

    try:
        secrets = parse_secret_map(secrets_path.read_text(encoding="utf-8"))
    except ValueError as exc:
        print(f"Failed to parse secrets file: {exc}", file=sys.stderr)
        return 1

    if not secrets:
        print("No secrets found in the input file.", file=sys.stderr)
        return 1

    if args.dry_run:
        for name in secrets:
            print(name)
        return 0

    token = get_token()
    if not token:
        print(
            "Missing GitHub token. Set GITHUB_TOKEN or GH_TOKEN before running this script.",
            file=sys.stderr,
        )
        return 1

    try:
        public_key_id, public_key_b64 = get_repo_public_key(args.repo, token)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    for name, value in secrets.items():
        print(f"Setting {name} in {args.repo}")
        try:
            set_secret(args.repo, token, public_key_id, public_key_b64, name, value)
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            return 1

    print(f"Uploaded {len(secrets)} secret(s) to {args.repo}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
