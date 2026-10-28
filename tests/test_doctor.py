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


if __name__ == "__main__":
    unittest.main()

