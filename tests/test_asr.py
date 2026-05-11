"""ASR tests — slow because they actually load the model and run on GPU."""
from __future__ import annotations

import numpy as np
import pytest

from dictado.asr import ASR


_asr_model_ref: ASR | None = None  # global ref prevents GC during teardown


@pytest.fixture(scope="module")
def asr_model() -> ASR:
    """One model instance shared across the module to amortize load time."""
    global _asr_model_ref
    _asr_model_ref = ASR()
    return _asr_model_ref


@pytest.mark.slow
def test_transcribe_silence_returns_string(asr_model: ASR):
    """Transcribing pure silence shouldn't crash; output should be a string (possibly empty)."""
    silence = np.zeros(16000, dtype=np.float32)  # 1 second of silence
    text = asr_model.transcribe(silence, language="es")
    assert isinstance(text, str)


@pytest.mark.slow
def test_transcribe_accepts_non_float32_and_returns_string(asr_model: ASR):
    """If caller passes int16-derived audio (forgot to scale), ASR shouldn't crash."""
    int_audio = (np.random.randn(16000) * 100).astype(np.float64)
    text = asr_model.transcribe(int_audio, language="es")
    assert isinstance(text, str)
