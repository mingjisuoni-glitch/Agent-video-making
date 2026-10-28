"""Machine gate for the four confirmations and creative delivery checks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

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


def validate_plan(plan: dict) -> list[str]:
    problems: list[str] = []
    for key in ("ratio", "resolution", "duration_seconds", "fps"):
        if not plan.get(key):
            problems.append(f"{key} is required")
    style = plan.get("style") or {}
    if not style.get("id") or style.get("confirmed") is not True:
        problems.append("style.id and style.confirmed=true are required")
    voice = plan.get("voice") or {}
    if voice.get("mode") not in {"none", "volcano", "qwen3-local"}:
        problems.append("voice.mode must be none, volcano, or qwen3-local")
    if voice.get("confirmed") is not True:
        problems.append("voice.confirmed=true is required")
    if voice.get("mode") in {"volcano", "qwen3-local"} and not voice.get("voice_id"):
        problems.append("voice.voice_id is required for a TTS backend")
    if (plan.get("approval") or {}).get("plan_approved") is not True:
        problems.append("approval.plan_approved must be true")
    checks = plan.get("creative_checks") or {}
    for key in REQUIRED_CREATIVE_CHECKS:
        if checks.get(key) is not True:
            problems.append(f"creative_checks.{key} must be true")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Block render until the video plan is confirmed")
    parser.add_argument("plan", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    problems = validate_plan(plan)
    if args.json:
        print(json.dumps({"ok": not problems, "problems": problems}, ensure_ascii=False))
    elif problems:
        for problem in problems:
            print(f"[fail] {problem}")
    else:
        print("[ ok ] video plan is approved and all creative checks are recorded")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())

