"""Turn final-audio word timestamps into one caption per natural pause."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path


PAUSE_GAP = 0.28
MAX_CHARS = 18
_CJK = re.compile(r"[\u3400-\u9fff]")


def _join_tokens(tokens: list[str]) -> str:
    text = ""
    for token in tokens:
        token = token.strip()
        if not token:
            continue
        if text and not (_CJK.search(text[-1]) or _CJK.search(token[0]) or token[0] in "，。！？；：、,.!?;:"):
            text += " "
        text += token
    return text


def group_words(words: list[dict], pause_gap: float = PAUSE_GAP, max_chars: int = MAX_CHARS) -> list[dict]:
    if not words:
        return []
    groups: list[dict] = []
    current: list[dict] = []
    for word in words:
        text = str(word.get("text", "")).strip()
        if not text or text in {"♪", "�"}:
            continue
        normalized = {"text": text, "start": float(word["start"]), "end": float(word["end"])}
        if current and normalized["start"] - current[-1]["end"] >= pause_gap:
            caption = _join_tokens([item["text"] for item in current])
            groups.append({
                "text": caption,
                "start": current[0]["start"],
                "end": current[-1]["end"],
                "over_limit": len(caption) > max_chars,
            })
            current = []
        current.append(normalized)
    if current:
        caption = _join_tokens([item["text"] for item in current])
        groups.append({
            "text": caption,
            "start": current[0]["start"],
            "end": current[-1]["end"],
            "over_limit": len(caption) > max_chars,
        })
    return groups


def _srt_time(seconds: float) -> str:
    milliseconds = max(0, round(seconds * 1000))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"


def format_srt(groups: list[dict]) -> str:
    blocks = [
        f"{index}\n{_srt_time(item['start'])} --> {_srt_time(item['end'])}\n{item['text']}"
        for index, item in enumerate(groups, start=1)
    ]
    return "\n\n".join(blocks) + ("\n" if blocks else "")


def _load_words(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        payload = payload.get("words", [])
    if not isinstance(payload, list):
        raise ValueError("transcript must be a word array or an object containing words")
    return payload


def transcribe(audio: Path, model: str, language: str | None) -> list[dict]:
    command = ["npx", "hyperframes", "transcribe", str(audio), "--model", model, "--json"]
    if language:
        command.extend(["--language", language])
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    payload = json.loads(completed.stdout)
    return payload.get("words", payload) if isinstance(payload, dict) else payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate pause-grouped captions from final audio")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--audio", type=Path)
    source.add_argument("--transcript", type=Path)
    parser.add_argument("--model", default="small", help="Use a multilingual model for Chinese; never rely on small.en")
    parser.add_argument("--language", default="zh")
    parser.add_argument("--pause-gap", type=float, default=PAUSE_GAP)
    parser.add_argument("--max-chars", type=int, default=MAX_CHARS)
    parser.add_argument("--json-output", type=Path, default=Path("captions.json"))
    parser.add_argument("--srt-output", type=Path, default=Path("captions.srt"))
    args = parser.parse_args(argv)
    words = transcribe(args.audio, args.model, args.language) if args.audio else _load_words(args.transcript)
    groups = group_words(words, args.pause_gap, args.max_chars)
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.srt_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(groups, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.srt_output.write_text(format_srt(groups), encoding="utf-8")
    long_groups = sum(bool(item["over_limit"]) for item in groups)
    print(json.dumps({"groups": len(groups), "over_limit": long_groups}, ensure_ascii=False))
    return 2 if long_groups else 0


if __name__ == "__main__":
    raise SystemExit(main())
