import json
import tempfile
import unittest
from pathlib import Path

from voice.cli import load_profiles, plan_batch


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


if __name__ == "__main__":
    unittest.main()

