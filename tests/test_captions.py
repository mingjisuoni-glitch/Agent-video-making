import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from voice.captions import format_srt, group_words, transcribe


class CaptionTests(unittest.TestCase):
    def test_groups_only_at_natural_pauses(self):
        words = [
            {"text": "先", "start": 0.0, "end": 0.2},
            {"text": "确认", "start": 0.22, "end": 0.6},
            {"text": "方案", "start": 0.92, "end": 1.3},
        ]
        groups = group_words(words, pause_gap=0.28, max_chars=18)
        self.assertEqual([item["text"] for item in groups], ["先确认", "方案"])
        self.assertEqual(groups[0]["end"], 0.6)

    def test_long_unpaused_phrase_is_flagged_not_arbitrarily_split(self):
        words = [
            {"text": char, "start": index * 0.1, "end": index * 0.1 + 0.08}
            for index, char in enumerate("这是一个没有自然停顿的超长字幕测试")
        ]
        groups = group_words(words, pause_gap=0.28, max_chars=8)
        self.assertEqual(len(groups), 1)
        self.assertTrue(groups[0]["over_limit"])

    def test_srt_uses_group_boundaries(self):
        srt = format_srt([{"text": "测试", "start": 1.0, "end": 2.25}])
        self.assertIn("00:00:01,000 --> 00:00:02,250", srt)
        self.assertTrue(srt.endswith("\n"))

    def test_transcribe_loads_words_from_hyperframes_sidecar(self):
        with tempfile.TemporaryDirectory() as folder:
            transcript = Path(folder) / "transcript.json"
            words = [{"text": "测试", "start": 0.0, "end": 0.4}]
            transcript.write_text(json.dumps(words), encoding="utf-8")
            completed = type("Completed", (), {
                "stdout": json.dumps({"ok": True, "wordCount": 1, "transcriptPath": str(transcript)})
            })()
            with patch("voice.captions.shutil.which", return_value="npx.cmd"), patch(
                "voice.captions.subprocess.run", return_value=completed
            ) as run:
                self.assertEqual(transcribe(Path("audio.wav"), "small", "zh"), words)
            self.assertEqual(
                run.call_args.args[0][:4],
                ["npx.cmd", "--yes", "--offline", "hyperframes@0.8.210"],
            )

    def test_transcribe_rejects_missing_transcript_path(self):
        completed = type("Completed", (), {"stdout": '{"ok":true,"wordCount":1}'})()
        with patch("voice.captions.shutil.which", return_value="npx"), patch(
            "voice.captions.subprocess.run", return_value=completed
        ), self.assertRaisesRegex(ValueError, "transcriptPath"):
            transcribe(Path("audio.wav"), "small", "zh")


if __name__ == "__main__":
    unittest.main()

