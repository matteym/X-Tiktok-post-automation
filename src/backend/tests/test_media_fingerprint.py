"""Tests for media SHA-256 + size fingerprinting and set hashing."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parent.parent
MEDIA_PACKAGE = BACKEND_ROOT / "src" / "content_autopilot" / "media"
FINGERPRINT_MODULE = MEDIA_PACKAGE / "fingerprint.py"


def _expected_fingerprint(content: bytes) -> str:
    digest = hashlib.sha256(content).hexdigest()
    return f"{digest}:{len(content)}"


def test_media_fingerprint_module_exists() -> None:
    assert (MEDIA_PACKAGE / "__init__.py").is_file()
    assert FINGERPRINT_MODULE.is_file()


def test_fingerprint_file_returns_sha256_size_string(tmp_path: Path) -> None:
    from content_autopilot.media.fingerprint import fingerprint_file

    content = b"photo-or-video-bytes"
    media_path = tmp_path / "clip.mp4"
    media_path.write_bytes(content)

    assert fingerprint_file(media_path) == _expected_fingerprint(content)


def test_fingerprint_file_stream_reads_binary_fixture(tmp_path: Path) -> None:
    from content_autopilot.media.fingerprint import fingerprint_file

    content = b"a" * 65536 + b"b" * 65536
    media_path = tmp_path / "large-media.bin"
    media_path.write_bytes(content)

    assert fingerprint_file(media_path) == _expected_fingerprint(content)


def test_fingerprint_file_is_independent_of_filename(tmp_path: Path) -> None:
    from content_autopilot.media.fingerprint import fingerprint_file

    content = b"shared-media-payload"
    first = tmp_path / "front.jpg"
    second = tmp_path / "different-name.mp4"
    first.write_bytes(content)
    second.write_bytes(content)

    assert fingerprint_file(first) == fingerprint_file(second)


def test_fingerprint_file_is_independent_of_directory(tmp_path: Path) -> None:
    from content_autopilot.media.fingerprint import fingerprint_file

    content = b"shared-media-payload"
    root_file = tmp_path / "clip.mp4"
    nested_file = tmp_path / "nested" / "clip.mp4"
    nested_file.parent.mkdir()
    root_file.write_bytes(content)
    nested_file.write_bytes(content)

    assert fingerprint_file(root_file) == fingerprint_file(nested_file)


def test_fingerprint_media_paths_preserves_cli_video_order(tmp_path: Path) -> None:
    from content_autopilot.media.fingerprint import fingerprint_media_paths

    first_content = b"first-video"
    second_content = b"second-photo"
    first_path = tmp_path / "one.mp4"
    second_path = tmp_path / "two.jpg"
    first_path.write_bytes(first_content)
    second_path.write_bytes(second_content)

    fingerprints = fingerprint_media_paths([first_path, second_path])

    assert fingerprints == [
        _expected_fingerprint(first_content),
        _expected_fingerprint(second_content),
    ]


def test_media_set_hash_is_order_sensitive() -> None:
    from content_autopilot.media.fingerprint import media_set_hash

    first = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa:11"
    second = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb:12"

    forward = media_set_hash([first, second])
    reverse = media_set_hash([second, first])

    assert forward != reverse


def test_media_set_hash_matches_for_same_files_regardless_of_path(
    tmp_path: Path,
) -> None:
    from content_autopilot.media.fingerprint import (
        fingerprint_media_paths,
        media_set_hash,
    )

    content_a = b"alpha-media"
    content_b = b"beta-media"
    paths_a = [
        tmp_path / "a1.mp4",
        tmp_path / "a2.jpg",
    ]
    paths_b = [
        tmp_path / "nested" / "other-name.mp4",
        tmp_path / "elsewhere" / "photo.png",
    ]
    paths_b[0].parent.mkdir()
    paths_b[1].parent.mkdir()
    for path, content in zip(paths_a, [content_a, content_b], strict=True):
        path.write_bytes(content)
    for path, content in zip(paths_b, [content_a, content_b], strict=True):
        path.write_bytes(content)

    set_hash_a = media_set_hash(fingerprint_media_paths(paths_a))
    set_hash_b = media_set_hash(fingerprint_media_paths(paths_b))

    assert set_hash_a == set_hash_b


def test_fingerprint_media_paths_changes_when_video_order_changes(tmp_path: Path) -> None:
    from content_autopilot.media.fingerprint import (
        fingerprint_media_paths,
        media_set_hash,
    )

    first_content = b"first"
    second_content = b"second"
    first_path = tmp_path / "first.mp4"
    second_path = tmp_path / "second.mp4"
    first_path.write_bytes(first_content)
    second_path.write_bytes(second_content)

    forward = fingerprint_media_paths([first_path, second_path])
    reverse = fingerprint_media_paths([second_path, first_path])

    assert forward != reverse
    assert media_set_hash(forward) != media_set_hash(reverse)
