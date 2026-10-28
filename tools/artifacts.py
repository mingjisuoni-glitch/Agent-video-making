"""Shared hashing and ffprobe helpers for generated artifacts."""

from __future__ import annotations

import hashlib
import json
import subprocess
from fractions import Fraction
from pathlib import Path


def sha256_file(path: Path, limit: int | None = None) -> str:
    digest = hashlib.sha256()
    remaining = limit
    with path.open("rb") as handle:
        while remaining is None or remaining > 0:
            size = 1024 * 1024 if remaining is None else min(1024 * 1024, remaining)
            chunk = handle.read(size)
            if not chunk:
                break
            digest.update(chunk)
            if remaining is not None:
                remaining -= len(chunk)
    return digest.hexdigest()


def write_json_atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _number(value) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if result >= 0 else None


def _fps(value) -> float | None:
    try:
        fraction = Fraction(str(value))
    except (ValueError, ZeroDivisionError):
        return None
    return float(fraction) if fraction > 0 else None


def probe_media(path: Path, runner=subprocess.run) -> dict:
    command = [
        "ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path),
    ]
    try:
        completed = runner(
            command,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        payload = json.loads(completed.stdout)
    except (OSError, ValueError, json.JSONDecodeError, subprocess.SubprocessError) as error:
        raise ValueError(f"ffprobe could not read {path}: {error}") from error
    if not isinstance(payload, dict) or not isinstance(payload.get("streams"), list):
        raise TypeError(f"ffprobe returned invalid JSON for {path}")
    streams = payload["streams"]
    video_stream = next((item for item in streams if item.get("codec_type") == "video"), None)
    audio_stream = next((item for item in streams if item.get("codec_type") == "audio"), None)
    duration = _number((payload.get("format") or {}).get("duration"))
    if duration is None:
        durations = [_number(item.get("duration")) for item in streams]
        duration = max((item for item in durations if item is not None), default=None)
    if duration is None or duration <= 0:
        raise ValueError(f"ffprobe did not report a positive duration for {path}")
    video = None
    if video_stream:
        video = {
            "index": video_stream.get("index"),
            "codec": video_stream.get("codec_name"),
            "width": video_stream.get("width"),
            "height": video_stream.get("height"),
            "fps": _fps(video_stream.get("avg_frame_rate") or video_stream.get("r_frame_rate")),
        }
    audio = None
    if audio_stream:
        audio = {
            "index": audio_stream.get("index"),
            "codec": audio_stream.get("codec_name"),
            "sample_rate": (
                int(audio_stream["sample_rate"])
                if str(audio_stream.get("sample_rate", "")).isdigit()
                else None
            ),
            "channels": audio_stream.get("channels"),
        }
    return {"duration_seconds": duration, "video": video, "audio": audio}
