import json
import tempfile
import unittest
from pathlib import Path

from voice import assemble


def captions() -> list[dict]:
    times = [(0.0, 1.1), (1.5, 3.8), (5.0, 7.0), (8.0, 10.5), (11.0, 15.0), (16.0, 19.5)]
    return [
        {"text": f"字幕 {index}", "start": start, "end": end, "over_limit": False}
        for index, (start, end) in enumerate(times, start=1)
    ]


def write_inputs(root: Path, group_count: int = 6) -> Path:
    (root / "final.wav").write_bytes(b"fake-audio")
    (root / "captions.json").write_text(
        json.dumps(captions()[:group_count], ensure_ascii=False), encoding="utf-8"
    )
    config = {
        "canvas": {"ratio": "16:9", "width": 1920, "height": 1080, "fps": 30},
        "style": {"id": "story-driven-explainer"},
        "audio": "final.wav",
        "captions": "captions.json",
        "scenes": [
            {"id": "evidence", "carrier": "证据", "source": "先看真实证据"},
            {"id": "action", "carrier": "行动", "source": "再把步骤连起来"},
            {"id": "result", "carrier": "结果", "source": "最后形成可交付结果"},
        ],
    }
    path = root / "scenes.json"
    path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")
    return path


class AssembleTests(unittest.TestCase):
    def test_build_uses_audio_duration_and_caption_boundary_scene_cuts(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            config = write_inputs(root)
            output = root / "generated"
            result = assemble.build_project(
                config, output,
                probe=lambda _path: {"duration_seconds": 20.0, "audio": {"codec": "pcm_s16le"}, "video": None},
            )
            self.assertEqual(result["duration_seconds"], 20.0)
            self.assertEqual(result["total_frames"], 600)
            self.assertEqual(
                [(item["start"], item["duration"]) for item in result["scenes"]],
                [(0.0, 5.0), (5.0, 6.0), (11.0, 9.0)],
            )
            index = (output / "index.html").read_text(encoding="utf-8")
            self.assertIn('data-duration="20"', index)
            self.assertIn('data-total-frames="600"', index)

    def test_generated_tracks_templates_timelines_and_motion_sidecars_are_valid(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            output = root / "generated"
            assemble.build_project(
                write_inputs(root), output,
                probe=lambda _path: {"duration_seconds": 20.0, "audio": {}, "video": None},
            )
            index = (output / "index.html").read_text(encoding="utf-8")
            self.assertIn('data-track-kind="captions"', index)
            self.assertIn('data-track-kind="graphics"', index)
            self.assertIn('id="voiceover"', index)
            self.assertIn('id="caption-1"', index)
            self.assertNotIn("Math.random", index)
            self.assertNotIn("Date.now", index)
            for scene_id in ("evidence", "action", "result"):
                html = (output / "compositions" / f"{scene_id}.html").read_text(encoding="utf-8")
                self.assertIn("<template>", html)
                self.assertIn(f'data-composition-id="{scene_id}"', html)
                self.assertIn("gsap.timeline({paused:true", html)
                self.assertIn(f'window.__timelines["{scene_id}"]', html)
                self.assertIn("{opacity:1,y:52,scale:.96}", html)
                self.assertNotIn("Math.random", html)
                self.assertNotIn("Date.now", html)
                motion = json.loads(
                    (output / "compositions" / f"{scene_id}.motion.json").read_text(encoding="utf-8")
                )
                kinds = {item["kind"] for item in motion["assertions"]}
                self.assertTrue({"keepsMoving", "staysInFrame"}.issubset(kinds))

    def test_fewer_caption_groups_than_scenes_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with self.assertRaisesRegex(ValueError, "caption groups"):
                assemble.build_project(
                    write_inputs(root, group_count=2), root / "generated",
                    probe=lambda _path: {"duration_seconds": 20.0, "audio": {}, "video": None},
                )


if __name__ == "__main__":
    unittest.main()
