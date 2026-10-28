"""Validate and inspect the external Skill manifest without cloning unknown code."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path


SOURCE_TYPES = {"git", "platform", "local-only"}
AVAILABILITY_TYPES = {"public-git", "platform-builtin", "private-plugin", "local-only"}


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
        else:
            source_type = source.get("type")
            if source_type not in SOURCE_TYPES:
                problems.append(f"{name}: source.type must be one of {sorted(SOURCE_TYPES)}")
            elif source_type == "git":
                if not source.get("repo"):
                    problems.append(f"{name}: git source.repo is required")
                if not source.get("skill_path"):
                    problems.append(f"{name}: git source.skill_path is required")
                if not re.fullmatch(r"[0-9a-fA-F]{40}", str(source.get("commit", ""))):
                    problems.append(f"{name}: git source must pin a 40-character commit")
                if not re.fullmatch(r"[0-9a-fA-F]{64}", str(source.get("skill_sha256", ""))):
                    problems.append(f"{name}: git source must pin a 64-character skill_sha256")
            elif source_type == "platform":
                if not source.get("platform"):
                    problems.append(f"{name}: platform source.platform is required")
                if not source.get("documentation_url"):
                    problems.append(f"{name}: platform source.documentation_url is required")
            elif source_type == "local-only":
                if not source.get("name"):
                    problems.append(f"{name}: local-only source.name is required")
                if not entry.get("alternative"):
                    problems.append(f"{name}: local-only source requires an alternative or explanation")
        if entry.get("availability") not in AVAILABILITY_TYPES:
            problems.append(f"{name}: availability must be one of {sorted(AVAILABILITY_TYPES)}")
        if not entry.get("install_hint"):
            problems.append(f"{name}: install_hint is required")
        if not entry.get("license"):
            problems.append(f"{name}: license is required")
        installed_paths = entry.get("installed_paths", [name])
        if not isinstance(installed_paths, list) or not installed_paths:
            problems.append(f"{name}: installed_paths must be a non-empty array when provided")
        else:
            for installed_path in installed_paths:
                path = Path(str(installed_path))
                if path.is_absolute() or ".." in path.parts:
                    problems.append(f"{name}: installed_paths entries must be safe relative paths")
    return problems


def _candidate_roots() -> list[Path]:
    home = Path.home()
    configured = [Path(item) for item in os.environ.get("AVM_SKILL_ROOTS", "").split(os.pathsep) if item]
    return configured + [home / ".agents" / "skills", home / ".codex" / "skills"]


def inspect_manifest(manifest: dict, roots: list[Path] | None = None) -> list[dict]:
    roots = roots or _candidate_roots()
    results: list[dict] = []
    for name, entry in manifest["skills"].items():
        relative_paths = [Path(item) for item in entry.get("installed_paths", [name])]
        installed = next(
            (
                root / relative_path
                for root in roots
                for relative_path in relative_paths
                if (root / relative_path / "SKILL.md").is_file()
            ),
            None,
        )
        state = "ok" if installed else ("fail" if entry.get("required") else "warn")
        detail = None
        expected_hash = entry["source"].get("skill_sha256")
        if installed and expected_hash:
            actual_hash = hashlib.sha256((installed / "SKILL.md").read_bytes()).hexdigest()
            if actual_hash.lower() != expected_hash.lower():
                state = "fail" if entry.get("required") else "warn"
                detail = f"SKILL.md hash mismatch: expected {expected_hash}, got {actual_hash}"
        results.append({
            "name": name,
            "state": state,
            "required": bool(entry.get("required")),
            "availability": entry["availability"],
            "installed_path": str(installed) if installed else None,
            "license": entry["license"],
            "source": entry["source"],
            "install_hint": entry["install_hint"],
            "detail": detail,
        })
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check declared external Skills")
    parser.add_argument("--manifest", type=Path, default=Path("skills/manifest.json"))
    parser.add_argument("--check", action="store_true", help="Check installation without changing it")
    parser.add_argument("--validate-only", action="store_true", help="Validate manifest pins without inspecting installed Skills")
    parser.add_argument("--root", action="append", type=Path, help="Additional Skill root (repeatable)")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    problems = validate_manifest(manifest)
    roots = (args.root or []) + _candidate_roots()
    results = [] if problems or args.validate_only else inspect_manifest(manifest, roots)
    code = 1 if problems or any(item["state"] == "fail" for item in results) else 0
    payload = {"ok": code == 0, "manifest_problems": problems, "skills": results}
    if args.json:
        print(json.dumps(payload, ensure_ascii=False))
    else:
        for problem in problems:
            print(f"[fail] {problem}")
        for item in results:
            source = (
                item["source"].get("repo")
                or item["source"].get("documentation_url")
                or item["source"].get("name", "manual")
            )
            print(
                f"[{item['state']:>4}] {item['name']:<24} "
                f"{item['availability']} | {source} | {item['license']}"
            )
            if item["detail"]:
                print(f"       detail: {item['detail']}")
            if item["state"] != "ok":
                print(f"       install: {item['install_hint']}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())

