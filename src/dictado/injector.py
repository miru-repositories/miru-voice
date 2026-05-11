from __future__ import annotations
import ctypes
import time
from ctypes import wintypes

import win32clipboard
import win32con
from pynput.keyboard import Controller as KeyboardController

PUL = ctypes.POINTER(ctypes.c_ulong)


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", PUL),
    ]


class _InputUnion(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("u", _InputUnion)]


INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
VK_CONTROL = 0x11
VK_V = 0x56

SendInput = ctypes.windll.user32.SendInput


def _key(vk: int, up: bool = False) -> INPUT:
    return INPUT(
        type=INPUT_KEYBOARD,
        u=_InputUnion(ki=KEYBDINPUT(vk, 0, KEYEVENTF_KEYUP if up else 0, 0, None)),
    )


class TextInjector:
    """Paste text into the active window via clipboard, or fall back to typing."""

    def __init__(self, mode: str = "auto", restore_clipboard: bool = True):
        if mode not in {"auto", "paste", "type"}:
            raise ValueError(f"mode must be auto|paste|type, got {mode!r}")
        self._mode = mode
        self._restore = restore_clipboard
        self._kb = KeyboardController()

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
        saved = None
        win32clipboard.OpenClipboard()
        try:
            if self._restore:
                try:
                    saved = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
                except Exception:
                    saved = None
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, text)
        finally:
            win32clipboard.CloseClipboard()

        inputs = (INPUT * 4)(
            _key(VK_CONTROL),
            _key(VK_V),
            _key(VK_V, up=True),
            _key(VK_CONTROL, up=True),
        )
        sent = SendInput(4, ctypes.byref(inputs), ctypes.sizeof(INPUT))
        if sent != 4:
            raise OSError(f"SendInput delivered {sent}/4 events")

        if self._restore and saved is not None:
            time.sleep(0.1)
            try:
                win32clipboard.OpenClipboard()
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, saved)
            finally:
                win32clipboard.CloseClipboard()
