from __future__ import annotations
import numpy as np
from faster_whisper import WhisperModel


class ASR:
    """Wrapper around faster-whisper. One model held in VRAM for the process lifetime."""

    def __init__(
        self,
        model: str = "Systran/faster-whisper-large-v3",
        compute_type: str = "int8",
        device: str = "cuda",
        device_index: int = 0,
    ):
        self._model = WhisperModel(
            model,
            device=device,
            device_index=device_index,
            compute_type=compute_type,
        )

    def transcribe(self, audio: np.ndarray, language: str | None = None) -> str:
        """Transcribe a full audio buffer (float32, 16kHz mono) → plain text."""
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)
        segments, _info = self._model.transcribe(
            audio,
            language=language,
            beam_size=1,
            vad_filter=False,  # we have our own VAD upstream
            without_timestamps=True,
        )
        return " ".join(seg.text.strip() for seg in segments).strip()
