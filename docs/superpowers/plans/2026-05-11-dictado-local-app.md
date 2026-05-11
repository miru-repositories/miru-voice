# Dictado Local App Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Windows native push-to-talk dictation app that transcribes voice to text 100% locally on an RTX 3080, latency target <500ms end-to-end.

**Architecture:** Single Python process. Hotkey listener triggers WASAPI audio capture → silero-vad chunks audio at speech boundaries → faster-whisper (distil-large-v3 int8) transcribes on GPU → regex + Phi-3-mini Q4 postprocess → clipboard+SendInput pastes text into active app. Tray icon shows state.

**Tech Stack:** Python 3.11+ · `sounddevice` (WASAPI exclusive) · `silero-vad` · `faster-whisper` · `llama-cpp-python` (CUDA) · `pynput` · `pywin32` · `pystray` · `pytest` · `PyInstaller`.

**Spec:** `docs/superpowers/specs/2026-05-11-dictado-local-design.md`

**Working directory:** `C:\Users\aaron\dictado-app\`

**Hardware assumption:** Windows 11, NVIDIA RTX 3080 10GB, CUDA 12.x driver 591.86+.

---

## File Structure (locked-in decomposition)

```
dictado-app/
├── pyproject.toml              # deps + tooling config
├── README.md                   # quickstart
├── .gitignore                  # ignore venv, models, logs
├── src/dictado/
│   ├── __init__.py
│   ├── main.py                 # orchestrator, asyncio event loop
│   ├── hotkey.py               # global hotkey listener (pynput)
│   ├── audio_capture.py        # WASAPI exclusive capture
│   ├── vad.py                  # silero-vad wrapper
│   ├── asr.py                  # faster-whisper wrapper
│   ├── postprocess.py          # regex + LLM cleanup
│   ├── llm.py                  # llama-cpp-python wrapper
│   ├── injector.py             # clipboard + SendInput paste
│   ├── app_context.py          # active app detection + rules
│   ├── tray.py                 # system tray icon + menu
│   ├── config.py               # TOML config load/save
│   ├── state.py                # shared state machine (idle/listening/transcribing)
│   └── logging_setup.py        # rotating file logger
└── tests/
    ├── conftest.py             # shared fixtures, audio samples
    ├── fixtures/
    │   ├── hello_world_es.wav
    │   ├── hello_world_en.wav
    │   └── with_muletillas.wav
    ├── test_hotkey.py
    ├── test_audio_capture.py
    ├── test_vad.py
    ├── test_asr.py
    ├── test_postprocess.py
    ├── test_injector.py
    ├── test_app_context.py
    ├── test_config.py
    └── test_integration.py
```

Each `src/dictado/*.py` file has one responsibility. `main.py` orchestrates; everything else exposes a narrow interface and can be tested independently.

---

## Chunk 1: Project Setup + Phase 1 MVP (hotkey → ASR → paste)

Goal at end of Chunk 1: sostener Right Alt, hablar "hola mundo", soltar, "hola mundo" aparece pegado en Notepad.

### Task 1.1: Initialize repo and project structure

**Files:**
- Create: `C:\Users\aaron\dictado-app\.gitignore`
- Create: `C:\Users\aaron\dictado-app\README.md`
- Create: `C:\Users\aaron\dictado-app\pyproject.toml`
- Create: `C:\Users\aaron\dictado-app\src\dictado\__init__.py`
- Create: `C:\Users\aaron\dictado-app\tests\conftest.py`

- [ ] **Step 1: Initialize git repo**

```powershell
cd C:\Users\aaron\dictado-app
git init
git branch -M main
```

- [ ] **Step 2: Create `.gitignore`**

```
# Python
__pycache__/
*.py[cod]
*.egg-info/
.pytest_cache/
.venv/
venv/

# Models (large binary files — downloaded on first run)
models/
*.gguf
*.bin

# Logs
*.log
logs/

# OS
Thumbs.db
.DS_Store

# Build artifacts
build/
dist/
*.spec
```

- [ ] **Step 3: Create `pyproject.toml`**

```toml
[project]
name = "dictado"
version = "0.1.0"
description = "Local push-to-talk dictation for Windows (RTX 3080)"
requires-python = ">=3.11"
dependencies = [
    "sounddevice>=0.4.6",
    "numpy>=1.26",
    "silero-vad>=5.0",
    "faster-whisper>=1.0",
    "pynput>=1.7",
    "pywin32>=306",
    "pystray>=0.19",
    "Pillow>=10",
    "tomli-w>=1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8",
    "pytest-asyncio>=0.23",
    "pytest-mock>=3.12",
    "ruff>=0.4",
]
llm = [
    # CUDA wheel — install via: pip install --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu121/ llama-cpp-python
    "llama-cpp-python>=0.2.79",
]

[project.scripts]
dictado = "dictado.main:run"

[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"

[tool.ruff]
line-length = 100
target-version = "py311"
```

- [ ] **Step 4: Create `README.md`**

```markdown
# Dictado

Local push-to-talk dictation app for Windows. Inspired by Wispr Flow but runs 100% on your machine.

## Requirements

- Windows 10/11
- NVIDIA GPU with ≥8GB VRAM (tested on RTX 3080)
- CUDA 12.x driver (591.86+)
- Python 3.11+

## Install (dev)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
pip install --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu121/ llama-cpp-python
```

## Run

```powershell
python -m dictado.main
```

Hold `Right Alt`, speak, release. Text pastes into active window.

## Test

```powershell
pytest -v
```

See `docs/superpowers/specs/` for the full design.
```

- [ ] **Step 5: Create empty package and conftest stubs**

`src/dictado/__init__.py`:
```python
__version__ = "0.1.0"
```

`tests/conftest.py`:
```python
import sys
from pathlib import Path

# Ensure src/ is importable
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
```

- [ ] **Step 6: First commit**

```powershell
git add .gitignore README.md pyproject.toml src/ tests/
git commit -m "chore: scaffold dictado project"
```

---

### Task 1.2: Create Python venv and install base deps

- [ ] **Step 1: Create venv and activate**

```powershell
cd C:\Users\aaron\dictado-app
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -c "import sys; print(sys.version)"
```
Expected: `3.11.x` or higher.

- [ ] **Step 2: Install dev deps (sin LLM por ahora)**

```powershell
pip install --upgrade pip
pip install -e ".[dev]"
```
Expected: install completes without errors. `pytest --version` works.

- [ ] **Step 3: Verify CUDA-capable PyTorch is NOT needed by faster-whisper**

`faster-whisper` uses CTranslate2, not PyTorch. But `silero-vad` does need PyTorch CPU. Install minimal:
```powershell
pip install torch --index-url https://download.pytorch.org/whl/cpu
python -c "import torch; print(torch.__version__)"
```
Expected: prints torch version.

- [ ] **Step 4: Smoke test imports**

```powershell
python -c "import sounddevice, faster_whisper, pynput, pystray; print('OK')"
```
Expected: `OK`.

- [ ] **Step 5: Commit lockfile state via README note**

```powershell
git add README.md
git commit -m "docs: confirm venv setup steps work" --allow-empty
```

---

### Task 1.3: Implement `hotkey.py` (push-to-talk listener)

**Files:**
- Create: `src/dictado/hotkey.py`
- Create: `tests/test_hotkey.py`

- [ ] **Step 1: Write failing test**

`tests/test_hotkey.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

```powershell
pytest tests/test_hotkey.py -v
```
Expected: FAIL — `ModuleNotFoundError: dictado.hotkey`.

- [ ] **Step 3: Implement `hotkey.py`**

```python
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
```

- [ ] **Step 4: Run tests to verify pass**

```powershell
pytest tests/test_hotkey.py -v
```
Expected: 2 passed.

- [ ] **Step 5: Commit**

```powershell
git add src/dictado/hotkey.py tests/test_hotkey.py
git commit -m "feat: hotkey listener with hold and toggle modes"
```

---

### Task 1.4: Implement `audio_capture.py` (WASAPI exclusive)

**Files:**
- Create: `src/dictado/audio_capture.py`
- Create: `tests/test_audio_capture.py`

- [ ] **Step 1: Write failing test**

`tests/test_audio_capture.py`:
```python
import asyncio
import numpy as np
import pytest
from dictado.audio_capture import AudioCapture


@pytest.mark.asyncio
async def test_capture_yields_chunks(mocker):
    """AudioCapture yields fixed-size float32 chunks from sounddevice."""
    # Patch sounddevice to push fake audio frames into the callback
    fake_frames = np.zeros((320, 1), dtype=np.float32)

    class FakeStream:
        def __init__(self, samplerate, blocksize, channels, dtype, callback, **kw):
            self._callback = callback
        def __enter__(self):
            # simulate 3 callbacks
            for _ in range(3):
                self._callback(fake_frames, 320, None, None)
            return self
        def __exit__(self, *a): pass

    mocker.patch("dictado.audio_capture.sd.InputStream", FakeStream)

    capture = AudioCapture(samplerate=16000, blocksize=320)
    chunks = []
    async for chunk in capture.stream(duration=0.05):
        chunks.append(chunk)
        if len(chunks) == 3:
            break

    assert len(chunks) == 3
    assert all(c.shape == (320,) for c in chunks)
    assert all(c.dtype == np.float32 for c in chunks)
```

- [ ] **Step 2: Run test to verify it fails**

```powershell
pytest tests/test_audio_capture.py -v
```
Expected: FAIL — module not found.

- [ ] **Step 3: Implement `audio_capture.py`**

```python
from __future__ import annotations
import asyncio
import numpy as np
import sounddevice as sd


class AudioCapture:
    """Capture mono 16kHz audio from default input via WASAPI exclusive when available."""

    def __init__(self, samplerate: int = 16000, blocksize: int = 320, device: int | None = None):
        self.samplerate = samplerate
        self.blocksize = blocksize  # 320 samples = 20ms @ 16kHz
        self.device = device
        self._queue: asyncio.Queue[np.ndarray] = asyncio.Queue(maxsize=200)
        self._loop: asyncio.AbstractEventLoop | None = None

    def _callback(self, indata, frames, time_info, status):
        # sounddevice callback runs in audio thread; push to asyncio queue safely
        if self._loop is None:
            return
        chunk = indata[:, 0].copy()  # mono
        try:
            self._loop.call_soon_threadsafe(self._queue.put_nowait, chunk)
        except asyncio.QueueFull:
            pass  # drop frame if downstream is too slow (logged elsewhere)

    async def stream(self, duration: float | None = None):
        """Async generator yielding audio chunks. If duration is None, runs until cancelled."""
        self._loop = asyncio.get_running_loop()
        # Try WASAPI exclusive first; fall back to default
        extra = None
        try:
            extra = sd.WasapiSettings(exclusive=True)
        except Exception:
            pass

        with sd.InputStream(
            samplerate=self.samplerate,
            blocksize=self.blocksize,
            channels=1,
            dtype="float32",
            device=self.device,
            callback=self._callback,
            extra_settings=extra,
        ):
            if duration is None:
                while True:
                    yield await self._queue.get()
            else:
                deadline = self._loop.time() + duration
                while self._loop.time() < deadline:
                    try:
                        yield await asyncio.wait_for(
                            self._queue.get(), timeout=max(0.001, deadline - self._loop.time())
                        )
                    except asyncio.TimeoutError:
                        return
```

- [ ] **Step 4: Run test to verify pass**

```powershell
pytest tests/test_audio_capture.py -v
```
Expected: 1 passed.

- [ ] **Step 5: Manual mic smoke test (run, speak, observe shape)**

Create temp `scripts/smoke_audio.py`:
```python
import asyncio, numpy as np
from dictado.audio_capture import AudioCapture

async def main():
    cap = AudioCapture()
    n = 0
    async for chunk in cap.stream(duration=2.0):
        n += 1
        if n == 1:
            print(f"shape={chunk.shape} dtype={chunk.dtype} rms={np.sqrt((chunk**2).mean()):.4f}")
    print(f"got {n} chunks in 2s (expected ~100)")

asyncio.run(main())
```

```powershell
python scripts/smoke_audio.py
```
Expected: ~100 chunks. RMS >0 if speaking, ~0 if silent.

- [ ] **Step 6: Commit**

```powershell
git add src/dictado/audio_capture.py tests/test_audio_capture.py
git commit -m "feat: WASAPI exclusive audio capture with asyncio streaming"
```

---

### Task 1.5: Implement `asr.py` (faster-whisper wrapper)

**Files:**
- Create: `src/dictado/asr.py`
- Create: `tests/test_asr.py`
- Create: `tests/fixtures/hello_world_es.wav` (record manually: "hola mundo, esto es una prueba")

- [ ] **Step 1: Record fixture audio**

```powershell
# Use Windows Sound Recorder or any tool. Save as 16kHz mono WAV at:
# C:\Users\aaron\dictado-app\tests\fixtures\hello_world_es.wav
# Content: "hola mundo, esto es una prueba"
# Duration: 2-3 seconds
```

- [ ] **Step 2: Write failing test**

`tests/test_asr.py`:
```python
import wave
import numpy as np
from pathlib import Path
from dictado.asr import ASR

FIXTURES = Path(__file__).parent / "fixtures"


def load_wav(path: Path) -> np.ndarray:
    with wave.open(str(path), "rb") as w:
        assert w.getframerate() == 16000
        assert w.getnchannels() == 1
        raw = w.readframes(w.getnframes())
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0


def test_transcribe_spanish_fixture():
    asr = ASR(model="distil-whisper/distil-large-v3", compute_type="int8", device="cuda")
    audio = load_wav(FIXTURES / "hello_world_es.wav")
    text = asr.transcribe(audio, language="es")
    assert "hola" in text.lower()
    assert "mundo" in text.lower()
```

- [ ] **Step 3: Run test to verify it fails**

```powershell
pytest tests/test_asr.py -v
```
Expected: FAIL — module not found.

- [ ] **Step 4: Implement `asr.py`**

```python
from __future__ import annotations
import numpy as np
from faster_whisper import WhisperModel


class ASR:
    """Wrapper around faster-whisper. One model held in VRAM for the process lifetime."""

    def __init__(
        self,
        model: str = "distil-whisper/distil-large-v3",
        compute_type: str = "int8",
        device: str = "cuda",
        device_index: int = 0,
    ):
        self._model = WhisperModel(
            model,
            device=device,
            device_index=device_index,
            compute_type=compute_type,
        )

    def transcribe(self, audio: np.ndarray, language: str | None = None) -> str:
        """Transcribe a full audio buffer (float32, 16kHz mono) → plain text."""
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)
        segments, _info = self._model.transcribe(
            audio,
            language=language,
            beam_size=1,
            vad_filter=False,  # we have our own VAD upstream
            without_timestamps=True,
        )
        return " ".join(seg.text.strip() for seg in segments).strip()
```

- [ ] **Step 5: Pre-download model (one-time, large file)**

```powershell
python -c "from faster_whisper import WhisperModel; WhisperModel('distil-whisper/distil-large-v3', device='cuda', compute_type='int8')"
```
Expected: downloads ~756MB to `%USERPROFILE%\.cache\huggingface`. Takes ~2 min on decent internet.

- [ ] **Step 6: Run test to verify pass**

```powershell
pytest tests/test_asr.py -v
```
Expected: 1 passed. First run takes ~5s for model load + inference.

- [ ] **Step 7: Commit**

```powershell
git add src/dictado/asr.py tests/test_asr.py tests/fixtures/hello_world_es.wav
git commit -m "feat: faster-whisper ASR with distil-large-v3 int8 on CUDA"
```

---

### Task 1.6: Implement `injector.py` (clipboard + Ctrl+V)

**Files:**
- Create: `src/dictado/injector.py`
- Create: `tests/test_injector.py`

- [ ] **Step 1: Write failing test**

`tests/test_injector.py`:
```python
from unittest.mock import patch, MagicMock
from dictado.injector import TextInjector


def test_inject_uses_clipboard_then_paste():
    inj = TextInjector(mode="paste")
    with patch("dictado.injector.win32clipboard") as cb, \
         patch("dictado.injector.SendInput") as send:
        cb.GetClipboardData.return_value = "previous"
        inj.inject("hola mundo")

        # opened, set CF_UNICODETEXT, closed
        cb.OpenClipboard.assert_called()
        cb.EmptyClipboard.assert_called()
        cb.SetClipboardData.assert_called()
        cb.CloseClipboard.assert_called()
        # Ctrl+V sent
        assert send.called
        # 4 inputs: ctrl down, v down, v up, ctrl up
        args = send.call_args[0]
        assert args[0] == 4
```

- [ ] **Step 2: Run test to verify it fails**

```powershell
pytest tests/test_injector.py -v
```
Expected: FAIL — module not found.

- [ ] **Step 3: Implement `injector.py`**

```python
from __future__ import annotations
import ctypes
import time
from ctypes import wintypes

import win32clipboard
import win32con
from pynput.keyboard import Controller as KeyboardController

# Win32 SendInput plumbing
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
            # auto: fall back
            self._kb.type(text)

    def _paste(self, text: str) -> None:
        saved = None
        win32clipboard.OpenClipboard()
        try:
            if self._restore:
                try:
                    saved = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
                except TypeError:
                    saved = None
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, text)
        finally:
            win32clipboard.CloseClipboard()

        # Send Ctrl+V
        inputs = (INPUT * 4)(
            _key(VK_CONTROL),
            _key(VK_V),
            _key(VK_V, up=True),
            _key(VK_CONTROL, up=True),
        )
        SendInput(4, ctypes.byref(inputs), ctypes.sizeof(INPUT))

        # Restore clipboard after a short delay so the paste actually consumes it
        if self._restore and saved is not None:
            time.sleep(0.1)
            try:
                win32clipboard.OpenClipboard()
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, saved)
            finally:
                win32clipboard.CloseClipboard()
```

- [ ] **Step 4: Run test to verify pass**

```powershell
pytest tests/test_injector.py -v
```
Expected: 1 passed.

- [ ] **Step 5: Manual smoke test (paste into Notepad)**

```powershell
# 1. Open Notepad and click in the text area
# 2. Run:
python -c "from dictado.injector import TextInjector; TextInjector().inject('hola desde dictado')"
```
Expected: "hola desde dictado" appears in Notepad.

- [ ] **Step 6: Commit**

```powershell
git add src/dictado/injector.py tests/test_injector.py
git commit -m "feat: clipboard-based text injection with typing fallback"
```

---

### Task 1.7: Implement `main.py` MVP orchestrator (no VAD yet)

**Files:**
- Create: `src/dictado/main.py`

- [ ] **Step 1: Implement orchestrator**

```python
from __future__ import annotations
import asyncio
import logging
import sys
import threading
from collections import deque

import numpy as np

from dictado.audio_capture import AudioCapture
from dictado.asr import ASR
from dictado.hotkey import HotkeyEvent, HotkeyListener
from dictado.injector import TextInjector

log = logging.getLogger("dictado")


class App:
    def __init__(self):
        self._loop = asyncio.new_event_loop()
        self._capture = AudioCapture()
        self._asr: ASR | None = None  # lazy load
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
        # Skip pure silence
        if np.sqrt((audio**2).mean()) < 0.005:
            log.info("silence skip")
            return
        if self._asr is None:
            log.info("loading ASR model...")
            self._asr = ASR()
        text = await asyncio.to_thread(self._asr.transcribe, audio)
        if text:
            log.info(f"transcribed: {text!r}")
            self._injector.inject(text)

    def run(self) -> None:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
        listener = HotkeyListener(key="alt_r", mode="hold", on_event=self._on_hotkey)
        listener.start()
        log.info("ready — hold Right Alt to dictate. Ctrl+C to quit.")
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
```

- [ ] **Step 2: Smoke-test end-to-end**

```powershell
# 1. Open Notepad, click in the text area
# 2. In a separate terminal:
python -m dictado.main
# 3. Hold Right Alt, say "hola mundo esto es una prueba", release
# 4. Wait ~1 second
# 5. Verify text appears in Notepad
# 6. Ctrl+C to stop
```
Expected: text appears in Notepad. Latency ~600-800ms (no VAD yet, no LLM yet).

- [ ] **Step 3: Commit**

```powershell
git add src/dictado/main.py
git commit -m "feat: MVP orchestrator — hotkey + capture + ASR + paste"
```

---

### Task 1.8: Tag Phase 1 MVP

- [ ] **Step 1: Tag release**

```powershell
git tag -a phase1-mvp -m "Phase 1: minimal viable dictation working"
```

- [ ] **Step 2: Update README**

Add a "Status" section to `README.md`:
```markdown
## Status

- [x] Phase 1: MVP — hotkey + ASR + paste
- [ ] Phase 2: VAD + regex postprocess + tray
- [ ] Phase 3: LLM postprocess + voice commands + app context
- [ ] Phase 4: Packaging
```

```powershell
git add README.md
git commit -m "docs: phase 1 status"
```

---

## Chunk 2: Phase 2 — VAD, regex postprocess, tray icon

Goal at end of Chunk 2: latencia <800ms con corrección de muletillas automática, fin de frase detectado por VAD, icono visual en tray que muestra estado.

### Task 2.1: Implement `vad.py` (silero-vad wrapper)

**Files:**
- Create: `src/dictado/vad.py`
- Create: `tests/test_vad.py`

- [ ] **Step 1: Failing test**

`tests/test_vad.py`:
```python
import numpy as np
from dictado.vad import VAD, SpeechEvent


def test_vad_detects_speech_in_loud_audio():
    vad = VAD()
    # 0.5s of 440Hz tone at -10dB
    t = np.linspace(0, 0.5, 8000, endpoint=False)
    audio = (0.3 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    events = []
    for i in range(0, len(audio), 512):
        ev = vad.process(audio[i:i+512])
        if ev:
            events.append(ev)
    assert any(e == SpeechEvent.SPEECH_START for e in events)


def test_vad_silence_no_event():
    vad = VAD()
    audio = np.zeros(8000, dtype=np.float32)
    events = []
    for i in range(0, len(audio), 512):
        ev = vad.process(audio[i:i+512])
        if ev:
            events.append(ev)
    assert not any(e == SpeechEvent.SPEECH_START for e in events)
```

- [ ] **Step 2: Run test (expected fail)**

```powershell
pytest tests/test_vad.py -v
```

- [ ] **Step 3: Implement `vad.py`**

```python
from __future__ import annotations
import enum
import numpy as np
import torch
from silero_vad import load_silero_vad


class SpeechEvent(enum.Enum):
    SPEECH_START = "start"
    SPEECH_END = "end"


class VAD:
    """Streaming voice activity detector. Feed 16kHz mono chunks; receive START/END events."""

    def __init__(self, threshold: float = 0.5, min_silence_ms: int = 400, samplerate: int = 16000):
        self._model = load_silero_vad()
        self._threshold = threshold
        self._samplerate = samplerate
        self._min_silence_samples = int(samplerate * min_silence_ms / 1000)
        self._silence_run = 0
        self._in_speech = False

    def process(self, chunk: np.ndarray) -> SpeechEvent | None:
        # silero expects 512-sample windows at 16kHz
        if len(chunk) != 512:
            # pad or truncate
            if len(chunk) < 512:
                chunk = np.pad(chunk, (0, 512 - len(chunk)))
            else:
                chunk = chunk[:512]
        with torch.no_grad():
            prob = self._model(torch.from_numpy(chunk), self._samplerate).item()
        speaking = prob >= self._threshold
        if speaking:
            self._silence_run = 0
            if not self._in_speech:
                self._in_speech = True
                return SpeechEvent.SPEECH_START
        else:
            self._silence_run += len(chunk)
            if self._in_speech and self._silence_run >= self._min_silence_samples:
                self._in_speech = False
                return SpeechEvent.SPEECH_END
        return None

    def reset(self) -> None:
        self._silence_run = 0
        self._in_speech = False
```

- [ ] **Step 4: Run tests**

```powershell
pytest tests/test_vad.py -v
```

- [ ] **Step 5: Commit**

```powershell
git add src/dictado/vad.py tests/test_vad.py
git commit -m "feat: silero-vad streaming wrapper with START/END events"
```

---

### Task 2.2: Wire VAD into orchestrator for early end-of-speech

- [ ] **Step 1: Modify `main.py`**

Add VAD-driven flush: when VAD signals SPEECH_END while recording, trigger transcribe even if hotkey still held (for users who release late). Keep hotkey release as a secondary trigger.

```python
# In App.__init__:
self._vad = VAD()

# In _capture_loop:
async def _capture_loop(self) -> None:
    self._vad.reset()
    try:
        async for chunk in self._capture.stream():
            if not self._recording:
                break
            self._buffer.append(chunk)
            event = self._vad.process(chunk)
            if event == SpeechEvent.SPEECH_END:
                log.info("VAD: end of speech detected")
                # Optionally auto-flush mid-press; for now just log
    except asyncio.CancelledError:
        pass
```

(Auto-flush mid-press is a Phase 3 enhancement — Phase 2 just logs.)

- [ ] **Step 2: Smoke test**

```powershell
python -m dictado.main
# Hold Right Alt, say "hola" with a pause, then "mundo", release
# Watch logs — should see VAD: end of speech detected after the pause
```

- [ ] **Step 3: Commit**

```powershell
git add src/dictado/main.py
git commit -m "feat: integrate VAD into capture loop (logging only for now)"
```

---

### Task 2.3: Implement `postprocess.py` regex stage

**Files:**
- Create: `src/dictado/postprocess.py`
- Create: `tests/test_postprocess.py`

- [ ] **Step 1: Failing test**

`tests/test_postprocess.py`:
```python
from dictado.postprocess import PostProcessor


def test_removes_spanish_fillers():
    pp = PostProcessor(use_llm=False)
    assert pp.process("o sea quiero decir eh hola") == "Quiero decir hola"


def test_voice_command_newline():
    pp = PostProcessor(use_llm=False)
    assert pp.process("hola nueva línea mundo") == "Hola\nmundo"


def test_voice_command_comma():
    pp = PostProcessor(use_llm=False)
    assert pp.process("hola coma mundo") == "Hola, mundo"


def test_capitalizes_first_letter():
    pp = PostProcessor(use_llm=False)
    assert pp.process("hola mundo") == "Hola mundo"
```

- [ ] **Step 2: Implement `postprocess.py`**

```python
from __future__ import annotations
import re


FILLERS_ES = [r"\beh\b", r"\beste\b", r"\bo sea\b", r"\bpues\b", r"\bajá\b", r"\bmmm\b"]
FILLERS_EN = [r"\buh\b", r"\bum\b", r"\bahem\b", r"\blike\b(?=\s)"]
ALL_FILLERS = re.compile("|".join(FILLERS_ES + FILLERS_EN), re.IGNORECASE)

VOICE_COMMANDS = [
    (re.compile(r"\bnueva línea\b", re.IGNORECASE), "\n"),
    (re.compile(r"\bnew line\b", re.IGNORECASE), "\n"),
    (re.compile(r"\bpunto y aparte\b", re.IGNORECASE), ".\n\n"),
    (re.compile(r"\bcoma\b", re.IGNORECASE), ","),
    (re.compile(r"\bpunto\b", re.IGNORECASE), "."),
    (re.compile(r"\bdos puntos\b", re.IGNORECASE), ":"),
]


class PostProcessor:
    def __init__(self, use_llm: bool = True, llm=None, llm_min_words: int = 20):
        self._use_llm = use_llm
        self._llm = llm
        self._llm_min_words = llm_min_words

    def process(self, raw: str, force_llm: bool = False) -> str:
        text = self._regex_pass(raw)
        if self._use_llm and self._llm and (force_llm or len(text.split()) >= self._llm_min_words):
            text = self._llm.refine(text)
        return text

    def _regex_pass(self, text: str) -> str:
        # 1. Fillers
        text = ALL_FILLERS.sub("", text)
        # 2. Voice commands
        for pattern, replacement in VOICE_COMMANDS:
            text = pattern.sub(replacement, text)
        # 3. Collapse multi-space, fix space-before-punct
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"\s+([,.\n:])", r"\1", text)
        text = text.strip()
        # 4. Capitalize first character
        if text:
            text = text[0].upper() + text[1:]
        return text
```

- [ ] **Step 3: Run tests**

```powershell
pytest tests/test_postprocess.py -v
```
Expected: 4 passed.

- [ ] **Step 4: Wire into main**

In `main.py` `_transcribe_and_inject`:
```python
from dictado.postprocess import PostProcessor
self._postprocess = PostProcessor(use_llm=False)
...
text = await asyncio.to_thread(self._asr.transcribe, audio)
text = self._postprocess.process(text)
```

- [ ] **Step 5: Commit**

```powershell
git add src/dictado/postprocess.py tests/test_postprocess.py src/dictado/main.py
git commit -m "feat: regex postprocess for fillers and voice commands"
```

---

### Task 2.4: Implement `state.py` and `tray.py`

**Files:**
- Create: `src/dictado/state.py`
- Create: `src/dictado/tray.py`

- [ ] **Step 1: `state.py`**

```python
from __future__ import annotations
import enum
import threading
from typing import Callable


class AppState(enum.Enum):
    IDLE = "idle"
    LISTENING = "listening"
    TRANSCRIBING = "transcribing"
    ERROR = "error"


class StateMachine:
    def __init__(self):
        self._state = AppState.IDLE
        self._lock = threading.Lock()
        self._listeners: list[Callable[[AppState], None]] = []

    @property
    def state(self) -> AppState:
        return self._state

    def set(self, new: AppState) -> None:
        with self._lock:
            if self._state == new:
                return
            self._state = new
        for cb in self._listeners:
            try:
                cb(new)
            except Exception:
                pass

    def subscribe(self, cb: Callable[[AppState], None]) -> None:
        self._listeners.append(cb)
```

- [ ] **Step 2: `tray.py`**

```python
from __future__ import annotations
import threading
from PIL import Image, ImageDraw
import pystray

from dictado.state import AppState, StateMachine


_COLORS = {
    AppState.IDLE: (80, 80, 80),
    AppState.LISTENING: (60, 200, 100),
    AppState.TRANSCRIBING: (240, 200, 60),
    AppState.ERROR: (220, 60, 60),
}


def _make_icon(state: AppState) -> Image.Image:
    img = Image.new("RGB", (64, 64), (32, 32, 32))
    d = ImageDraw.Draw(img)
    d.ellipse((8, 8, 56, 56), fill=_COLORS[state])
    return img


class Tray:
    def __init__(self, sm: StateMachine, on_quit):
        self._sm = sm
        self._on_quit = on_quit
        self._icon = pystray.Icon(
            "dictado",
            _make_icon(sm.state),
            "Dictado — idle",
            menu=pystray.Menu(
                pystray.MenuItem("Quit", self._quit),
            ),
        )
        sm.subscribe(self._on_state)

    def _on_state(self, state: AppState) -> None:
        self._icon.icon = _make_icon(state)
        self._icon.title = f"Dictado — {state.value}"

    def _quit(self, icon, item):
        self._icon.stop()
        self._on_quit()

    def start_thread(self) -> threading.Thread:
        t = threading.Thread(target=self._icon.run, daemon=True)
        t.start()
        return t
```

- [ ] **Step 3: Wire into `main.py`**

```python
from dictado.state import AppState, StateMachine
from dictado.tray import Tray

# in App.__init__
self._sm = StateMachine()

# in _start_recording
self._sm.set(AppState.LISTENING)

# in _stop_recording (start of)
self._sm.set(AppState.TRANSCRIBING)

# in _transcribe_and_inject (end of, in finally)
self._sm.set(AppState.IDLE)

# in run()
tray = Tray(self._sm, on_quit=self._loop.stop)
tray.start_thread()
```

- [ ] **Step 4: Manual smoke test**

```powershell
python -m dictado.main
# Verify tray icon appears, changes color when holding hotkey, returns to grey when done
```

- [ ] **Step 5: Commit**

```powershell
git add src/dictado/state.py src/dictado/tray.py src/dictado/main.py
git commit -m "feat: state machine + tray icon with status colors"
```

---

### Task 2.5: Tag Phase 2

```powershell
git tag -a phase2-quality -m "Phase 2: VAD + regex + tray"
```

Update README status. Commit.

---

## Chunk 3: Phase 3 — LLM postprocess, voice commands, app context

Goal: latencia <600ms en frases cortas; corrección semántica con LLM en frases largas; reglas específicas según la app activa.

### Task 3.1: Install llama-cpp-python with CUDA and download Phi-3-mini

- [ ] **Step 1: Install with CUDA wheel**

```powershell
pip install --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu121/ llama-cpp-python
python -c "from llama_cpp import Llama; print('OK')"
```
Expected: prints OK.

- [ ] **Step 2: Download Phi-3-mini Q4_K_M**

```powershell
mkdir models -ErrorAction SilentlyContinue
# Use huggingface-hub or direct download:
pip install huggingface-hub
python -c "from huggingface_hub import hf_hub_download; print(hf_hub_download('microsoft/Phi-3-mini-4k-instruct-gguf', 'Phi-3-mini-4k-instruct-q4.gguf', local_dir='models'))"
```
Expected: ~2.3GB file at `models/Phi-3-mini-4k-instruct-q4.gguf`.

- [ ] **Step 3: Verify GPU offload works**

```powershell
python -c "from llama_cpp import Llama; m = Llama(model_path='models/Phi-3-mini-4k-instruct-q4.gguf', n_gpu_layers=-1, n_ctx=2048, verbose=False); print(m('Hola, ¿cómo estás?', max_tokens=10)['choices'][0]['text'])"
```
Expected: prints a short Spanish response. Watch GPU usage in `nvidia-smi` — should hit ~3GB VRAM.

- [ ] **Step 4: Commit `.gitignore` update**

Confirm `models/` and `*.gguf` are gitignored (already from Task 1.1). No commit needed.

---

### Task 3.2: Implement `llm.py` and wire into `postprocess.py`

**Files:**
- Create: `src/dictado/llm.py`
- Modify: `src/dictado/postprocess.py`
- Modify: `tests/test_postprocess.py`

- [ ] **Step 1: Implement `llm.py`**

```python
from __future__ import annotations
from llama_cpp import Llama


SYSTEM_PROMPT = (
    "Eres un asistente de dictado. Corrige gramática y puntuación del texto adjunto. "
    "Mantén el idioma original. NO agregues introducciones, comentarios ni explicaciones. "
    "Devuelve SOLO el texto corregido."
)


class LocalLLM:
    def __init__(
        self,
        model_path: str = "models/Phi-3-mini-4k-instruct-q4.gguf",
        n_gpu_layers: int = -1,
        n_ctx: int = 2048,
    ):
        self._llm = Llama(
            model_path=model_path,
            n_gpu_layers=n_gpu_layers,
            n_ctx=n_ctx,
            verbose=False,
        )

    def refine(self, text: str) -> str:
        prompt = f"<|system|>\n{SYSTEM_PROMPT}<|end|>\n<|user|>\n{text}<|end|>\n<|assistant|>\n"
        out = self._llm(
            prompt,
            max_tokens=min(512, len(text.split()) * 4 + 64),
            temperature=0.1,
            stop=["<|end|>", "<|user|>"],
        )
        refined = out["choices"][0]["text"].strip()
        # Safety: if the LLM doubled the length or returned empty, fall back to input
        if not refined or len(refined) > len(text) * 2.5:
            return text
        return refined
```

- [ ] **Step 2: Add LLM test (slow, marked)**

`tests/test_postprocess.py` (append):
```python
import pytest

@pytest.mark.slow
def test_llm_fixes_grammar():
    from dictado.llm import LocalLLM
    pp = PostProcessor(use_llm=True, llm=LocalLLM(), llm_min_words=1)
    out = pp.process("yo querer ir a la tienda mañana")
    assert "quiero" in out.lower() or "querer" not in out.lower()
```

Register marker in `pyproject.toml`:
```toml
[tool.pytest.ini_options]
markers = ["slow: requires GPU + downloaded models"]
```

- [ ] **Step 3: Run fast tests + run slow once**

```powershell
pytest -v -m "not slow"
pytest -v -m slow
```

- [ ] **Step 4: Wire LLM into main**

In `main.py`:
```python
from dictado.llm import LocalLLM
# lazy-load like ASR
self._llm = None
# in _transcribe_and_inject after model load:
if self._llm is None:
    self._llm = LocalLLM()
self._postprocess = PostProcessor(use_llm=True, llm=self._llm, llm_min_words=20)
```

- [ ] **Step 5: Commit**

```powershell
git add src/dictado/llm.py src/dictado/postprocess.py tests/test_postprocess.py src/dictado/main.py pyproject.toml
git commit -m "feat: Phi-3-mini LLM refinement stage in postprocess"
```

---

### Task 3.3: Implement `app_context.py`

**Files:**
- Create: `src/dictado/app_context.py`
- Create: `tests/test_app_context.py`

- [ ] **Step 1: Failing test**

```python
from dictado.app_context import parse_window_title, AppContext


def test_parse_known_app():
    ctx = parse_window_title("code.exe", "main.py - dictado - Visual Studio Code")
    assert ctx.app_kind == "vscode"


def test_parse_unknown_app():
    ctx = parse_window_title("randomthing.exe", "foo")
    assert ctx.app_kind == "unknown"
```

- [ ] **Step 2: Implement**

```python
from __future__ import annotations
from dataclasses import dataclass
import win32gui
import win32process
import psutil


@dataclass
class AppContext:
    exe: str
    title: str
    app_kind: str  # "vscode" | "slack" | "browser" | "word" | "terminal" | "unknown"


_KIND_MAP = {
    "code.exe": "vscode",
    "slack.exe": "slack",
    "chrome.exe": "browser",
    "firefox.exe": "browser",
    "msedge.exe": "browser",
    "winword.exe": "word",
    "windowsterminal.exe": "terminal",
    "powershell.exe": "terminal",
    "cmd.exe": "terminal",
}


def parse_window_title(exe: str, title: str) -> AppContext:
    return AppContext(exe=exe, title=title, app_kind=_KIND_MAP.get(exe.lower(), "unknown"))


def get_active_app() -> AppContext:
    try:
        hwnd = win32gui.GetForegroundWindow()
        title = win32gui.GetWindowText(hwnd)
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        exe = psutil.Process(pid).name()
    except Exception:
        return AppContext("", "", "unknown")
    return parse_window_title(exe, title)
```

Add `psutil` to deps in `pyproject.toml`.

- [ ] **Step 3: Add app-context-aware rule in postprocess**

In `postprocess.py`, add optional `app_kind` param to `process()`:
```python
def process(self, raw: str, app_kind: str = "unknown", force_llm: bool = False) -> str:
    text = self._regex_pass(raw)
    if app_kind == "vscode":
        # don't aggressively correct — code dictation likely
        return text
    if self._use_llm and self._llm and (force_llm or len(text.split()) >= self._llm_min_words):
        text = self._llm.refine(text)
    return text
```

- [ ] **Step 4: Wire into main**

```python
from dictado.app_context import get_active_app
# in _transcribe_and_inject
ctx = get_active_app()
text = self._postprocess.process(text, app_kind=ctx.app_kind)
```

- [ ] **Step 5: Run tests + commit**

```powershell
pytest -v -m "not slow"
git add src/dictado/app_context.py tests/test_app_context.py src/dictado/postprocess.py src/dictado/main.py pyproject.toml
git commit -m "feat: detect active app and skip LLM correction in code editors"
```

---

### Task 3.4: VAD-driven mid-press flush (optional polish)

If recordings are long and pause-prone, flush ASR mid-press when VAD detects a long pause, so transcription progresses while user keeps holding the key.

- [ ] **Step 1: Add streaming flush logic in `_capture_loop`**

```python
event = self._vad.process(chunk)
if event == SpeechEvent.SPEECH_END:
    # Flush current buffer to ASR in background; keep recording
    audio = np.concatenate(list(self._buffer))
    self._buffer.clear()
    self._loop.create_task(self._inject_partial(audio))
```

- [ ] **Step 2: Smoke test**

Speak with long pauses; verify partials appear before key release.

- [ ] **Step 3: Commit**

```powershell
git add src/dictado/main.py
git commit -m "feat: mid-press flush on VAD speech-end"
```

---

### Task 3.5: Tag Phase 3

```powershell
git tag -a phase3-intelligence -m "Phase 3: LLM + app-aware + mid-press flush"
```

---

## Chunk 4: Phase 4 — Config, error handling, packaging

Goal: usable como app real instalable, con config editable, errores manejados, instalador `.exe`.

### Task 4.1: Implement `config.py`

**Files:**
- Create: `src/dictado/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Implement**

```python
from __future__ import annotations
import os
import tomllib
import tomli_w
from dataclasses import dataclass, asdict, field
from pathlib import Path


@dataclass
class HotkeyCfg:
    key: str = "alt_r"
    mode: str = "hold"


@dataclass
class ASRCfg:
    model: str = "distil-whisper/distil-large-v3"
    compute_type: str = "int8"
    language: str = "auto"


@dataclass
class PostprocessCfg:
    use_llm: bool = True
    llm_model: str = "models/Phi-3-mini-4k-instruct-q4.gguf"
    llm_min_words: int = 20


@dataclass
class InjectorCfg:
    mode: str = "auto"


@dataclass
class Config:
    hotkey: HotkeyCfg = field(default_factory=HotkeyCfg)
    asr: ASRCfg = field(default_factory=ASRCfg)
    postprocess: PostprocessCfg = field(default_factory=PostprocessCfg)
    injector: InjectorCfg = field(default_factory=InjectorCfg)


def config_path() -> Path:
    base = Path(os.environ.get("APPDATA", str(Path.home())))
    return base / "dictado" / "config.toml"


def load(path: Path | None = None) -> Config:
    path = path or config_path()
    if not path.exists():
        cfg = Config()
        save(cfg, path)
        return cfg
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    return Config(
        hotkey=HotkeyCfg(**raw.get("hotkey", {})),
        asr=ASRCfg(**raw.get("asr", {})),
        postprocess=PostprocessCfg(**raw.get("postprocess", {})),
        injector=InjectorCfg(**raw.get("injector", {})),
    )


def save(cfg: Config, path: Path | None = None) -> None:
    path = path or config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(tomli_w.dumps(asdict(cfg)).encode("utf-8"))
```

- [ ] **Step 2: Tests, wire into main, commit**

`tests/test_config.py`:
```python
from dictado.config import Config, save, load

def test_roundtrip(tmp_path):
    cfg = Config()
    cfg.hotkey.key = "ctrl_r"
    p = tmp_path / "config.toml"
    save(cfg, p)
    cfg2 = load(p)
    assert cfg2.hotkey.key == "ctrl_r"
```

In `main.py`:
```python
from dictado.config import load as load_config
cfg = load_config()
# use cfg.hotkey.key, cfg.hotkey.mode, etc.
```

```powershell
pytest -v -m "not slow"
git add src/dictado/config.py tests/test_config.py src/dictado/main.py
git commit -m "feat: TOML config loaded from %APPDATA%/dictado/config.toml"
```

---

### Task 4.2: Add `logging_setup.py` with rotation

- [ ] **Step 1: Create**

```python
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import os


def setup():
    base = Path(os.environ.get("APPDATA", str(Path.home()))) / "dictado" / "logs"
    base.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(base / "dictado.log", maxBytes=5_000_000, backupCount=3, encoding="utf-8")
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    handler.setFormatter(fmt)
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)
    # also keep console
    console = logging.StreamHandler()
    console.setFormatter(fmt)
    root.addHandler(console)
```

Wire from `main.py`:
```python
from dictado.logging_setup import setup as setup_logging
setup_logging()
```

```powershell
git add src/dictado/logging_setup.py src/dictado/main.py
git commit -m "feat: rotating log file in %APPDATA%/dictado/logs"
```

---

### Task 4.3: Error handling pass

For each failure point in the spec §6, add explicit handling:

- [ ] **CUDA OOM** in `asr.py`: catch on load → retry with `distil-whisper/distil-small.en`; set state ERROR.
- [ ] **Audio device disconnect** in `audio_capture.py`: catch `sd.PortAudioError` in `_callback` → log + reset stream.
- [ ] **Hotkey conflict**: on `HotkeyListener.start()` failure, log and prompt user to change config.
- [ ] **LLM hang**: wrap `LocalLLM.refine` in `asyncio.wait_for(timeout=2.0)`; on timeout, return original text.
- [ ] **Clipboard injection fail**: already handled by fallback in `injector.py`.

Add tests for the CUDA OOM fallback (mock `WhisperModel` to raise).

```powershell
git add src/dictado/
git commit -m "feat: error handling for OOM, device loss, LLM timeout, hotkey conflict"
```

---

### Task 4.4: Package with PyInstaller

- [ ] **Step 1: Create entry script**

`scripts/build.ps1`:
```powershell
pip install pyinstaller
pyinstaller `
  --name dictado `
  --windowed `
  --onefile `
  --icon assets/icon.ico `
  --add-data "models;models" `
  --hidden-import pystray._win32 `
  --hidden-import win32timezone `
  src/dictado/main.py
```

- [ ] **Step 2: Build**

```powershell
.\scripts\build.ps1
# Output: dist/dictado.exe
```

- [ ] **Step 3: Smoke-test the .exe**

Move `dist/dictado.exe` to a clean Windows machine (or a fresh user profile). Run. Verify it launches tray and the hotkey works.

- [ ] **Step 4: Document install path in README**

Add a "Releases" section pointing at GitHub Releases artifact (manual upload OK for now).

- [ ] **Step 5: Commit**

```powershell
git add scripts/build.ps1 README.md
git commit -m "build: PyInstaller config for standalone .exe"
```

---

### Task 4.5: Final integration smoke tests

Run the manual checklist from spec §7:

- [ ] Dictar 10 palabras en Notepad → texto aparece sin errores
- [ ] Dictar mezclando ES/EN → idioma detectado
- [ ] Sostener tecla 30s → no se cuelga
- [ ] Comandos de voz ("nueva línea", "coma") → mapean correcto
- [ ] Cambiar entre Slack y VS Code → reglas aplican
- [ ] Latencia p50 <500ms (medir con timestamps en logs)

Document results in `docs/superpowers/test-results-phase4.md`.

```powershell
git add docs/
git commit -m "test: phase 4 smoke test results"
git tag -a v0.1.0 -m "First usable release"
```

---

## Verification Checklist (final)

Before declaring done, run:

```powershell
# All fast tests pass
pytest -v -m "not slow"

# Slow tests pass (with GPU)
pytest -v -m slow

# Lint clean
ruff check src/ tests/

# Build succeeds
.\scripts\build.ps1

# .exe runs on fresh shell
dist\dictado.exe
```

Expected: all green. App launches with tray icon. Holding Right Alt records and pastes transcribed text. Latency feels instant (<500ms perceived).

---

## Notes for the executing engineer

- **Always TDD** for `hotkey`, `postprocess`, `config`, `app_context` (pure logic, easy to test).
- **Manual smoke tests acceptable** for `audio_capture`, `asr`, `injector`, `tray` (hardware/UI integration).
- **Commit per task** — keep history granular so reverts are surgical.
- **Don't optimize prematurely** — Phase 1 must work end-to-end before adding VAD/LLM.
- **GPU contention:** if RTX 3080 is busy (game, training), CUDA OOM → fallback path kicks in. That's expected.
- **Phi-3-mini's system prompt** is sensitive; if it starts adding "Here is the corrected text:", tighten the prompt or add a regex strip.
- **Don't add features not in this plan** without updating the spec first.

---

## Skills to reference during execution

- `superpowers:test-driven-development` for every src file with logic tests
- `superpowers:systematic-debugging` if something breaks unexpectedly
- `superpowers:verification-before-completion` before claiming a phase done
- `superpowers:requesting-code-review` before merging Phase 1 (if working in a branch)
