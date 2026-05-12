from __future__ import annotations
import asyncio
import logging
from collections import deque

import numpy as np

from miru_voice.asr import ASR
from miru_voice.audio_capture import AudioCapture
from miru_voice.hotkey import HotkeyEvent, HotkeyListener
from miru_voice.injector import TextInjector

log = logging.getLogger("miru_voice")


class App:
    def __init__(self) -> None:
        self._loop = asyncio.new_event_loop()
        self._capture = AudioCapture()
        self._asr: ASR | None = None  # lazy load to defer model load until first use
        self._injector = TextInjector()
        self._recording = False
        self._buffer: deque[np.ndarray] = deque()
        self._capture_task: asyncio.Task | None = None

    def _on_hotkey(self, event: HotkeyEvent) -> None:
        # Called from pynput thread → bounce to event loop
        if event == HotkeyEvent.PRESS:
            self._loop.call_soon_threadsafe(self._start_recording)
        else:
            self._loop.call_soon_threadsafe(self._stop_recording)

    def _start_recording(self) -> None:
        if self._recording:
            return
        log.info("recording start")
        self._recording = True
        self._buffer.clear()
        self._capture_task = self._loop.create_task(self._capture_loop())

    def _stop_recording(self) -> None:
        if not self._recording:
            return
        log.info("recording stop")
        self._recording = False
        if self._capture_task:
            self._capture_task.cancel()
        self._loop.create_task(self._transcribe_and_inject())

    async def _capture_loop(self) -> None:
        try:
            async for chunk in self._capture.stream():
                if not self._recording:
                    break
                self._buffer.append(chunk)
        except asyncio.CancelledError:
            pass

    async def _transcribe_and_inject(self) -> None:
        if not self._buffer:
            return
        audio = np.concatenate(list(self._buffer))
        rms = float(np.sqrt((audio ** 2).mean()))
        if rms < 0.005:
            log.info("silence skip (rms=%.4f)", rms)
            return
        if self._asr is None:
            log.info("loading ASR model...")
            self._asr = ASR()
        text = await asyncio.to_thread(self._asr.transcribe, audio)
        if text:
            log.info("transcribed: %r", text)
            self._injector.inject(text)

    def run(self) -> None:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(message)s",
        )
        listener = HotkeyListener(
            keys=["ctrl_l", "space"], mode="hold", on_event=self._on_hotkey
        )
        listener.start()
        log.info("ready — hold Left Ctrl + Space to dictate. Ctrl+C to quit.")
        try:
            self._loop.run_forever()
        except KeyboardInterrupt:
            pass
        finally:
            listener.stop()


def run() -> None:
    App().run()


if __name__ == "__main__":
    run()
