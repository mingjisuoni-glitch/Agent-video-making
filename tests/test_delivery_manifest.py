import json
import os
import tempfile
import unittest
from pathlib import Path

from tools import delivery_manifest
from tools.artifacts import sha256_file


class DeliveryManifestTests(unittest.TestCase):
    def make_inputs(self, root: Path) -> dict[str, Path]:
        paths = {
            "plan": root / "video-plan.json",
            "video": root / "out.mp4",
            "audio": root / "final.wav",
            "captions": root / "captions.json",
            "checks": root / "check.json",
            "skills": root / "skills.json",
        }
        paths["plan"].write_text('{"duration_seconds":12}', encoding="utf-8")
        paths["video"].write_bytes(b"video-bytes")
        paths["audio"].write_bytes(b"audio-bytes")
        captions = [
            {"text": "第一句", "start": 0, "end": 1, "over_limit": False},
            {"text": "第二句", "start": 2, "end": 3, "over_limit": True},
        ]
        paths["captions"].write_text(json.dumps(captions, ensure_ascii=False), encoding="utf-8")
        Path(f"{paths['audio']}.avm.json").write_text(json.dumps({
            "provider": "qwen3-local",
            "speaker": "Vivian",
            "voice_id": "demo",
            "audio_sha256": sha256_file(paths["audio"]),
            "duration_seconds": 3.0,
            "runtime": {"model_sha256": "a" * 64, "head_sha256": "b" * 64},
        }), encoding="utf-8")
        Path(f"{paths['captions']}.avm.json").write_text(json.dumps({
            "groups": 2,
            "over_limit": 1,
            "transcript_sha256": "c" * 64,
            "captions_sha256": sha256_file(paths["captions"]),
        }), encoding="utf-8")
        paths["checks"].write_text(json.dumps({
            "ok": True, "strict": True, "browserSkipped": False,
            "lint": {"ok": True}, "runtime": {"ok": True},
        }), encoding="utf-8")
        paths["skills"].write_text(json.dumps({"skills": {
            "hyperframes": {"source": {
                "commit": "deadbeef", "skill_sha256": "d" * 64,
            }}
        }}), encoding="utf-8")
        return paths

    def test_manifest_embeds_artifact_facts_provenance_checks_env_and_skills(self):
        with tempfile.TemporaryDirectory() as folder:
            paths = self.make_inputs(Path(folder))
            manifest = delivery_manifest.build_delivery_manifest(
                **paths,
                root=Path(folder),
                probe=lambda path: {
                    "duration_seconds": 12.0 if path == paths["video"] else 3.0,
                    "video": {
                        "fps": 30.0, "width": 1920, "height": 1080, "codec": "h264"
                    } if path == paths["video"] else None,
                    "audio": {"codec": "aac"},
                },
                environment=lambda _root: {
                    "python": "3.13", "node": "v22", "hyperframes": "0.8.210",
                    "qwen-tts": "0.1.1",
                },
            )
            self.assertEqual(manifest["video"]["sha256"], sha256_file(paths["video"]))
            self.assertEqual(manifest["video"]["fps"], 30.0)
            self.assertEqual(manifest["audio"]["speaker"], "Vivian")
            self.assertEqual(manifest["audio"]["model_sha256"], "a" * 64)
            self.assertEqual(manifest["captions"]["groups"], 2)
            self.assertEqual(manifest["captions"]["over_limit"], 1)
            self.assertTrue(manifest["checks"]["hyperframes"]["ok"])
            self.assertEqual(manifest["env"]["node"], "v22")
            self.assertEqual(manifest["skills"][0]["commit"], "deadbeef")

    def test_manifest_rejects_missing_input_or_provenance(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            paths = self.make_inputs(root)
            paths["audio"].unlink()
            with self.assertRaises(FileNotFoundError):
                delivery_manifest.build_delivery_manifest(**paths, root=root)

    def test_manifest_rejects_incomplete_audio_provenance(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            paths = self.make_inputs(root)
            sidecar_path = Path(f"{paths['audio']}.avm.json")
            sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
            sidecar.pop("provider")
            sidecar_path.write_text(json.dumps(sidecar), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "provider"):
                delivery_manifest.build_delivery_manifest(
                    **paths,
                    root=root,
                    probe=lambda path: {
                        "duration_seconds": 12.0 if path == paths["video"] else 3.0,
                        "video": {"fps": 30.0, "width": 1920, "height": 1080, "codec": "h264"}
                        if path == paths["video"] else None,
                        "audio": {"codec": "aac"},
                    },
                )

    def test_manifest_rejects_tampered_audio_and_captions(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            paths = self.make_inputs(root)
            paths["audio"].write_bytes(b"tampered")
            with self.assertRaisesRegex(ValueError, "audio.*hash"):
                delivery_manifest.build_delivery_manifest(**paths, root=root)
            paths = self.make_inputs(root)
            paths["captions"].write_text("[]", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "captions.*hash"):
                delivery_manifest.build_delivery_manifest(**paths, root=root)

    def test_check_discovery_selects_unique_newest_report(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            video = root / "out" / "video.mp4"
            checks = root / ".hyperframes" / "artifacts" / "checks"
            video.parent.mkdir()
            checks.mkdir(parents=True)
            video.write_bytes(b"video")
            old = checks / "old.json"
            new = checks / "new.json"
            old.write_text("{}", encoding="utf-8")
            new.write_text("{}", encoding="utf-8")
            os.utime(old, ns=(1_000_000_000, 1_000_000_000))
            os.utime(new, ns=(2_000_000_000, 2_000_000_000))
            self.assertEqual(delivery_manifest._discover_checks(video), new.resolve())

    def test_check_discovery_rejects_equal_newest_timestamps(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            video = root / "out" / "video.mp4"
            checks = root / ".hyperframes" / "artifacts" / "checks"
            video.parent.mkdir()
            checks.mkdir(parents=True)
            video.write_bytes(b"video")
            for name in ("one.json", "two.json"):
                report = checks / name
                report.write_text("{}", encoding="utf-8")
                os.utime(report, ns=(3_000_000_000, 3_000_000_000))
            with self.assertRaisesRegex(ValueError, "ambiguous"):
                delivery_manifest._discover_checks(video)


if __name__ == "__main__":
    unittest.main()
