import pytest
from miru_voice.hotkey import HotkeyListener, HotkeyEvent


def _first(s):
    return next(iter(s))


def test_press_emits_event_single_key():
    events = []
    listener = HotkeyListener(keys="alt_r", mode="hold", on_event=events.append)
    target = _first(listener._target_keys)
    listener._handle_press(key=target)
    listener._handle_release(key=target)
    assert events == [HotkeyEvent.PRESS, HotkeyEvent.RELEASE]


def test_irrelevant_key_ignored():
    events = []
    listener = HotkeyListener(keys="alt_r", mode="hold", on_event=events.append)

    class FakeKey:
        pass

    listener._handle_press(key=FakeKey())
    assert events == []


def test_double_start_raises():
    listener = HotkeyListener(keys="alt_r", mode="hold", on_event=lambda e: None)
    listener._listener = object()
    with pytest.raises(RuntimeError, match="already started"):
        listener.start()


def test_on_event_exception_is_swallowed():
    def boom(_ev):
        raise RuntimeError("user code is broken")

    listener = HotkeyListener(keys="alt_r", mode="hold", on_event=boom)
    target = _first(listener._target_keys)
    listener._handle_press(key=target)
    listener._handle_release(key=target)


def test_combo_fires_only_when_all_keys_pressed():
    events = []
    listener = HotkeyListener(
        keys=["cmd_l", "space"], mode="hold", on_event=events.append
    )
    keys = list(listener._target_keys)
    a, b = keys[0], keys[1]

    listener._handle_press(key=a)
    assert events == []

    listener._handle_press(key=b)
    assert events == [HotkeyEvent.PRESS]

    listener._handle_release(key=b)
    assert events == [HotkeyEvent.PRESS, HotkeyEvent.RELEASE]

    listener._handle_release(key=a)
    assert events == [HotkeyEvent.PRESS, HotkeyEvent.RELEASE]


def test_combo_key_repeat_ignored():
    events = []
    listener = HotkeyListener(
        keys=["cmd_l", "space"], mode="hold", on_event=events.append
    )
    keys = list(listener._target_keys)
    a, b = keys[0], keys[1]

    listener._handle_press(key=a)
    listener._handle_press(key=b)
    listener._handle_press(key=b)  # repeat
    listener._handle_press(key=a)  # repeat
    assert events == [HotkeyEvent.PRESS]
