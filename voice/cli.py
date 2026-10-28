"""CLI for one approved narration segment and one named voice profile."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from .contracts import VoiceSpec
from .providers import Qwen3LocalProvider, VolcanoProvider


def main() -> None:
    parser = argparse.ArgumentParser(description="Synthesize an approved narration segment")
    parser.add_argument("--voices", type=Path, default=Path("voices.example.json"))
    parser.add_argument("--voice", required=True, help="Profile key in the voices JSON file")
    parser.add_argument("--text-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    profiles = json.loads(args.voices.read_text(encoding="utf-8"))["voices"]
    if args.voice not in profiles:
        parser.error(f"Unknown voice: {args.voice}")
    spec = VoiceSpec(**profiles[args.voice])
    text = args.text_file.read_text(encoding="utf-8").strip()
    provider = {
        "volcano": VolcanoProvider,
        "qwen3-local": Qwen3LocalProvider,
    }.get(spec.provider)
    if provider is None:
        parser.error(f"Unsupported provider: {spec.provider}")
    result = provider().synthesize(text, spec, args.output)
    print(json.dumps({**asdict(result), "path": str(result.path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()

