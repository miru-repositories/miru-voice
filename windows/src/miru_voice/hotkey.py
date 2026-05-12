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
    "alt_gr": keyboard.Key.alt_gr,
    "ctrl_r": keyboard.Key.ctrl_r,
    "ctrl_l": keyboard.Key.ctrl_l,
    "shift_l": keyboard.Key.shift_l,
    "shift_r": keyboard.Key.shift_r,
    "space": keyboard.Key.space,
    "caps_lock": keyboard.Key.caps_lock,
    "f12": keyboard.Key.f12,
    "f9": keyboard.Key.f9,
    "f10": keyboard.Key.f10,
}


class HotkeyListener:
    """Global hotkey listener. Emits PRESS/RELEASE for a single key or a key combination.

    Pass a string for a single key (e.g. ``"alt_gr"``) or a list for a combo
    (e.g. ``["ctrl_l", "space"]``). For combos, PRESS fires when ALL keys are
    held together; RELEASE fires when ANY key in the combo is released after
    that.
    """

    def __init__(
        self,
        keys: str | list[str],
        mode: str,
        on_event: Callable[[HotkeyEvent], None],
    ):
        if isinstance(keys, str):
            keys = [keys]
        if not keys:
            raise ValueError("keys must be a non-empty string or list of strings")
        for k in keys:
            if k not in _KEY_MAP:
                raise ValueError(f"Unsupported hotkey: {k}. Choose from {list(_KEY_MAP)}")
        if mode not in {"hold", "toggle"}:
            raise ValueError(f"Mode must be 'hold' or 'toggle', got {mode!r}")
        self._target_keys: set = {_KEY_MAP[k] for k in keys}
        self._mode = mode
        self._on_event = on_event
        self._pressed: set = set()
        self._is_active = False  # toggle mode
        self._listener: keyboard.Listener | None = None

    def _fire(self, event: HotkeyEvent) -> None:
        try:
            self._on_event(event)
        except Exception:
            pass

    def _handle_press(self, key) -> None:
        if key not in self._target_keys:
            return
        if key in self._pressed:
            return  # key repeat
        was_complete = self._pressed == self._target_keys
        self._pressed.add(key)
        is_complete = self._pressed == self._target_keys
        if not was_complete and is_complete:
            if self._mode == "hold":
                self._fire(HotkeyEvent.PRESS)
            else:
                self._is_active = not self._is_active
                self._fire(HotkeyEvent.PRESS if self._is_active else HotkeyEvent.RELEASE)

    def _handle_release(self, key) -> None:
        if key not in self._target_keys:
            return
        if key not in self._pressed:
            return
        was_complete = self._pressed == self._target_keys
        self._pressed.discard(key)
        if was_complete and self._mode == "hold":
            self._fire(HotkeyEvent.RELEASE)

    def start(self) -> None:
        if self._listener is not None:
            raise RuntimeError("HotkeyListener already started")
        self._listener = keyboard.Listener(
            on_press=self._handle_press,
            on_release=self._handle_release,
        )
        self._listener.start()

    def stop(self) -> None:
        if self._listener:
            self._listener.stop()
            self._listener = None
