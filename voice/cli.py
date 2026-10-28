"""CLI for one approved narration segment and one named voice profile."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
from dataclasses import asdict
from pathlib import Path

from .contracts import VoiceSpec
from .providers import Qwen3LocalProvider, VolcanoProvider


def check_voice(spec: VoiceSpec) -> list[str]:
    """Check local configuration only; never contact a TTS service or load a model."""
    problems: list[str] = []
    if not spec.speaker.strip():
        problems.append("Configure a nonempty speaker in the voice profile")
    if spec.provider == "volcano":
        if not spec.resource_id:
            problems.append("Configure the Volcano resource_id for this voice")
        if not -50 <= spec.speech_rate <= 100:
            problems.append("Volcano speech_rate must be between -50 and 100")
        if spec.instruct:
            problems.append("This Volcano adapter does not support instruct")
        if not (os.environ.get("VOLC_API_KEY") or
                (os.environ.get("VOLC_APP_ID") and os.environ.get("VOLC_ACCESS_KEY"))):
            problems.append("Set VOLC_API_KEY, or VOLC_APP_ID and VOLC_ACCESS_KEY")
    elif spec.provider == "qwen3-local":
        if spec.speech_rate != 0:
            problems.append("Qwen3 CustomVoice has no numeric speech_rate control")
        model_dir = Path(os.environ.get("QWEN3_TTS_MODEL_DIR", ""))
        if not (model_dir / "model.safetensors").is_file():
            problems.append("Download a CustomVoice model and set QWEN3_TTS_MODEL_DIR")
        config_path = model_dir / "config.json"
        if config_path.is_file():
            try:
                config = json.loads(config_path.read_text(encoding="utf-8"))
                if config.get("tts_model_type") != "custom_voice":
                    problems.append("The model is not a Qwen3 CustomVoice model")
                if spec.instruct and config.get("tts_model_size") == "0b6":
                    problems.append("Qwen3 0.6B ignores instruct; use 1.7B or remove it")
            except (OSError, ValueError):
                problems.append("Qwen3 config.json is unreadable or invalid")
        else:
            problems.append("Qwen3 config.json is missing")
        for module in ("numpy", "soundfile", "torch", "qwen_tts"):
            if importlib.util.find_spec(module) is None:
                problems.append(f"Install the Python package providing {module}")
    else:
        problems.append(f"Unsupported provider: {spec.provider}")
    return problems


def main() -> None:
    parser = argparse.ArgumentParser(description="Synthesize an approved narration segment")
    parser.add_argument("--voices", type=Path, default=Path("voices.example.json"))
    parser.add_argument("--voice", required=True, help="Profile key in the voices JSON file")
    parser.add_argument("--check", action="store_true", help="Check local setup without synthesis")
    parser.add_argument("--text-file", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    profiles = json.loads(args.voices.read_text(encoding="utf-8"))["voices"]
    if args.voice not in profiles:
        parser.error(f"Unknown voice: {args.voice}")
    spec = VoiceSpec(**profiles[args.voice])
    if args.check:
        problems = check_voice(spec)
        print(json.dumps({"local_check_passed": not problems, "voice": args.voice, "problems": problems}, ensure_ascii=True))
        if problems:
            parser.exit(1)
        return
    if args.text_file is None or args.output is None:
        parser.error("--text-file and --output are required unless --check is used")
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

