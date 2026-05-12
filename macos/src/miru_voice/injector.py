from __future__ import annotations
import time

import pyperclip
from pynput.keyboard import Controller, Key


class TextInjector:
    """Paste text into the focused app on macOS via clipboard + Cmd+V, or fall back to typing.

    Requires Accessibility permission for the Python process to simulate the
    Cmd+V keystroke. Grant via System Settings → Privacy & Security →
    Accessibility.
    """

    def __init__(self, mode: str = "auto", restore_clipboard: bool = True):
        if mode not in {"auto", "paste", "type"}:
            raise ValueError(f"mode must be auto|paste|type, got {mode!r}")
        self._mode = mode
        self._restore = restore_clipboard
        self._kb = Controller()

    def inject(self, text: str) -> None:
        if not text:
            return
        if self._mode == "type":
            self._kb.type(text)
            return
        try:
            self._paste(text)
        except Exception:
            if self._mode == "paste":
                raise
            # auto: fall back to typing
            self._kb.type(text)

    def _paste(self, text: str) -> None:
        saved = pyperclip.paste() if self._restore else None
        pyperclip.copy(text)

        # Simulate Cmd+V
        with self._kb.pressed(Key.cmd):
            self._kb.press("v")
            self._kb.release("v")

        if self._restore and saved is not None:
            time.sleep(0.1)
            pyperclip.copy(saved)
