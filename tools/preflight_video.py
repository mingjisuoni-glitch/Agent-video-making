"""Machine gate for the four confirmations and creative delivery checks."""

from __future__ import annotations

import argparse
import json
import math
import re
from math import gcd
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
    ratio = plan.get("ratio")
    ratio_match = re.fullmatch(r"([1-9][0-9]*):([1-9][0-9]*)", ratio) if isinstance(ratio, str) else None
    if not ratio_match:
        problems.append("ratio must use positive W:H integers, for example 16:9")
    resolution = plan.get("resolution")
    resolution_match = re.fullmatch(r"([1-9][0-9]*)x([1-9][0-9]*)", resolution) if isinstance(resolution, str) else None
    if not resolution_match:
        problems.append("resolution must use positive WIDTHxHEIGHT integers")
    elif ratio_match:
        width, height = (int(value) for value in resolution_match.groups())
        divisor = gcd(width, height)
        actual_ratio = f"{width // divisor}:{height // divisor}"
        if actual_ratio != ratio:
            problems.append(f"ratio {ratio} does not match resolution {resolution}")
    for key in ("duration_seconds", "fps"):
        value = plan.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            problems.append(f"{key} must be a positive finite number")
    style = plan.get("style") if isinstance(plan.get("style"), dict) else {}
    style_id = style.get("id")
    if not isinstance(style_id, str) or not style_id.strip() or style.get("confirmed") is not True:
        problems.append("style.id and style.confirmed=true are required")
    voice = plan.get("voice") if isinstance(plan.get("voice"), dict) else {}
    if voice.get("mode") not in {"none", "volcano", "qwen3-local"}:
        problems.append("voice.mode must be none, volcano, or qwen3-local")
    if voice.get("confirmed") is not True:
        problems.append("voice.confirmed=true is required")
    if voice.get("mode") in {"volcano", "qwen3-local"}:
        voice_id = voice.get("voice_id")
        if not isinstance(voice_id, str) or not voice_id.strip():
            problems.append("voice.voice_id must be a nonempty string for a TTS backend")
    approval = plan.get("approval") if isinstance(plan.get("approval"), dict) else {}
    if approval.get("plan_approved") is not True:
        problems.append("approval.plan_approved must be true")
    checks = plan.get("creative_checks") if isinstance(plan.get("creative_checks"), dict) else {}
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

