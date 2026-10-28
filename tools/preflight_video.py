"""Artifact-backed render gate for approved video plans."""

from __future__ import annotations

import argparse
import json
from math import gcd
from pathlib import Path

from jsonschema import Draft202012Validator

from tools.artifacts import probe_media

REQUIRED_CREATIVE_CHECKS = (
    "no_static_card_sequence",
    "action_per_narrative_unit",
    "motivated_transitions",
    "captions_synced_to_final_audio",
    "license_reviewed",
    "layered_assets_ready",
    "three_state_shots",
    "final_audio_locked",
)
DEFAULT_SCHEMA = Path(__file__).resolve().parents[1] / "video.schema.json"


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _schema_problems(plan: dict, schema: dict) -> list[str]:
    problems = []
    for error in sorted(Draft202012Validator(schema).iter_errors(plan), key=lambda item: list(item.path)):
        location = ".".join(str(part) for part in error.absolute_path) or "plan"
        problems.append(f"{location}: {error.message}")
    return problems


def _evidence_path(base_dir: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else base_dir / path


def _media_duration(path: Path) -> float | None:
    try:
        return float(probe_media(path)["duration_seconds"])
    except (OSError, TypeError, ValueError):
        return None


def _parse_json_evidence(path: Path, label: str, problems: list[str]):
    if not path.is_file():
        problems.append(f"{label} evidence does not exist: {path}")
        return None
    try:
        return _json(path)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        problems.append(f"{label} evidence cannot be parsed as JSON ({path}): {error}")
        return None


def validate_plan(plan: dict, base_dir: Path, check_report: dict | None = None) -> list[str]:
    """Run semantic and artifact checks after JSON Schema validation."""
    problems: list[str] = []
    width, height = (int(value) for value in plan["resolution"].split("x"))
    divisor = gcd(width, height)
    actual_ratio = f"{width // divisor}:{height // divisor}"
    if actual_ratio != plan["ratio"]:
        problems.append(f"ratio {plan['ratio']} does not match resolution {plan['resolution']}")
    expected_frames = round(plan["duration_seconds"] * plan["fps"])
    if plan["total_frames"] != expected_frames:
        problems.append(
            f"total_frames must equal round(duration_seconds * fps): expected {expected_frames}"
        )

    checks = plan["creative_checks"]
    parsed_evidence: dict[str, object] = {}
    for key in REQUIRED_CREATIVE_CHECKS:
        path = _evidence_path(base_dir, checks[key]["evidence"])
        if key == "final_audio_locked" and plan["voice"]["mode"] != "none":
            if not path.is_file():
                problems.append(f"creative_checks.{key} evidence does not exist: {path}")
            elif not (_media_duration(path) or 0) > 0:
                problems.append(f"creative_checks.{key} evidence is not readable audio: {path}")
            parsed_evidence[key] = path
        else:
            parsed_evidence[key] = _parse_json_evidence(
                path, f"creative_checks.{key}", problems
            )

    captions = parsed_evidence.get("captions_synced_to_final_audio")
    caption_check = checks["captions_synced_to_final_audio"]
    if isinstance(captions, list):
        if caption_check["groups"] != len(captions):
            problems.append(
                "creative_checks.captions_synced_to_final_audio.groups "
                f"is {caption_check['groups']} but evidence contains {len(captions)} groups"
            )
        if plan["voice"]["mode"] == "none" and captions:
            problems.append("voice.mode=none requires zero caption groups")
        caption_ends = []
        previous_end = 0.0
        for index, item in enumerate(captions, start=1):
            try:
                if not isinstance(item, dict):
                    raise TypeError
                start = float(item["start"])
                end = float(item["end"])
                if start < previous_end or end <= start:
                    raise ValueError
            except (KeyError, TypeError, ValueError):
                problems.append(
                    f"caption group {index} requires numeric, ordered, positive start/end"
                )
                continue
            caption_ends.append(end)
            previous_end = end
        if plan["voice"]["mode"] != "none" and caption_ends:
            audio_path = parsed_evidence.get("final_audio_locked")
            audio_duration = _media_duration(audio_path) if isinstance(audio_path, Path) else None
            caption_end = max(caption_ends)
            if audio_duration and caption_end > audio_duration * 1.03:
                problems.append(
                    f"caption duration {caption_end:.3f}s exceeds 103% of final audio "
                    f"duration {audio_duration:.3f}s"
                )

    no_audio = parsed_evidence.get("final_audio_locked")
    if (
        plan["voice"]["mode"] == "none"
        and isinstance(no_audio, dict)
        and (no_audio.get("mode") != "none" or no_audio.get("locked") is not True)
    ):
        problems.append("final_audio_locked evidence must declare mode=none and locked=true")

    if check_report is not None and not (
        check_report.get("ok") is True
        and check_report.get("strict") is True
        and check_report.get("browserSkipped") is False
    ):
        problems.append("HyperFrames report must have ok=true, strict=true, browserSkipped=false")
    return problems


def load_and_validate_plan(
    plan_path: Path,
    schema_path: Path | None = None,
    checks_path: Path | None = None,
) -> tuple[dict, list[str]]:
    """Load a plan, validate its schema, then validate artifact evidence."""
    try:
        plan = _json(plan_path)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        return {}, [f"plan cannot be parsed as JSON ({plan_path}): {error}"]
    try:
        schema = _json(schema_path or DEFAULT_SCHEMA)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        return plan, [f"schema cannot be parsed as JSON: {error}"]
    problems = _schema_problems(plan, schema)
    if problems:
        return plan, problems
    check_report = None
    if checks_path is not None:
        try:
            check_report = _json(checks_path)
        except (OSError, ValueError, json.JSONDecodeError) as error:
            return plan, [f"HyperFrames report cannot be parsed ({checks_path}): {error}"]
    problems.extend(validate_plan(plan, plan_path.resolve().parent, check_report))
    return plan, problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Block render until approvals and evidence are valid")
    parser.add_argument("plan", type=Path)
    parser.add_argument("--schema", type=Path)
    parser.add_argument("--with-checks", type=Path, help="HyperFrames structured check report")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    _, problems = load_and_validate_plan(args.plan, args.schema, args.with_checks)
    if args.json:
        print(json.dumps({"ok": not problems, "problems": problems}, ensure_ascii=False))
    elif problems:
        for problem in problems:
            print(f"[fail] {problem}")
    else:
        print("[ ok ] video plan approvals and artifact evidence are valid")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
