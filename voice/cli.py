"""CLI for checked, resumable narration synthesis."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import wave
from dataclasses import asdict
from importlib import metadata
from pathlib import Path

from tools.artifacts import sha256_file, write_json_atomic

from .contracts import VoiceSpec
from .providers import Qwen3LocalProvider, VolcanoProvider, has_model_weights


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
        if not has_model_weights(model_dir):
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


def load_profiles(path: Path) -> dict[str, VoiceSpec]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw_profiles = payload.get("voices")
    if not isinstance(raw_profiles, dict) or not raw_profiles:
        raise ValueError("voices JSON must contain a nonempty 'voices' object")
    return {name: VoiceSpec(**entry) for name, entry in raw_profiles.items()}


def plan_batch(rows: list[dict], resume: bool) -> list[dict]:
    planned: list[dict] = []
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            raise TypeError(f"batch row {index} must be a JSON object")
        if not row.get("id") or not str(row.get("text", "")).strip() or not row.get("output"):
            raise ValueError(f"batch row {index} requires id, text, and output")
        planned.append(row)
    return planned


def file_sha256(path: Path, limit: int | None = None) -> str:
    return sha256_file(path, limit=limit)


def _package_version(name: str) -> str:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return "not-installed"


def _model_provenance(spec: VoiceSpec) -> dict:
    provenance = {
        "agent_video_making": _package_version("agent-video-making"),
        "provider": spec.provider,
    }
    if spec.provider != "qwen3-local":
        return provenance
    provenance["qwen_tts"] = _package_version("qwen-tts")
    configured = os.environ.get("QWEN3_TTS_MODEL_DIR")
    if not configured:
        provenance["model_dir"] = None
        return provenance
    model_dir = Path(configured).resolve()
    provenance["model_dir"] = str(model_dir)
    files = []
    for path in sorted([model_dir / "config.json", model_dir / "model.safetensors.index.json"] + list(model_dir.glob("*.safetensors"))):
        if path.is_file():
            stat = path.stat()
            files.append({
                "name": path.name,
                "size": stat.st_size,
                "mtime_ns": stat.st_mtime_ns,
                "head_sha256": file_sha256(path, limit=1024 * 1024),
                "sha256": file_sha256(path),
            })
    provenance["model_files"] = files
    for target, source in (("model_sha256", "sha256"), ("head_sha256", "head_sha256")):
        if files:
            joined = "\n".join(f"{item['name']}:{item[source]}" for item in files).encode("utf-8")
            provenance[target] = hashlib.sha256(joined).hexdigest()
        else:
            provenance[target] = None
    return provenance


def segment_fingerprint(
    row: dict, voice_id: str, spec: VoiceSpec, runtime: dict | None = None,
) -> str:
    payload = {
        "text": str(row["text"]).strip(),
        "voice_id": voice_id,
        "voice": asdict(spec),
        "runtime": runtime if runtime is not None else _model_provenance(spec),
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _resume_metadata(output: Path) -> Path:
    return Path(f"{output}.avm.json")


def _can_resume(output: Path, fingerprint: str, duration_reader) -> tuple[bool, float | None]:
    metadata = _resume_metadata(output)
    if not output.is_file() or output.stat().st_size <= 0 or not metadata.is_file():
        return False, None
    try:
        payload = json.loads(metadata.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False, None
    if payload.get("fingerprint") != fingerprint:
        return False, None
    expected_audio_hash = payload.get("audio_sha256")
    if not isinstance(expected_audio_hash, str) or file_sha256(output) != expected_audio_hash:
        return False, None
    duration = duration_reader(output)
    return duration is not None and duration > 0, duration


def _read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"invalid JSON on line {line_number}: {error}") from error
        rows.append(row)
    return rows


def _duration_seconds(path: Path) -> float | None:
    if path.suffix.lower() == ".wav":
        try:
            with wave.open(str(path), "rb") as audio:
                return audio.getnframes() / float(audio.getframerate())
        except (OSError, ValueError, ZeroDivisionError, wave.Error):
            return None
    try:
        completed = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nokey=1:noprint_wrappers=1", str(path)],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return float(completed.stdout.strip())
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def _provider(spec: VoiceSpec):
    provider_type = {"volcano": VolcanoProvider, "qwen3-local": Qwen3LocalProvider}.get(spec.provider)
    if provider_type is None:
        raise ValueError(f"Unsupported provider: {spec.provider}")
    return provider_type()


def _audio_metadata(
    output: Path,
    spec: VoiceSpec,
    voice_id: str,
    duration: float,
    runtime: dict,
    fingerprint: str,
) -> dict:
    return {
        "schema_version": 1,
        "kind": "audio",
        "provider": spec.provider,
        "speaker": spec.speaker,
        "voice_id": voice_id,
        "fingerprint": fingerprint,
        "audio_sha256": file_sha256(output),
        "duration_seconds": duration,
        "runtime": runtime,
    }


def _synthesize(
    text: str,
    spec: VoiceSpec,
    voice_id: str,
    output: Path,
    provider_factory=_provider,
    duration_reader=_duration_seconds,
) -> dict:
    runtime = _model_provenance(spec)
    fingerprint = segment_fingerprint({"text": text}, voice_id, spec, runtime)
    result = provider_factory(spec).synthesize(text, spec, output)
    duration = duration_reader(output)
    if duration is None or duration <= 0:
        raise ValueError(f"synthesized audio is unreadable or empty: {output}")
    write_json_atomic(
        _resume_metadata(output),
        _audio_metadata(output, spec, voice_id, duration, runtime, fingerprint),
    )
    return {**asdict(result), "path": str(result.path)}


def execute_batch(
    rows: list[dict],
    profiles: dict[str, VoiceSpec],
    default_voice: str | None,
    dry_run: bool,
    provider_factory=_provider,
    duration_reader=_duration_seconds,
    resume: bool = False,
) -> list[dict]:
    """Execute planned rows while reusing one loaded provider per voice profile."""
    providers: dict[str, object] = {}
    runtimes: dict[str, dict] = {}
    report: list[dict] = []
    for row in rows:
        voice_id = row.get("voice") or default_voice
        if not voice_id or voice_id not in profiles:
            raise ValueError(f"Unknown or missing voice for batch row {row['id']}")
        item = {"id": row["id"], "voice": voice_id, "output": row["output"], "status": "planned"}
        spec = profiles[voice_id]
        output = Path(row["output"])
        if voice_id not in runtimes:
            runtimes[voice_id] = _model_provenance(spec)
        runtime = runtimes[voice_id]
        fingerprint = segment_fingerprint(row, voice_id, spec, runtime)
        resumable, prior_duration = _can_resume(output, fingerprint, duration_reader) if resume else (False, None)
        if resumable:
            item.update({"status": "skipped", "duration_seconds": prior_duration, "fingerprint": fingerprint})
            report.append(item)
            continue
        if not dry_run:
            provider = providers.get(voice_id)
            if provider is None:
                provider = provider_factory(spec)
                providers[voice_id] = provider
            result = provider.synthesize(str(row["text"]).strip(), spec, output)
            duration = duration_reader(output)
            if duration is None or duration <= 0:
                raise ValueError(f"synthesized audio is unreadable or empty: {output}")
            write_json_atomic(
                _resume_metadata(output),
                _audio_metadata(output, spec, voice_id, duration, runtime, fingerprint),
            )
            item.update({
                "status": "completed",
                "result": {**asdict(result), "path": str(result.path)},
                "duration_seconds": duration,
                "fingerprint": fingerprint,
            })
        report.append(item)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Synthesize approved narration segments")
    parser.add_argument("--voices", type=Path, default=Path("voices.example.json"))
    parser.add_argument("--voice", help="Default profile key in the voices JSON file")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--list-voices", action="store_true")
    mode.add_argument("--check", action="store_true", help="Check local setup without synthesis")
    mode.add_argument("--batch", type=Path, help="JSONL rows with id, text, output, and optional voice")
    parser.add_argument("--text-file", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--resume", action="store_true",
        help="Skip only readable outputs whose text, voice, runtime/model, and audio hash still match",
    )
    parser.add_argument("--dry-run", action="store_true", help="Validate and print work without synthesis")
    parser.add_argument("--duration-report", nargs="?", const="duration-report.json", type=Path)
    args = parser.parse_args(argv)

    try:
        profiles = load_profiles(args.voices)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        parser.error(str(error))
    if args.resume and not args.batch:
        parser.error("--resume requires --batch")
    if args.list_voices:
        listing = [
            {"id": name, "provider": spec.provider, "speaker": spec.speaker, "display_name": spec.display_name}
            for name, spec in sorted(profiles.items())
        ]
        print(json.dumps(listing, ensure_ascii=False, indent=2))
        return 0

    if args.batch:
        try:
            rows = plan_batch(_read_jsonl(args.batch), args.resume)
        except (OSError, TypeError, ValueError) as error:
            parser.error(str(error))
        try:
            report = execute_batch(rows, profiles, args.voice, args.dry_run, resume=args.resume)
        except ValueError as error:
            parser.error(str(error))
        payload = {"dry_run": args.dry_run, "segments": report}
        if args.duration_report:
            args.duration_report.parent.mkdir(parents=True, exist_ok=True)
            args.duration_report.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(payload, ensure_ascii=False))
        return 0

    if not args.voice or args.voice not in profiles:
        parser.error("--voice is required and must name a configured profile")
    spec = profiles[args.voice]
    if args.check:
        problems = check_voice(spec)
        print(json.dumps({"local_check_passed": not problems, "voice": args.voice, "problems": problems}, ensure_ascii=True))
        return 1 if problems else 0
    if args.text_file is None or args.output is None:
        parser.error("--text-file and --output are required unless --check, --list-voices, or --batch is used")
    text = args.text_file.read_text(encoding="utf-8").strip()
    if args.dry_run:
        print(json.dumps({"dry_run": True, "voice": args.voice, "output": str(args.output), "characters": len(text)}))
        return 0
    result = _synthesize(text, spec, args.voice, args.output)
    if args.duration_report:
        payload = {"result": result, "duration_seconds": _duration_seconds(args.output)}
        args.duration_report.parent.mkdir(parents=True, exist_ok=True)
        args.duration_report.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
