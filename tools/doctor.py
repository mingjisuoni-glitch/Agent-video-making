"""New-machine diagnostics for the Agent Video Making method kit."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class Check:
    name: str
    state: str
    detail: str


def parse_node_major(version: str) -> int | None:
    token = version.strip().lstrip("v").split(".", 1)[0]
    return int(token) if token.isdigit() else None


def _command(command: list[str], cwd: Path) -> tuple[int, str]:
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return 127, str(error)
    output = (completed.stdout or completed.stderr).strip()
    return completed.returncode, output


def inspect_qwen_model(model_dir: Path | None) -> Check:
    if model_dir is None:
        return Check("Qwen3-TTS model", "warn", "QWEN3_TTS_MODEL_DIR is unset; local TTS is optional")
    config = model_dir / "config.json"
    weights = list(model_dir.glob("*.safetensors"))
    if not config.is_file() or not weights:
        return Check("Qwen3-TTS model", "fail", "config.json or safetensors weights are missing")
    try:
        payload = json.loads(config.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return Check("Qwen3-TTS model", "fail", "config.json is unreadable or invalid")
    if payload.get("tts_model_type") not in (None, "custom_voice"):
        return Check("Qwen3-TTS model", "fail", "configured model is not CustomVoice")
    total_bytes = sum(path.stat().st_size for path in weights)
    if total_bytes < 100 * 1024 * 1024:
        return Check("Qwen3-TTS model", "fail", "model weights look incomplete (<100 MB)")
    return Check("Qwen3-TTS model", "ok", f"{model_dir} ({total_bytes / 1024**3:.1f} GB weights)")


def _voice_profiles(root: Path) -> Check:
    path = root / "voices.example.json"
    try:
        voices = json.loads(path.read_text(encoding="utf-8"))["voices"]
        if not isinstance(voices, dict) or not voices:
            raise ValueError("no profiles")
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        return Check("Voice profiles", "fail", f"invalid {path.name}: {error}")
    return Check("Voice profiles", "ok", f"{len(voices)} profiles")


def run_checks(root: Path) -> list[Check]:
    checks: list[Check] = []
    py_ok = sys.version_info >= (3, 10)
    checks.append(Check("Python", "ok" if py_ok else "fail", sys.version.split()[0] + " (requires >=3.10)"))

    node_code, node_text = _command(["node", "--version"], root)
    node_major = parse_node_major(node_text) if node_code == 0 else None
    checks.append(Check(
        "Node.js",
        "ok" if node_major is not None and node_major >= 22 else "fail",
        node_text or "not found; HyperFrames requires Node >=22",
    ))

    npx_path = shutil.which("npx")
    checks.append(Check("npx", "ok" if npx_path else "fail", npx_path or "not found"))
    if npx_path:
        code, text = _command([npx_path, "--yes", "--offline", "hyperframes@0.8.210", "--version"], root)
        checks.append(Check(
            "HyperFrames CLI",
            "ok" if code == 0 else "warn",
            text or "not cached; run npx hyperframes@0.8.210 doctor once while online",
        ))
    else:
        checks.append(Check("HyperFrames CLI", "fail", "npx is unavailable"))

    ffmpeg_code, ffmpeg_text = _command(["ffmpeg", "-version"], root)
    checks.append(Check(
        "ffmpeg",
        "ok" if ffmpeg_code == 0 else "fail",
        (ffmpeg_text.splitlines() or ["not found"])[0],
    ))

    free_gb = shutil.disk_usage(root).free / 1024**3
    disk_state = "ok" if free_gb >= 8 else ("warn" if free_gb >= 2 else "fail")
    checks.append(Check("Disk", disk_state, f"{free_gb:.1f} GB free; local TTS needs several GB"))

    configured_model = os.environ.get("QWEN3_TTS_MODEL_DIR")
    checks.append(inspect_qwen_model(Path(configured_model) if configured_model else None))
    has_cloud = bool(os.environ.get("VOLC_API_KEY") or (
        os.environ.get("VOLC_APP_ID") and os.environ.get("VOLC_ACCESS_KEY")
    ))
    checks.append(Check(
        "Volcano credentials",
        "ok" if has_cloud else "warn",
        "configured" if has_cloud else "unset; cloud TTS is optional",
    ))
    checks.append(_voice_profiles(root))

    test_code, test_text = _command([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-q"], root)
    summary = (test_text.splitlines() or ["no output"])[-1]
    checks.append(Check("Offline tests", "ok" if test_code == 0 else "fail", summary))
    return checks


def exit_code_for(checks: list[Check]) -> int:
    return 1 if any(item.state == "fail" for item in checks) else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check a new machine before using the project")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    checks = run_checks(args.root.resolve())
    code = exit_code_for(checks)
    if args.json:
        print(json.dumps({"ok": code == 0, "checks": [asdict(item) for item in checks]}, ensure_ascii=False))
    else:
        for item in checks:
            print(f"[{item.state:>4}] {item.name:<24} {item.detail}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())

