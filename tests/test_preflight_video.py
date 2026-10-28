import json
import tempfile
import unittest
import wave
from pathlib import Path

from tools import preflight_video


def write_wav(path: Path, duration: float = 2.0, sample_rate: int = 8000) -> None:
    with wave.open(str(path), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(sample_rate)
        audio.writeframes(b"\x00\x00" * round(duration * sample_rate))


def write_evidence(root: Path, captions: list[dict] | None = None) -> None:
    captions = captions or []
    (root / "creative.json").write_text('{"reviewed":true}', encoding="utf-8")
    (root / "captions.json").write_text(json.dumps(captions), encoding="utf-8")
    (root / "no-audio.json").write_text('{"mode":"none","locked":true}', encoding="utf-8")


def valid_plan(groups: int = 0) -> dict:
    evidence = {"ok": True, "evidence": "creative.json"}
    return {
        "ratio": "9:16",
        "resolution": "1080x1920",
        "duration_seconds": 12,
        "fps": 30,
        "total_frames": 360,
        "style": {"id": "minimal-product", "confirmed": True},
        "voice": {"mode": "none", "confirmed": True},
        "approval": {"plan_approved": True},
        "creative_checks": {
            "no_static_card_sequence": dict(evidence),
            "action_per_narrative_unit": dict(evidence),
            "motivated_transitions": dict(evidence),
            "captions_synced_to_final_audio": {
                "ok": True, "evidence": "captions.json", "groups": groups,
            },
            "license_reviewed": dict(evidence),
            "layered_assets_ready": dict(evidence),
            "three_state_shots": dict(evidence),
            "final_audio_locked": {"ok": True, "evidence": "no-audio.json"},
        },
    }


class PreflightTests(unittest.TestCase):
    def _validate_file(self, root: Path, plan: dict, checks: dict | None = None) -> list[str]:
        plan_path = root / "plan.json"
        plan_path.write_text(json.dumps(plan), encoding="utf-8")
        checks_path = None
        if checks is not None:
            checks_path = root / "checks.json"
            checks_path.write_text(json.dumps(checks), encoding="utf-8")
        _, problems = preflight_video.load_and_validate_plan(plan_path, checks_path=checks_path)
        return problems

    def test_valid_plan_with_parseable_evidence_passes(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            write_evidence(root)
            self.assertEqual(self._validate_file(root, valid_plan()), [])

    def test_schema_rejects_zero_resolution_noninteger_fps_and_missing_voice_id(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            write_evidence(root)
            plan = valid_plan()
            plan.update({"resolution": "0x0", "fps": 29.97})
            plan["voice"] = {"mode": "qwen3-local", "confirmed": True}
            problems = self._validate_file(root, plan)
            self.assertTrue(any("resolution" in item for item in problems))
            self.assertTrue(any("fps" in item for item in problems))
            self.assertTrue(any("voice_id" in item for item in problems))

    def test_ratio_and_total_frames_are_semantic_rules(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            write_evidence(root)
            plan = valid_plan()
            plan.update({"resolution": "1920x1080", "total_frames": 359})
            problems = self._validate_file(root, plan)
            self.assertTrue(any("does not match" in item for item in problems))
            self.assertTrue(any("total_frames" in item for item in problems))

    def test_missing_or_unparseable_evidence_blocks_render(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            write_evidence(root)
            plan = valid_plan()
            plan["creative_checks"]["motivated_transitions"]["evidence"] = "missing.json"
            (root / "creative.json").write_text("not-json", encoding="utf-8")
            problems = self._validate_file(root, plan)
            self.assertTrue(any("missing.json" in item for item in problems))
            self.assertTrue(any("creative.json" in item and "parse" in item for item in problems))

    def test_caption_group_count_must_match_file(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            write_evidence(root, [{"text": "one", "start": 0, "end": 1, "over_limit": False}])
            problems = self._validate_file(root, valid_plan(groups=2))
            self.assertTrue(any("groups" in item for item in problems))

    def test_caption_duration_over_103_percent_of_audio_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            captions = [{"text": "late", "start": 0, "end": 2.08, "over_limit": False}]
            write_evidence(root, captions)
            audio = root / "final.wav"
            write_wav(audio, duration=2.0)
            plan = valid_plan(groups=1)
            plan["voice"] = {"mode": "qwen3-local", "voice_id": "demo", "confirmed": True}
            plan["creative_checks"]["final_audio_locked"]["evidence"] = "final.wav"
            problems = self._validate_file(root, plan)
            self.assertTrue(any("103%" in item for item in problems))

    def test_caption_evidence_requires_numeric_ordered_boundaries(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            write_evidence(root, [{"text": "bad", "start": "later", "end": 1}])
            write_wav(root / "final.wav", duration=2.0)
            plan = valid_plan(groups=1)
            plan["voice"] = {"mode": "qwen3-local", "voice_id": "demo", "confirmed": True}
            plan["creative_checks"]["final_audio_locked"]["evidence"] = "final.wav"
            problems = self._validate_file(root, plan)
            self.assertTrue(any("caption group 1" in item for item in problems))

    def test_hyperframes_report_must_be_strict_complete_and_browser_checked(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            write_evidence(root)
            for report in (
                {"ok": False, "strict": True, "browserSkipped": False},
                {"ok": True, "strict": False, "browserSkipped": False},
                {"ok": True, "strict": True, "browserSkipped": True},
            ):
                problems = self._validate_file(root, valid_plan(), report)
                self.assertTrue(any("HyperFrames" in item for item in problems))

    def test_hyperframes_strict_report_passes(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            write_evidence(root)
            report = {"ok": True, "strict": True, "browserSkipped": False}
            self.assertEqual(self._validate_file(root, valid_plan(), report), [])


if __name__ == "__main__":
    unittest.main()
