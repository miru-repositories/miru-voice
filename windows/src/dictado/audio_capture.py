from __future__ import annotations
import asyncio
import numpy as np
import sounddevice as sd
import logging

_log = logging.getLogger(__name__)


class AudioCapture:
    """Capture mono 16kHz audio from default input via WASAPI exclusive when available."""

    def __init__(self, samplerate: int = 16000, blocksize: int = 320, device: int | None = None):
        self.samplerate = samplerate
        self.blocksize = blocksize  # 320 samples = 20ms @ 16kHz
        self.device = device
        self._queue: asyncio.Queue[np.ndarray] = asyncio.Queue(maxsize=200)
        self._loop: asyncio.AbstractEventLoop | None = None

    def _callback(self, indata, frames, time_info, status):
        if self._loop is None:
            return
        chunk = indata[:, 0].copy()  # mono

        def _enqueue():
            try:
                self._queue.put_nowait(chunk)
            except asyncio.QueueFull:
                _log.debug("audio frame dropped — consumer too slow")

        self._loop.call_soon_threadsafe(_enqueue)

    def _open_stream(self):
        common = dict(
            samplerate=self.samplerate,
            blocksize=self.blocksize,
            channels=1,
            dtype="float32",
            device=self.device,
            callback=self._callback,
        )
        # Prefer WASAPI exclusive for low latency. Falls back if the default
        # device's host API is incompatible (e.g., MME/DirectSound) or if the
        # device is already in exclusive use by another process.
        try:
            return sd.InputStream(**common, extra_settings=sd.WasapiSettings(exclusive=True))
        except Exception as e:
            _log.info("WASAPI exclusive unavailable (%s); using default host API", e)
            return sd.InputStream(**common)

    async def stream(self, duration: float | None = None):
        """Async generator yielding audio chunks. If duration is None, runs until cancelled."""
        self._loop = asyncio.get_running_loop()

        with self._open_stream():
            if duration is None:
                while True:
                    yield await self._queue.get()
            else:
                deadline = self._loop.time() + duration
                while self._loop.time() < deadline:
                    try:
                        yield await asyncio.wait_for(
                            self._queue.get(), timeout=max(0.001, deadline - self._loop.time())
                        )
                    except asyncio.TimeoutError:
                        return
