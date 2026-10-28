import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.doctor import (
    Check,
    environment_snapshot,
    exit_code_for,
    inspect_qwen_model,
    parse_node_major,
)


def write_fake_safetensors(path: Path, data_bytes: int) -> None:
    header = json.dumps({
        "weight": {"dtype": "U8", "shape": [data_bytes], "data_offsets": [0, data_bytes]}
    }, separators=(",", ":")).encode("utf-8")
    header += b" " * (-len(header) % 8)
    with path.open("wb") as weights:
        weights.write(len(header).to_bytes(8, "little"))
        weights.write(header)
        weights.truncate(weights.tell() + data_bytes)


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
            self.assertIn("safetensors", check.detail.lower())

    def test_qwen_model_requires_exact_custom_voice_type(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "config.json").write_text("{}", encoding="utf-8")
            write_fake_safetensors(root / "model.safetensors", 101 * 1024 * 1024)
            self.assertEqual(inspect_qwen_model(root).state, "fail")

    def test_qwen_model_rejects_large_file_without_safetensors_header(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "config.json").write_text(
                '{"tts_model_type":"custom_voice"}', encoding="utf-8"
            )
            with (root / "model.safetensors").open("wb") as weights:
                weights.truncate(101 * 1024 * 1024)
            check = inspect_qwen_model(root)
            self.assertEqual(check.state, "fail")
            self.assertIn("header", check.detail)

    def test_qwen_model_rejects_unknown_safetensors_dtype(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "config.json").write_text(
                '{"tts_model_type":"custom_voice"}', encoding="utf-8"
            )
            data_bytes = 101 * 1024 * 1024
            header = json.dumps({
                "weight": {
                    "dtype": "NOT_A_DTYPE", "shape": [data_bytes],
                    "data_offsets": [0, data_bytes],
                }
            }, separators=(",", ":")).encode("utf-8")
            header += b" " * (-len(header) % 8)
            path = root / "model.safetensors"
            with path.open("wb") as weights:
                weights.write(len(header).to_bytes(8, "little"))
                weights.write(header)
                weights.truncate(weights.tell() + data_bytes)
            self.assertEqual(inspect_qwen_model(root).state, "fail")

    def test_qwen_model_rejects_shape_offset_byte_mismatch(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "config.json").write_text(
                '{"tts_model_type":"custom_voice"}', encoding="utf-8"
            )
            data_bytes = 101 * 1024 * 1024
            header = json.dumps({
                "weight": {
                    "dtype": "F32", "shape": [data_bytes],
                    "data_offsets": [0, data_bytes],
                }
            }, separators=(",", ":")).encode("utf-8")
            header += b" " * (-len(header) % 8)
            path = root / "model.safetensors"
            with path.open("wb") as weights:
                weights.write(len(header).to_bytes(8, "little"))
                weights.write(header)
                weights.truncate(weights.tell() + data_bytes)
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
            write_fake_safetensors(
                root / "model-00001-of-00002.safetensors", 101 * 1024 * 1024
            )
            self.assertEqual(inspect_qwen_model(root).state, "fail")

    def test_environment_snapshot_captures_runtime_versions(self):
        def command(args, _root):
            values = {
                "node": "v22.1.0",
                "npx": "0.8.210",
            }
            return 0, values.get(Path(args[0]).stem, "0.8.210")

        with patch("tools.doctor._command", side_effect=command), patch(
            "tools.doctor._package_version", return_value="0.1.1"
        ):
            snapshot = environment_snapshot(Path.cwd())
        self.assertEqual(snapshot["node"], "v22.1.0")
        self.assertEqual(snapshot["hyperframes"], "0.8.210")
        self.assertEqual(snapshot["qwen-tts"], "0.1.1")
        self.assertIn("python", snapshot)


if __name__ == "__main__":
    unittest.main()

