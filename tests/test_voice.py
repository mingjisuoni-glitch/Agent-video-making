import base64
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from voice import Qwen3LocalProvider, VoiceSpec, VolcanoProvider
from voice.cli import check_voice
from voice.providers import has_model_weights


class FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def __iter__(self):
        payload = base64.b64encode(b"fake-audio").decode("ascii")
        return iter([f'{{"code":0,"data":"{payload}"}}\n'.encode(),
                     b'{"code":20000000,"message":"done"}\n'])


class VoiceProviderTests(unittest.TestCase):
    def test_cloud_preflight_requires_credentials_without_network_call(self):
        with patch.dict(os.environ, {}, clear=True):
            problems = check_voice(VoiceSpec("volcano", "voice-id", resource_id="seed-tts-2.0"))
        self.assertTrue(any("VOLC_API_KEY" in item for item in problems))

    def test_volcano_uses_new_key_and_writes_only_completed_audio(self):
        captured = {}

        def opener(request, timeout):
            captured["request"] = request
            captured["timeout"] = timeout
            return FakeResponse()

        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {"VOLC_API_KEY": "test-key"}):
            output = Path(folder) / "voice.mp3"
            result = VolcanoProvider(opener).synthesize(
                "测试", VoiceSpec("volcano", "voice-id", resource_id="seed-tts-2.0"), output
            )
            self.assertEqual(output.read_bytes(), b"fake-audio")
            self.assertEqual(result.audio_format, "mp3")
            self.assertEqual(captured["request"].get_header("X-api-key"), "test-key")

    def test_volcano_requires_explicit_resource_and_does_not_write_output(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "voice.mp3"
            with self.assertRaisesRegex(ValueError, "resource_id"):
                VolcanoProvider().synthesize("测试", VoiceSpec("volcano", "voice-id"), output)
            self.assertFalse(output.exists())

    def test_qwen_06b_rejects_ignored_style_instruction_before_model_load(self):
        with tempfile.TemporaryDirectory() as folder:
            model_dir = Path(folder) / "Qwen3-TTS-12Hz-0.6B-CustomVoice"
            model_dir.mkdir()
            with (model_dir / "model.safetensors").open("wb") as weights:
                weights.truncate(101 * 1024 * 1024)
            (model_dir / "config.json").write_text(
                '{"tts_model_type":"custom_voice","tts_model_size":"0b6"}', encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "ignores instruct"):
                Qwen3LocalProvider(model_dir).synthesize(
                    "测试", VoiceSpec("qwen3-local", "Dylan", instruct="激动"), Path(folder) / "voice.wav"
                )

    def test_qwen_rejects_unavailable_numeric_speed_control(self):
        with self.assertRaisesRegex(ValueError, "no numeric speech_rate"):
            Qwen3LocalProvider().synthesize(
                "测试", VoiceSpec("qwen3-local", "Dylan", speech_rate=10), Path("voice.wav")
            )

    def test_qwen_detects_sharded_safetensors_weights(self):
        with tempfile.TemporaryDirectory() as folder:
            model_dir = Path(folder)
            (model_dir / "config.json").write_text(
                '{"tts_model_type":"custom_voice"}', encoding="utf-8"
            )
            names = ["model-00001-of-00002.safetensors", "model-00002-of-00002.safetensors"]
            (model_dir / "model.safetensors.index.json").write_text(json.dumps({
                "weight_map": {"a": names[0], "b": names[1]}
            }), encoding="utf-8")
            for name in names:
                with (model_dir / name).open("wb") as weights:
                    weights.truncate(51 * 1024 * 1024)
            self.assertTrue(has_model_weights(model_dir))


if __name__ == "__main__":
    unittest.main()

