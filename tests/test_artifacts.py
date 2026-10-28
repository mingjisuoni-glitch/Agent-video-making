import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools import artifacts


class ArtifactTests(unittest.TestCase):
    def test_sha256_file_supports_full_and_head_hashes(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "artifact.bin"
            path.write_bytes(b"abcdef")
            self.assertEqual(artifacts.sha256_file(path), hashlib.sha256(b"abcdef").hexdigest())
            self.assertEqual(artifacts.sha256_file(path, limit=3), hashlib.sha256(b"abc").hexdigest())

    def test_probe_media_normalizes_fractional_fps_and_selects_video_stream(self):
        payload = {
            "format": {"duration": "12.034"},
            "streams": [
                {"index": 0, "codec_type": "audio", "codec_name": "aac", "sample_rate": "48000"},
                {
                    "index": 1,
                    "codec_type": "video",
                    "codec_name": "h264",
                    "width": 1920,
                    "height": 1080,
                    "avg_frame_rate": "30000/1001",
                    "duration": "12.000",
                },
            ],
        }
        completed = type("Completed", (), {"stdout": json.dumps(payload)})()
        result = artifacts.probe_media(Path("movie.mp4"), runner=lambda *args, **kwargs: completed)
        self.assertEqual(result["duration_seconds"], 12.034)
        self.assertAlmostEqual(result["video"]["fps"], 30000 / 1001)
        self.assertEqual(result["video"]["codec"], "h264")
        self.assertEqual((result["video"]["width"], result["video"]["height"]), (1920, 1080))
        self.assertEqual(result["audio"]["codec"], "aac")

    def test_probe_media_rejects_unreadable_media(self):
        def failing_runner(*_args, **_kwargs):
            raise subprocess.CalledProcessError(1, ["ffprobe"], stderr="invalid data")

        with self.assertRaisesRegex(ValueError, "ffprobe"):
            artifacts.probe_media(Path("bad.mp4"), runner=failing_runner)

    def test_probe_media_decodes_ffprobe_json_as_utf8_on_windows(self):
        seen = {}
        payload = {
            "format": {"duration": "1.0", "filename": "D:/视频/final.wav"},
            "streams": [{"index": 0, "codec_type": "audio", "codec_name": "pcm_s16le"}],
        }

        def recording_runner(*_args, **kwargs):
            seen.update(kwargs)
            return type("Completed", (), {"stdout": json.dumps(payload, ensure_ascii=False)})()

        artifacts.probe_media(Path("final.wav"), runner=recording_runner)
        self.assertEqual(seen["encoding"], "utf-8")
        self.assertEqual(seen["errors"], "replace")


if __name__ == "__main__":
    unittest.main()
