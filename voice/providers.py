"""Volcano HTTP and offline Qwen3-TTS adapters.

The cloud adapter sends text only when synthesize() is explicitly called.
Imports for the local model are delayed so cloud users do not need PyTorch.
"""

from __future__ import annotations

import base64
import json
import os
import urllib.request
import uuid
from collections.abc import Callable
from pathlib import Path

from .contracts import SynthesisResult, VoiceSpec

VOLCANO_URL = "https://openspeech.bytedance.com/api/v3/tts/unidirectional"


def has_model_weights(model_dir: Path) -> bool:
    """Accept single-file and sharded safetensors checkpoints."""
    return any(path.is_file() for path in model_dir.glob("*.safetensors"))


class VolcanoProvider:
    """Volcano Engine HTTP Chunked V3 TTS, using new or legacy credentials."""

    def __init__(self, opener: Callable = urllib.request.urlopen) -> None:
        self._opener = opener

    def synthesize(self, text: str, voice: VoiceSpec, output: Path) -> SynthesisResult:
        if voice.provider != "volcano":
            raise ValueError("voice provider must be 'volcano'")
        if not text.strip():
            raise ValueError("text is empty")
        if not voice.resource_id:
            raise ValueError("Volcano voice requires an explicit resource_id")
        if not -50 <= voice.speech_rate <= 100:
            raise ValueError("Volcano speech_rate must be between -50 and 100")
        if output.suffix.lower() != ".mp3":
            raise ValueError("Volcano output must use the .mp3 extension")
        if voice.instruct:
            raise ValueError("This adapter does not map instruct to Volcano voice controls")

        headers = {
            "Content-Type": "application/json",
            "X-Api-Resource-Id": voice.resource_id,
            "X-Api-Request-Id": str(uuid.uuid4()),
        }
        api_key = os.environ.get("VOLC_API_KEY", "")
        app_id = os.environ.get("VOLC_APP_ID", "")
        access_key = os.environ.get("VOLC_ACCESS_KEY", "")
        if api_key:
            headers["X-Api-Key"] = api_key
        elif app_id and access_key:
            headers["X-Api-App-Id"] = app_id
            headers["X-Api-Access-Key"] = access_key
        else:
            raise RuntimeError("Set VOLC_API_KEY, or both VOLC_APP_ID and VOLC_ACCESS_KEY")

        body = {
            "user": {"uid": "video-method-kit"},
            "req_params": {
                "text": text,
                "speaker": voice.speaker,
                "audio_params": {
                    "format": "mp3",
                    "sample_rate": 24000,
                    "speech_rate": voice.speech_rate,
                },
            },
        }
        request = urllib.request.Request(
            VOLCANO_URL,
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        chunks: list[bytes] = []
        completed = False
        with self._opener(request, timeout=120) as response:
            for raw_line in response:
                if not raw_line.strip():
                    continue
                event = json.loads(raw_line)
                code = event.get("code", 0)
                if code == 20000000:
                    completed = True
                    break
                if code != 0:
                    raise RuntimeError(f"Volcano TTS failed, code={code}: {event.get('message', '')}")
                if event.get("data"):
                    chunks.append(base64.b64decode(event["data"], validate=True))
        if not completed or not chunks:
            raise RuntimeError("Volcano TTS returned incomplete or empty audio")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"".join(chunks))
        return SynthesisResult(output, "volcano", voice.speaker, "mp3", 24000)


class Qwen3LocalProvider:
    """Load a downloaded CustomVoice model from disk; never download at runtime."""

    def __init__(self, model_dir: Path | None = None) -> None:
        configured = os.environ.get("QWEN3_TTS_MODEL_DIR")
        self.model_dir = Path(model_dir or configured or "")
        self._model = None

    def synthesize(self, text: str, voice: VoiceSpec, output: Path) -> SynthesisResult:
        if voice.provider != "qwen3-local":
            raise ValueError("voice provider must be 'qwen3-local'")
        if not text.strip():
            raise ValueError("text is empty")
        if output.suffix.lower() != ".wav":
            raise ValueError("Qwen3 output must use the .wav extension")
        if voice.speech_rate != 0:
            raise ValueError("Qwen3 CustomVoice has no numeric speech_rate control")
        if not has_model_weights(self.model_dir):
            raise FileNotFoundError("Set QWEN3_TTS_MODEL_DIR to a downloaded CustomVoice model")
        config_path = self.model_dir / "config.json"
        if not config_path.is_file():
            raise FileNotFoundError("Qwen3-TTS config.json is missing")
        model_config = json.loads(config_path.read_text(encoding="utf-8"))
        if model_config.get("tts_model_type") != "custom_voice":
            raise ValueError("Qwen3 provider requires a CustomVoice model")
        if voice.instruct and model_config.get("tts_model_size") == "0b6":
            raise ValueError("Qwen3-TTS 0.6B CustomVoice ignores instruct; use 1.7B or remove it")

        import numpy as np
        import soundfile as sf
        import torch
        from qwen_tts import Qwen3TTSModel

        if self._model is None:
            use_cuda = torch.cuda.is_available()
            self._model = Qwen3TTSModel.from_pretrained(
                str(self.model_dir),
                device_map="cuda:0" if use_cuda else "cpu",
                dtype=torch.bfloat16 if use_cuda else torch.float32,
            )
        torch.manual_seed(voice.seed)
        waves, sample_rate = self._model.generate_custom_voice(
            text=text,
            language=voice.language,
            speaker=voice.speaker,
            instruct=voice.instruct or None,
            non_streaming_mode=True,
        )
        waveform = np.asarray(waves[0], dtype=np.float32).reshape(-1)
        if not waveform.size or not np.isfinite(waveform).all():
            raise RuntimeError("Qwen3-TTS returned invalid audio")
        output.parent.mkdir(parents=True, exist_ok=True)
        sf.write(output, waveform, int(sample_rate))
        return SynthesisResult(output, "qwen3-local", voice.speaker, "wav", int(sample_rate))

