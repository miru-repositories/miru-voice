from unittest.mock import patch
from dictado.injector import TextInjector


def test_inject_uses_clipboard_then_paste():
    inj = TextInjector(mode="paste")
    with patch("dictado.injector.win32clipboard") as cb, \
         patch("dictado.injector.SendInput") as send:
        cb.GetClipboardData.return_value = "previous"
        inj.inject("hola mundo")

        cb.OpenClipboard.assert_called()
        cb.EmptyClipboard.assert_called()
        cb.SetClipboardData.assert_called()
        cb.CloseClipboard.assert_called()
        assert send.called
        # SendInput called with 4 INPUT structs (Ctrl down, V down, V up, Ctrl up)
        args = send.call_args[0]
        assert args[0] == 4
