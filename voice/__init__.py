"""Provider-independent narration synthesis interface."""

from .contracts import SynthesisResult, VoiceSpec
from .providers import Qwen3LocalProvider, VolcanoProvider

__all__ = ["Qwen3LocalProvider", "SynthesisResult", "VoiceSpec", "VolcanoProvider"]

