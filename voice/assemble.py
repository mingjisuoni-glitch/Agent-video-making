"""Assemble audio, pause-grouped captions, and scenes into HyperFrames."""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
from pathlib import Path

from tools.artifacts import probe_media

HYPERFRAMES_VERSION = "0.8.210"
GSAP_VERSION = "3.14.2"
_SCENE_ID = re.compile(r"^[a-z][a-z0-9-]*$")


def _seconds(value: float) -> str:
    return f"{value:.6f}".rstrip("0").rstrip(".") or "0"


def _load_object(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"{path.name} must contain a JSON object")
    return payload


def _load_captions(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise TypeError("captions must contain a JSON array")
    previous_end = 0.0
    captions = []
    for index, item in enumerate(payload, start=1):
        if not isinstance(item, dict) or not str(item.get("text", "")).strip():
            raise ValueError(f"caption group {index} requires nonempty text")
        try:
            start, end = float(item["start"]), float(item["end"])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f"caption group {index} requires numeric start/end") from error
        if start < previous_end or end <= start:
            raise ValueError("caption groups must be ordered, non-overlapping, and positive")
        captions.append({**item, "text": str(item["text"]).strip(), "start": start, "end": end})
        previous_end = end
    return captions


def _scene_windows(captions: list[dict], scenes: list[dict], duration: float) -> list[dict]:
    if len(captions) < len(scenes):
        raise ValueError("caption groups must be at least the number of scenes")
    boundaries = [0]
    for index in range(1, len(scenes)):
        boundary = round(index * len(captions) / len(scenes))
        boundaries.append(boundary)
    boundaries.append(len(captions))
    windows = []
    for index, scene in enumerate(scenes):
        start = 0.0 if index == 0 else captions[boundaries[index]]["start"]
        end = duration if index == len(scenes) - 1 else captions[boundaries[index + 1]]["start"]
        if end <= start:
            raise ValueError("caption group boundaries do not produce positive scene durations")
        windows.append({**scene, "start": start, "duration": end - start})
    return windows


def _validate_config(config: dict) -> tuple[dict, list[dict]]:
    canvas = config.get("canvas")
    scenes = config.get("scenes")
    if not isinstance(canvas, dict):
        raise TypeError("canvas must be an object")
    for key in ("width", "height", "fps"):
        if isinstance(canvas.get(key), bool) or not isinstance(canvas.get(key), int) or canvas[key] <= 0:
            raise ValueError(f"canvas.{key} must be a positive integer")
    ratio = canvas.get("ratio")
    if not isinstance(ratio, str) or not re.fullmatch(r"[1-9][0-9]*:[1-9][0-9]*", ratio):
        raise ValueError("canvas.ratio must use positive W:H integers")
    if not isinstance(scenes, list) or not scenes:
        raise ValueError("scenes must be a nonempty array")
    seen = set()
    normalized = []
    for index, scene in enumerate(scenes, start=1):
        if not isinstance(scene, dict):
            raise TypeError(f"scene {index} must be an object")
        scene_id = scene.get("id")
        if not isinstance(scene_id, str) or not _SCENE_ID.fullmatch(scene_id) or scene_id in seen:
            raise ValueError(f"scene {index} needs a unique lowercase id")
        if not all(isinstance(scene.get(key), str) and scene[key].strip() for key in ("carrier", "source")):
            raise ValueError(f"scene {scene_id} requires nonempty carrier and source strings")
        seen.add(scene_id)
        normalized.append({
            "id": scene_id,
            "carrier": scene["carrier"].strip(),
            "source": scene["source"].strip(),
        })
    return canvas, normalized


def _subcomposition(scene: dict, width: int, height: int) -> str:
    scene_id = scene["id"]
    carrier = html.escape(scene["carrier"])
    source = html.escape(scene["source"])
    duration = _seconds(scene["duration"])
    return f'''<!doctype html><html><body><template>
<style>
#root{{position:absolute;inset:0;width:100%;height:100%;overflow:hidden;background:#0b1424;color:#f6fbff;font-family:system-ui,sans-serif}}
#{scene_id}-glow{{position:absolute;width:46%;aspect-ratio:1;border-radius:50%;left:7%;top:12%;background:radial-gradient(circle,#2dd4bf66,transparent 68%)}}
#{scene_id}-content{{position:absolute;left:8%;right:8%;top:17%;bottom:17%;border:1px solid #ffffff24;border-radius:40px;padding:7%;background:#13233cdd;box-shadow:0 30px 90px #0006;display:flex;flex-direction:column;justify-content:center}}
#{scene_id}-carrier{{font-size:clamp(24px,3.2vw,54px);letter-spacing:.18em;text-transform:uppercase;color:#5eead4;font-weight:750}}
#{scene_id}-source{{margin-top:4%;font-size:clamp(48px,6vw,108px);line-height:1.08;font-weight:780;max-width:92%}}
#{scene_id}-pulse{{position:absolute;right:9%;bottom:12%;width:18%;height:10px;border-radius:99px;background:#fbbf24;transform-origin:left center}}
</style>
<div id="root" data-composition-id="{scene_id}" data-duration="{duration}" data-width="{width}" data-height="{height}">
  <div id="{scene_id}-glow"></div>
  <div id="{scene_id}-content"><div id="{scene_id}-carrier">{carrier}</div><div id="{scene_id}-source">{source}</div><div id="{scene_id}-pulse"></div></div>
</div>
<script>
const tl=gsap.timeline({{paused:true,defaults:{{ease:"power3.out"}}}});
tl.fromTo("#{scene_id}-content",{{opacity:1,y:52,scale:.96}},{{opacity:1,y:0,scale:1,duration:.72}},0)
  .fromTo("#{scene_id}-carrier",{{opacity:.65,x:-34}},{{opacity:1,x:0,duration:.48}},.18)
  .fromTo("#{scene_id}-source",{{opacity:.25,y:30}},{{opacity:1,y:0,duration:.66}},.32)
  .fromTo("#{scene_id}-pulse",{{scaleX:.08}},{{scaleX:1,duration:{max(scene['duration'] - 0.4, 0.4):.3f},ease:"none"}},.2)
  .to("#{scene_id}-glow",{{x:180,y:70,scale:1.18,duration:{max(scene['duration'] - 0.2, 0.5):.3f},ease:"sine.inOut"}},0);
window.__timelines["{scene_id}"]=tl;
</script>
</template></body></html>
'''


def _motion(scene: dict) -> dict:
    scene_id = scene["id"]
    return {
        "duration": scene["duration"],
        "assertions": [
            {"kind": "staysInFrame", "selector": f"#{scene_id}-content"},
            {"kind": "keepsMoving", "withinSelector": "#root", "maxStaticSec": 2.0},
        ],
    }


def _index(config: dict, canvas: dict, captions: list[dict], scenes: list[dict], audio_name: str, duration: float, total_frames: int) -> str:
    width, height = canvas["width"], canvas["height"]
    scene_hosts = "\n".join(
        f'<div id="scene-{item["id"]}" class="clip" data-composition-id="{item["id"]}" '
        f'data-composition-src="compositions/{item["id"]}.html" data-start="{_seconds(item["start"])}" '
        f'data-duration="{_seconds(item["duration"])}" data-track-index="1" data-track-kind="graphics" '
        f'data-width="{width}" data-height="{height}"></div>'
        for item in scenes
    )
    caption_nodes = "\n".join(
        f'<div id="caption-{index}" class="clip caption" data-start="{_seconds(item["start"])}" '
        f'data-duration="{_seconds(item["end"] - item["start"])}" data-track-index="2" '
        f'data-track-kind="captions"><span>{html.escape(item["text"])}</span></div>'
        for index, item in enumerate(captions, start=1)
    )
    return f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="UTF-8"/><meta name="viewport" content="width={width}, height={height}"/>
<script src="node_modules/gsap/dist/gsap.min.js"></script><style>
*{{box-sizing:border-box}}html,body{{margin:0;width:100%;height:100%;overflow:hidden;background:#0b1424}}#root{{position:relative;width:100%;height:100%;overflow:hidden}}.clip{{position:absolute}}[data-track-kind="graphics"]{{inset:0;width:100%;height:100%}}.caption{{left:9%;right:9%;bottom:7%;z-index:20;text-align:center;pointer-events:none}}.caption span{{display:inline-block;max-width:100%;padding:.22em .45em;color:#fff;font:700 clamp(30px,3.2vw,58px)/1.3 system-ui,sans-serif;text-shadow:0 3px 12px #000,0 0 3px #000}}
</style></head><body>
<div id="root" data-composition-id="main" data-start="0" data-duration="{_seconds(duration)}" data-total-frames="{total_frames}" data-width="{width}" data-height="{height}">
<audio id="voiceover" src="assets/{html.escape(audio_name)}" data-start="0" data-duration="{_seconds(duration)}" data-track-index="0" data-track-kind="audio" data-volume="1"></audio>
{scene_hosts}
{caption_nodes}
</div><script>const tl=gsap.timeline({{paused:true}});window.__timelines["main"]=tl;</script></body></html>
'''


def build_project(config_path: Path, output_dir: Path, probe=probe_media) -> dict:
    config_path = config_path.resolve()
    base_dir = config_path.parent
    config = _load_object(config_path)
    canvas, scenes = _validate_config(config)
    for key in ("audio", "captions"):
        if not isinstance(config.get(key), str) or not config[key].strip():
            raise ValueError(f"{key} must be a nonempty path")
    audio_path = (base_dir / config["audio"]).resolve()
    captions_path = (base_dir / config["captions"]).resolve()
    if not audio_path.is_file() or not captions_path.is_file():
        raise FileNotFoundError("audio and captions files must exist")
    duration = float(probe(audio_path)["duration_seconds"])
    if duration <= 0:
        raise ValueError("audio must have a positive duration")
    captions = _load_captions(captions_path)
    if captions and captions[-1]["end"] > duration * 1.03:
        raise ValueError("captions extend beyond 103% of the audio duration")
    windows = _scene_windows(captions, scenes, duration)
    total_frames = round(duration * canvas["fps"])
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"output directory is not empty: {output_dir}")
    compositions = output_dir / "compositions"
    assets = output_dir / "assets"
    compositions.mkdir(parents=True, exist_ok=True)
    assets.mkdir(parents=True, exist_ok=True)
    audio_target = assets / audio_path.name
    shutil.copy2(audio_path, audio_target)
    (output_dir / "index.html").write_text(
        _index(config, canvas, captions, windows, audio_target.name, duration, total_frames), encoding="utf-8"
    )
    for scene in windows:
        (compositions / f"{scene['id']}.html").write_text(
            _subcomposition(scene, canvas["width"], canvas["height"]), encoding="utf-8"
        )
        (compositions / f"{scene['id']}.motion.json").write_text(
            json.dumps(_motion(scene), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    package = {
        "name": output_dir.name.lower().replace("_", "-"),
        "private": True,
        "type": "module",
        "scripts": {
            "check": "hyperframes check --strict",
            "render": "hyperframes render --quality delivery --output out/video.mp4",
        },
        "dependencies": {"gsap": GSAP_VERSION},
        "devDependencies": {"hyperframes": HYPERFRAMES_VERSION},
    }
    (output_dir / "package.json").write_text(json.dumps(package, indent=2) + "\n", encoding="utf-8")
    (output_dir / "hyperframes.json").write_text(json.dumps({
        "$schema": "https://hyperframes.heygen.com/schema/hyperframes.json",
        "paths": {"blocks": "compositions", "assets": "assets"},
        "authoringSkill": "general-video",
    }, indent=2) + "\n", encoding="utf-8")
    (output_dir / "meta.json").write_text(json.dumps({
        "id": output_dir.name, "name": output_dir.name,
    }, indent=2) + "\n", encoding="utf-8")
    result = {
        "duration_seconds": duration,
        "total_frames": total_frames,
        "fps": canvas["fps"],
        "scenes": [
            {"id": item["id"], "start": item["start"], "duration": item["duration"]}
            for item in windows
        ],
        "audio": str(audio_target.relative_to(output_dir)),
        "captions": len(captions),
    }
    (output_dir / "build.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a HyperFrames project from audio and captions")
    parser.add_argument("scenes", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = build_project(args.scenes, args.out)
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as error:
        parser.error(str(error))
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
