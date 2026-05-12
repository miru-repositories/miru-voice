from unittest.mock import patch, MagicMock
from miru_voice.injector import TextInjector


def test_inject_uses_clipboard_then_paste():
    """Paste mode: copies to clipboard, simulates Cmd+V via pynput, restores prior clipboard."""
    inj = TextInjector(mode="paste")

    with patch("miru_voice.injector.pyperclip") as cb:
        cb.paste.return_value = "previous"

        # Capture the keyboard controller's pressed-context calls
        fake_kb = MagicMock()
        inj._kb = fake_kb

        inj.inject("hola mundo")

        # Clipboard was read (for restore), then text was copied, then prior restored
        cb.paste.assert_called_once()
        # First copy is "hola mundo", second (after paste) is "previous"
        assert cb.copy.call_args_list[0].args[0] == "hola mundo"
        assert cb.copy.call_args_list[-1].args[0] == "previous"

        # Cmd+V was simulated
        fake_kb.pressed.assert_called_once()


def test_inject_empty_string_noop():
    inj = TextInjector(mode="paste")
    with patch("miru_voice.injector.pyperclip") as cb:
        inj.inject("")
        cb.copy.assert_not_called()


def test_type_mode_skips_clipboard():
    inj = TextInjector(mode="type")
    inj._kb = MagicMock()
    with patch("miru_voice.injector.pyperclip") as cb:
        inj.inject("hola")
        cb.copy.assert_not_called()
        inj._kb.type.assert_called_once_with("hola")


def test_invalid_mode_raises():
    import pytest

    with pytest.raises(ValueError, match="auto|paste|type"):
        TextInjector(mode="bogus")
