import json
import tempfile
import unittest
from pathlib import Path

from voice.cli import execute_batch, load_profiles, plan_batch
from voice.contracts import SynthesisResult, VoiceSpec


class VoiceCliFeatureTests(unittest.TestCase):
    def test_listable_profiles_keep_provider_and_display_name(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "voices.json"
            path.write_text(json.dumps({"voices": {"demo": {
                "provider": "qwen3-local", "speaker": "Vivian", "display_name": "清晰"
            }}}), encoding="utf-8")
            profiles = load_profiles(path)
            self.assertEqual(profiles["demo"].speaker, "Vivian")
            self.assertEqual(profiles["demo"].display_name, "清晰")

    def test_batch_plan_skips_completed_outputs_when_resuming(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            complete = root / "001.wav"
            complete.write_bytes(b"done")
            rows = [
                {"id": "001", "text": "第一句", "output": str(complete)},
                {"id": "002", "text": "第二句", "output": str(root / "002.wav")},
            ]
            planned = plan_batch(rows, resume=True)
            self.assertEqual([item["id"] for item in planned], ["002"])

    def test_batch_reuses_one_provider_for_the_same_voice(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            created = []

            class FakeProvider:
                def synthesize(self, _text, spec, output):
                    output.write_bytes(b"audio")
                    return SynthesisResult(output, spec.provider, spec.speaker, "wav", 24000)

            def factory(_spec):
                created.append(object())
                return FakeProvider()

            rows = [
                {"id": "001", "text": "第一句", "output": str(root / "001.wav")},
                {"id": "002", "text": "第二句", "output": str(root / "002.wav")},
            ]
            profiles = {"demo": VoiceSpec("qwen3-local", "Vivian")}
            report = execute_batch(rows, profiles, "demo", False, factory, lambda _path: 1.0)
            self.assertEqual(len(created), 1)
            self.assertEqual([item["status"] for item in report], ["completed", "completed"])


if __name__ == "__main__":
    unittest.main()

