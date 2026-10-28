import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "examples" / "voiced-demo"


class VoicedDemoContractTests(unittest.TestCase):
    def test_demo_inputs_define_three_caption_boundary_scenes(self):
        config = json.loads((DEMO / "scenes.json").read_text(encoding="utf-8"))
        transcript = json.loads((DEMO / "transcript.json").read_text(encoding="utf-8"))

        self.assertEqual(len(config["scenes"]), 3)
        self.assertEqual(config["audio"], "build/final.wav")
        self.assertEqual(config["captions"], "build/captions.json")
        self.assertGreaterEqual(len(transcript["words"]), 6)
        self.assertLessEqual(max(word["end"] for word in transcript["words"]), 20.0)

    def test_audio_script_pins_exact_twenty_seconds_without_committing_audio(self):
        script = (DEMO / "scripts" / "make-audio.sh").read_text(encoding="utf-8")

        self.assertIn("espeak-ng", script)
        self.assertIn("-t 20", script)
        self.assertIn("ffprobe", script)
        self.assertIn("abs(duration - 20.0) < 0.01", script)

    def test_build_script_requires_generated_project_and_clean_strict_report(self):
        script = (DEMO / "scripts" / "build.sh").read_text(encoding="utf-8")
        caption_script = (DEMO / "scripts" / "make-captions.sh").read_text(encoding="utf-8")

        self.assertIn("avm-captions", caption_script)
        self.assertIn("avm-assemble", script)
        self.assertIn('$generated_dir/index.html', script)
        self.assertIn("npm run --silent check", script)
        self.assertIn("report['strict'] is True", script)
        self.assertIn("report['ok'] is True", script)
        self.assertIn("report['errors'] == 0", script)
        self.assertIn("report['warnings'] == 0", script)

    def test_generated_demo_artifacts_are_ignored(self):
        ignored = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("examples/voiced-demo/build/", ignored)
        self.assertIn("examples/voiced-demo/generated/", ignored)


if __name__ == "__main__":
    unittest.main()
