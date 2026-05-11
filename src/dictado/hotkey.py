from __future__ import annotations
import enum
from typing import Callable
from pynput import keyboard


class HotkeyEvent(enum.Enum):
    PRESS = "press"
    RELEASE = "release"


_KEY_MAP = {
    "alt_r": keyboard.Key.alt_r,
    "alt_l": keyboard.Key.alt_l,
    "ctrl_r": keyboard.Key.ctrl_r,
    "ctrl_l": keyboard.Key.ctrl_l,
    "caps_lock": keyboard.Key.caps_lock,
}


class HotkeyListener:
    """Global hotkey listener. Emits PRESS/RELEASE events for the configured key only."""

    def __init__(self, key: str, mode: str, on_event: Callable[[HotkeyEvent], None]):
        if key not in _KEY_MAP:
            raise ValueError(f"Unsupported hotkey: {key}. Choose from {list(_KEY_MAP)}")
        if mode not in {"hold", "toggle"}:
            raise ValueError(f"Mode must be 'hold' or 'toggle', got {mode!r}")
        self._target_key = _KEY_MAP[key]
        self._mode = mode
        self._on_event = on_event
        self._is_active = False  # for toggle mode
        self._listener: keyboard.Listener | None = None

    def _handle_press(self, key) -> None:
        if key != self._target_key:
            return
        if self._mode == "hold":
            self._on_event(HotkeyEvent.PRESS)
        else:  # toggle
            self._is_active = not self._is_active
            self._on_event(HotkeyEvent.PRESS if self._is_active else HotkeyEvent.RELEASE)

    def _handle_release(self, key) -> None:
        if key != self._target_key:
            return
        if self._mode == "hold":
            self._on_event(HotkeyEvent.RELEASE)
        # toggle mode ignores releases

    def start(self) -> None:
        self._listener = keyboard.Listener(
            on_press=self._handle_press,
            on_release=self._handle_release,
        )
        self._listener.start()

    def stop(self) -> None:
        if self._listener:
            self._listener.stop()
            self._listener = None
