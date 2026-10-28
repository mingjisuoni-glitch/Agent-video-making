"""Small, stable contract between a video workflow and a TTS backend."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class VoiceSpec:
    provider: str
    speaker: str
    display_name: str = ""
    language: str = "Chinese"
    resource_id: str | None = None
    speech_rate: int = 0
    instruct: str = ""
    seed: int = 43101


@dataclass(frozen=True)
class SynthesisResult:
    path: Path
    provider: str
    speaker: str
    audio_format: str
    sample_rate: int

