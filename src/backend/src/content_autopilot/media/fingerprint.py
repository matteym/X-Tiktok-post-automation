"""SHA-256 + size media fingerprinting for deduplication."""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from pathlib import Path

_READ_CHUNK_SIZE = 65536


def fingerprint_file(path: Path | str) -> str:
    """Return a stable per-file fingerprint as ``{sha256_hex}:{size_bytes}``."""
    media_path = Path(path)
    hasher = hashlib.sha256()
    size = 0

    with media_path.open("rb") as media_file:
        while chunk := media_file.read(_READ_CHUNK_SIZE):
            hasher.update(chunk)
            size += len(chunk)

    return f"{hasher.hexdigest()}:{size}"


def fingerprint_media_paths(paths: Sequence[Path | str]) -> list[str]:
    """Fingerprint media files in the exact order provided by the CLI."""
    return [fingerprint_file(path) for path in paths]


def media_set_hash(fingerprints: Sequence[str]) -> str:
    """Return a canonical hash for an ordered list of media fingerprints."""
    payload = "\n".join(fingerprints)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
