import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from voice.cli import (
    _duration_seconds,
    execute_batch,
    file_sha256,
    load_profiles,
    plan_batch,
    segment_fingerprint,
)
from voice.contracts import SynthesisResult, VoiceSpec


class VoiceCliFeatureTests(unittest.TestCase):
    def test_invalid_wav_has_no_duration(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bad.wav"
            path.write_bytes(b"not a wav")
            self.assertIsNone(_duration_seconds(path))

    def test_listable_profiles_keep_provider_and_display_name(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "voices.json"
            path.write_text(json.dumps({"voices": {"demo": {
                "provider": "qwen3-local", "speaker": "Vivian", "display_name": "清晰"
            }}}), encoding="utf-8")
            profiles = load_profiles(path)
            self.assertEqual(profiles["demo"].speaker, "Vivian")
            self.assertEqual(profiles["demo"].display_name, "清晰")

    def test_resume_only_skips_output_with_matching_fingerprint(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            complete = root / "001.wav"
            complete.write_bytes(b"RIFFaudio")
            rows = [{"id": "001", "text": "第一句", "output": str(complete)}]
            spec = VoiceSpec("qwen3-local", "Vivian")
            Path(f"{complete}.avm.json").write_text(json.dumps({
                "fingerprint": segment_fingerprint(rows[0], "demo", spec),
                "audio_sha256": file_sha256(complete),
            }), encoding="utf-8")
            report = execute_batch(
                plan_batch(rows, resume=True), {"demo": spec}, "demo", False,
                provider_factory=lambda _spec: self.fail("provider should not run"),
                duration_reader=lambda _path: 1.25, resume=True,
            )
            self.assertEqual(report[0]["status"], "skipped")
            self.assertEqual(report[0]["duration_seconds"], 1.25)

    def test_resume_rejects_tampered_audio(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "001.wav"
            output.write_bytes(b"original")
            row = {"id": "001", "text": "same", "output": str(output)}
            spec = VoiceSpec("qwen3-local", "Vivian")
            Path(f"{output}.avm.json").write_text(json.dumps({
                "fingerprint": segment_fingerprint(row, "demo", spec),
                "audio_sha256": file_sha256(output),
            }), encoding="utf-8")
            output.write_bytes(b"tampered")

            class FakeProvider:
                def synthesize(self, _text, voice, path):
                    path.write_bytes(b"regenerated")
                    return SynthesisResult(path, voice.provider, voice.speaker, "wav", 24000)

            report = execute_batch(
                [row], {"demo": spec}, "demo", False, lambda _spec: FakeProvider(),
                lambda _path: 1.0, resume=True,
            )
            self.assertEqual(report[0]["status"], "completed")

    def test_resume_regenerates_stale_output(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "001.wav"
            output.write_bytes(b"old")
            row = {"id": "001", "text": "new text", "output": str(output)}
            spec = VoiceSpec("qwen3-local", "Vivian")

            class FakeProvider:
                def synthesize(self, _text, voice, path):
                    path.write_bytes(b"new")
                    return SynthesisResult(path, voice.provider, voice.speaker, "wav", 24000)

            report = execute_batch(
                [row], {"demo": spec}, "demo", False, lambda _spec: FakeProvider(),
                lambda _path: 1.0, resume=True,
            )
            self.assertEqual(report[0]["status"], "completed")
            self.assertTrue(Path(f"{output}.avm.json").is_file())

    def test_qwen_model_provenance_changes_segment_fingerprint(self):
        with tempfile.TemporaryDirectory() as folder:
            model_dir = Path(folder)
            config = model_dir / "config.json"
            row = {"id": "001", "text": "same", "output": "001.wav"}
            spec = VoiceSpec("qwen3-local", "Vivian")
            with patch.dict(os.environ, {"QWEN3_TTS_MODEL_DIR": str(model_dir)}):
                config.write_text('{"revision":1}', encoding="utf-8")
                first = segment_fingerprint(row, "demo", spec)
                config.write_text('{"revision":2}', encoding="utf-8")
                second = segment_fingerprint(row, "demo", spec)
            self.assertNotEqual(first, second)

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

