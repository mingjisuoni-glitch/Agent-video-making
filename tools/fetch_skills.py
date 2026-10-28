"""Validate and inspect the external Skill manifest without cloning unknown code."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def validate_manifest(manifest: dict) -> list[str]:
    problems: list[str] = []
    skills = manifest.get("skills")
    if not isinstance(skills, dict):
        return ["manifest.skills must be an object"]
    for name, entry in skills.items():
        if not isinstance(entry, dict):
            problems.append(f"{name}: entry must be an object")
            continue
        source = entry.get("source")
        if not isinstance(source, dict):
            problems.append(f"{name}: source is required")
        elif source.get("type") == "git":
            if not source.get("repo"):
                problems.append(f"{name}: git source.repo is required")
            if not re.fullmatch(r"[0-9a-fA-F]{40}", str(source.get("commit", ""))):
                problems.append(f"{name}: git source must pin a 40-character commit")
        if not entry.get("license"):
            problems.append(f"{name}: license is required")
    return problems


def _candidate_roots() -> list[Path]:
    home = Path.home()
    return [home / ".agents" / "skills", home / ".codex" / "skills"]


def inspect_manifest(manifest: dict) -> list[dict]:
    results: list[dict] = []
    for name, entry in manifest["skills"].items():
        installed = next((root / name for root in _candidate_roots() if (root / name / "SKILL.md").is_file()), None)
        state = "ok" if installed else ("fail" if entry.get("required") else "warn")
        results.append({
            "name": name,
            "state": state,
            "required": bool(entry.get("required")),
            "installed_path": str(installed) if installed else None,
            "license": entry["license"],
            "source": entry["source"],
        })
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check declared external Skills")
    parser.add_argument("--manifest", type=Path, default=Path("skills/manifest.json"))
    parser.add_argument("--check", action="store_true", help="Check installation without changing it")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    problems = validate_manifest(manifest)
    results = [] if problems else inspect_manifest(manifest)
    code = 1 if problems or any(item["state"] == "fail" for item in results) else 0
    payload = {"ok": code == 0, "manifest_problems": problems, "skills": results}
    if args.json:
        print(json.dumps(payload, ensure_ascii=False))
    else:
        for problem in problems:
            print(f"[fail] {problem}")
        for item in results:
            source = item["source"].get("repo") or item["source"].get("name", "manual")
            print(f"[{item['state']:>4}] {item['name']:<24} {source} | {item['license']}")
        if any(item["license"] == "CHECK_BEFORE_USE" for item in results):
            print("[warn] CHECK_BEFORE_USE entries require a separate license review before installation or redistribution.")
    return code


if __name__ == "__main__":
    raise SystemExit(main())

