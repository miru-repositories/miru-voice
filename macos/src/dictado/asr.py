from __future__ import annotations
import numpy as np
from faster_whisper import WhisperModel


class ASR:
    """Wrapper around faster-whisper. One model held in RAM for the process lifetime.

    macOS notes:
    - CTranslate2 has no Metal/GPU backend on macOS; this runs on CPU.
    - On Apple Silicon (M1+) the CPU is fast enough for `large-v3` at int8 to be
      usable (~600-900ms for a 5s utterance). On Intel Macs prefer `medium`
      or `small`.
    - For best performance on Apple Silicon, swap to `mlx-whisper` or
      `whisper.cpp` Metal — both can run large-v3 at ~3x realtime.
    """

    def __init__(
        self,
        model: str = "Systran/faster-whisper-large-v3",
        compute_type: str = "int8",
        device: str = "cpu",
        device_index: int = 0,
        cpu_threads: int = 0,  # 0 → let CT2 auto-detect
    ):
        self._model = WhisperModel(
            model,
            device=device,
            device_index=device_index,
            compute_type=compute_type,
            cpu_threads=cpu_threads,
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
