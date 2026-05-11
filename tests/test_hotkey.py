from unittest.mock import MagicMock
from dictado.hotkey import HotkeyListener, HotkeyEvent


def test_press_emits_event(monkeypatch):
    """When the configured key is pressed, callback fires with PRESS event."""
    events = []

    def on_event(ev: HotkeyEvent):
        events.append(ev)

    listener = HotkeyListener(key="alt_r", mode="hold", on_event=on_event)
    listener._handle_press(key=listener._target_key)
    listener._handle_release(key=listener._target_key)

    assert events == [HotkeyEvent.PRESS, HotkeyEvent.RELEASE]


def test_irrelevant_key_ignored():
    events = []
    listener = HotkeyListener(key="alt_r", mode="hold", on_event=events.append)

    class FakeKey:
        pass

    listener._handle_press(key=FakeKey())
    assert events == []
