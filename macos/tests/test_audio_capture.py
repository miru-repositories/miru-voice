import numpy as np
import pytest

from dictado.audio_capture import AudioCapture


@pytest.mark.asyncio
async def test_capture_yields_chunks(mocker):
    """AudioCapture yields fixed-size float32 chunks from sounddevice."""
    fake_frames = np.zeros((320, 1), dtype=np.float32)

    class FakeStream:
        def __init__(self, samplerate, blocksize, channels, dtype, callback, **kw):
            self._callback = callback

        def __enter__(self):
            for _ in range(3):
                self._callback(fake_frames, 320, None, None)
            return self

        def __exit__(self, *a):
            pass

    mocker.patch("dictado.audio_capture.sd.InputStream", FakeStream)

    capture = AudioCapture(samplerate=16000, blocksize=320)
    chunks = []
    async for chunk in capture.stream(duration=0.05):
        chunks.append(chunk)
        if len(chunks) == 3:
            break

    assert len(chunks) == 3
    assert all(c.shape == (320,) for c in chunks)
    assert all(c.dtype == np.float32 for c in chunks)
