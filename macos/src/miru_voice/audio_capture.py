from __future__ import annotations
import asyncio
import logging

import numpy as np
import sounddevice as sd

_log = logging.getLogger(__name__)


class AudioCapture:
    """Capture mono 16kHz audio from default input via CoreAudio (macOS)."""

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

    async def stream(self, duration: float | None = None):
        """Async generator yielding audio chunks. If duration is None, runs until cancelled."""
        self._loop = asyncio.get_running_loop()

        with sd.InputStream(
            samplerate=self.samplerate,
            blocksize=self.blocksize,
            channels=1,
            dtype="float32",
            device=self.device,
            callback=self._callback,
        ):
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
