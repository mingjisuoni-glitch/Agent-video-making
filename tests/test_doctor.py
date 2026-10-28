import json
import tempfile
import unittest
from pathlib import Path

from tools.doctor import Check, exit_code_for, inspect_qwen_model, parse_node_major


class DoctorTests(unittest.TestCase):
    def test_node_major_parser_accepts_v_prefix(self):
        self.assertEqual(parse_node_major("v24.19.0"), 24)

    def test_json_mode_does_not_hide_failures(self):
        self.assertEqual(exit_code_for([Check("Node.js", "fail", "missing")]), 1)
        self.assertEqual(exit_code_for([Check("Qwen", "warn", "optional")]), 0)

    def test_qwen_model_rejects_placeholder_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "config.json").write_text(
                '{"tts_model_type":"custom_voice"}', encoding="utf-8"
            )
            (root / "model.safetensors").touch()
            check = inspect_qwen_model(root)
            self.assertEqual(check.state, "fail")
            self.assertIn("incomplete", check.detail.lower())

    def test_qwen_model_requires_exact_custom_voice_type(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "config.json").write_text("{}", encoding="utf-8")
            with (root / "model.safetensors").open("wb") as weights:
                weights.truncate(101 * 1024 * 1024)
            self.assertEqual(inspect_qwen_model(root).state, "fail")

    def test_qwen_model_rejects_missing_indexed_shard(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "config.json").write_text(
                '{"tts_model_type":"custom_voice"}', encoding="utf-8"
            )
            (root / "model.safetensors.index.json").write_text(json.dumps({
                "weight_map": {
                    "a": "model-00001-of-00002.safetensors",
                    "b": "model-00002-of-00002.safetensors",
                }
            }), encoding="utf-8")
            with (root / "model-00001-of-00002.safetensors").open("wb") as weights:
                weights.truncate(101 * 1024 * 1024)
            self.assertEqual(inspect_qwen_model(root).state, "fail")


if __name__ == "__main__":
    unittest.main()

