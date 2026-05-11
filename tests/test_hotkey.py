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


def test_double_start_raises():
    import pytest
    listener = HotkeyListener(key="alt_r", mode="hold", on_event=lambda e: None)
    # We don't actually call .start() because it would spawn a real listener;
    # instead verify the guard by direct state.
    listener._listener = object()  # simulate an already-started listener
    with pytest.raises(RuntimeError, match="already started"):
        listener.start()


def test_on_event_exception_is_swallowed():
    def boom(_ev):
        raise RuntimeError("user code is broken")

    listener = HotkeyListener(key="alt_r", mode="hold", on_event=boom)
    # Should NOT raise — exception caught by _fire.
    listener._handle_press(key=listener._target_key)
    listener._handle_release(key=listener._target_key)
