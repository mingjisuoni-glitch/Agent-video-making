"""Build an evidence-backed delivery manifest from final artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.artifacts import probe_media, sha256_file, write_json_atomic
from tools.doctor import environment_snapshot


def _load_object(path: Path, label: str) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"{label} is unreadable: {path}: {error}") from error
    if not isinstance(payload, dict):
        raise TypeError(f"{label} must contain a JSON object: {path}")
    return payload


def _load_array(path: Path, label: str) -> list:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"{label} is unreadable: {path}: {error}") from error
    if not isinstance(payload, list):
        raise TypeError(f"{label} must contain a JSON array: {path}")
    return payload


def _require_files(paths: dict[str, Path]) -> None:
    missing = [f"{name}: {path}" for name, path in paths.items() if not path.is_file()]
    if missing:
        raise FileNotFoundError("missing required input(s): " + "; ".join(missing))


def _require_keys(payload: dict, label: str, keys: tuple[str, ...]) -> None:
    missing = [key for key in keys if payload.get(key) in (None, "")]
    if missing:
        raise ValueError(f"{label} is missing required field(s): {', '.join(missing)}")


def _discover_checks(video: Path) -> Path:
    candidates: list[Path] = []
    for parent in (video.parent, *video.parents[:4]):
        folder = parent / ".hyperframes" / "artifacts" / "checks"
        if folder.is_dir():
            candidates.extend(path for path in folder.glob("*.json") if path.is_file())
    candidates = list(dict.fromkeys(path.resolve() for path in candidates))
    if not candidates:
        raise FileNotFoundError("no HyperFrames check report found; pass --checks explicitly")
    newest_ns = max(path.stat().st_mtime_ns for path in candidates)
    newest = [path for path in candidates if path.stat().st_mtime_ns == newest_ns]
    if len(newest) != 1:
        raise ValueError("ambiguous newest HyperFrames check report; pass --checks explicitly")
    return newest[0]


def _skill_snapshot(payload: dict) -> list[dict]:
    raw = payload.get("skills")
    if not isinstance(raw, dict):
        raise TypeError("skills manifest must contain a skills object")
    snapshots = []
    for skill_id, item in sorted(raw.items()):
        source = item.get("source") if isinstance(item, dict) else None
        if not isinstance(source, dict):
            raise TypeError(f"skill {skill_id} is missing source provenance")
        snapshots.append({
            "id": skill_id,
            "commit": source.get("commit") or source.get("reference_commit"),
            "sha256": source.get("skill_sha256") or source.get("reference_skill_sha256"),
            "availability": item.get("availability"),
        })
    return snapshots


def build_delivery_manifest(
    *,
    plan: Path,
    video: Path,
    audio: Path,
    captions: Path,
    checks: Path | None,
    skills: Path,
    root: Path,
    probe=probe_media,
    environment=environment_snapshot,
) -> dict:
    plan, video, audio, captions, skills = (
        Path(path).resolve() for path in (plan, video, audio, captions, skills)
    )
    checks = Path(checks).resolve() if checks is not None else _discover_checks(video)
    audio_sidecar = Path(f"{audio}.avm.json")
    caption_sidecar = Path(f"{captions}.avm.json")
    _require_files({
        "plan": plan,
        "video": video,
        "audio": audio,
        "captions": captions,
        "audio provenance": audio_sidecar,
        "caption provenance": caption_sidecar,
        "HyperFrames checks": checks,
        "skills manifest": skills,
    })

    plan_payload = _load_object(plan, "plan")
    check_payload = _load_object(checks, "HyperFrames checks")
    audio_provenance = _load_object(audio_sidecar, "audio provenance")
    caption_provenance = _load_object(caption_sidecar, "caption provenance")
    skill_payload = _load_object(skills, "skills manifest")
    caption_groups = _load_array(captions, "captions")

    _require_keys(
        audio_provenance,
        "audio provenance",
        ("provider", "speaker", "voice_id", "audio_sha256", "duration_seconds", "runtime"),
    )
    _require_keys(
        caption_provenance,
        "caption provenance",
        ("groups", "over_limit", "transcript_sha256", "captions_sha256"),
    )

    actual_audio_hash = sha256_file(audio)
    if audio_provenance.get("audio_sha256") != actual_audio_hash:
        raise ValueError("audio provenance hash does not match the delivered audio")
    actual_caption_hash = sha256_file(captions)
    if caption_provenance.get("captions_sha256") != actual_caption_hash:
        raise ValueError("captions provenance hash does not match the delivered captions")
    actual_over_limit = sum(bool(item.get("over_limit")) for item in caption_groups if isinstance(item, dict))
    if caption_provenance.get("groups") != len(caption_groups):
        raise ValueError("captions provenance group count does not match the delivered captions")
    if caption_provenance.get("over_limit") != actual_over_limit:
        raise ValueError("captions provenance over-limit count does not match the delivered captions")

    video_probe = probe(video)
    if not isinstance(video_probe.get("video"), dict):
        raise TypeError("delivered video has no readable video stream")
    stream = video_probe["video"]
    audio_probe = probe(audio)
    actual_audio_duration = float(audio_probe["duration_seconds"])
    if abs(float(audio_provenance["duration_seconds"]) - actual_audio_duration) >= 0.05:
        raise ValueError("audio provenance duration does not match the delivered audio")
    runtime = audio_provenance.get("runtime")
    if not isinstance(runtime, dict):
        raise TypeError("audio provenance is missing runtime/model details")

    return {
        "schema_version": 1,
        "plan": {
            "sha256": sha256_file(plan),
            "data": plan_payload,
        },
        "video": {
            "sha256": sha256_file(video),
            "duration": video_probe["duration_seconds"],
            "fps": stream.get("fps"),
            "width": stream.get("width"),
            "height": stream.get("height"),
            "codec": stream.get("codec"),
        },
        "audio": {
            "sha256": actual_audio_hash,
            "duration": actual_audio_duration,
            "provider": audio_provenance.get("provider"),
            "speaker": audio_provenance.get("speaker"),
            "voice_id": audio_provenance.get("voice_id"),
            "model_sha256": runtime.get("model_sha256"),
            "head_sha256": runtime.get("head_sha256"),
            "runtime": runtime,
        },
        "captions": {
            "sha256": actual_caption_hash,
            "groups": len(caption_groups),
            "over_limit": actual_over_limit,
            "transcript_sha256": caption_provenance.get("transcript_sha256"),
        },
        "checks": {"hyperframes": check_payload},
        "env": environment(Path(root)),
        "skills": _skill_snapshot(skill_payload),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a delivery manifest from final artifacts")
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--audio", type=Path, required=True)
    parser.add_argument("--captions", type=Path, required=True)
    parser.add_argument("--checks", type=Path)
    parser.add_argument("--skills", type=Path, default=Path("skills/manifest.json"))
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("-o", "--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        manifest = build_delivery_manifest(
            plan=args.plan,
            video=args.video,
            audio=args.audio,
            captions=args.captions,
            checks=args.checks,
            skills=args.skills,
            root=args.root,
        )
    except (FileNotFoundError, OSError, TypeError, ValueError, json.JSONDecodeError) as error:
        parser.error(str(error))
    write_json_atomic(args.output, manifest)
    print(json.dumps({"ok": True, "output": str(args.output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
