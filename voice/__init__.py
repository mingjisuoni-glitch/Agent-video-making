"""Provider-independent narration synthesis interface."""

from .contracts import SynthesisResult, VoiceSpec
from .providers import Qwen3LocalProvider, VolcanoProvider

__all__ = ["SynthesisResult", "VoiceSpec", "Qwen3LocalProvider", "VolcanoProvider"]

