# Miru Voice — Windows

Local push-to-talk dictation. Hold a hotkey, speak, release. Text gets pasted into the focused app. 100% on-device — audio never leaves your PC.

---

## Prerequisites

You **must** have all of these before installing:

| Requirement | Minimum | Tested on | How to check |
|---|---|---|---|
| OS | Windows 10 (1909+) | Windows 11 | `winver` |
| GPU | NVIDIA with **≥8 GB VRAM** | RTX 3080 (10 GB) | `nvidia-smi` |
| NVIDIA driver | 525+ for CUDA 12.x | 591.86 | `nvidia-smi` first line |
| Python | 3.11 | 3.12.5 | `python --version` |
| Free disk | ~5 GB | — | for venv + Whisper model |
| Microphone | Any working input | Logitech C920 webcam mic | Windows Settings → Sound |

**No NVIDIA GPU?** Won't work without modifications — see [Modify](#modify-it) section to swap ASR to CPU (very slow on Windows; not recommended).

**AMD/Intel GPU?** Same issue — CTranslate2 only supports CUDA. You'd need to switch to a different ASR backend.

---

## Install

Open PowerShell at the `windows/` folder of this repo, then:

### 1. Create a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If `Activate.ps1` is blocked by execution policy, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once and accept the prompt.

### 2. Install dependencies

```powershell
pip install --upgrade pip
pip install -e ".[dev]"
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

PyTorch CPU is fine — only `silero-vad` uses it, and that runs on CPU. Don't install a CUDA PyTorch unless you plan to use it for something else; it's a 2 GB download you don't need.

### 3. Fix the cuBLAS DLL issue (required on first install)

`faster-whisper` needs `cublas64_12.dll` and `cublasLt64_12.dll` at runtime. The NVIDIA driver alone doesn't install these — only the full CUDA Toolkit does. Workaround: grab them from a pip package and copy into the `ctranslate2` folder:

```powershell
pip install nvidia-cublas-cu12
$src = ".\.venv\Lib\site-packages\nvidia\cublas\bin"
$dst = ".\.venv\Lib\site-packages\ctranslate2"
Copy-Item "$src\cublas64_12.dll", "$src\cublasLt64_12.dll" $dst
```

You'll need to redo this step every time you recreate `.venv`. Skip if you already have CUDA Toolkit 12.x installed system-wide.

### 4. First run downloads the Whisper model

`Systran/faster-whisper-large-v3` is ~800 MB. Pre-download so the first dictation isn't a 2-minute surprise:

```powershell
.\.venv\Scripts\python.exe -c "from faster_whisper import WhisperModel; WhisperModel('Systran/faster-whisper-large-v3', device='cuda', compute_type='int8'); print('OK')"
```

Cached in `%USERPROFILE%\.cache\huggingface`.

---

## Run

### From PowerShell

```powershell
.\.venv\Scripts\python.exe -m miru_voice.main
```

You'll see:
```
... INFO ready — hold Left Ctrl + Space to dictate. Ctrl+C to quit.
```

### From a desktop / taskbar shortcut

Generate a shortcut once:

```powershell
.\scripts\install_shortcut.ps1
```

This creates `Miru Voice.lnk` on your Desktop and in the Start Menu. To pin to taskbar on Windows 11:

1. Double-click the Desktop shortcut → app launches minimized
2. Right-click the taskbar icon → **Pin to taskbar**
3. From now on, clicking the taskbar pin launches Miru Voice

### What to expect

- First click: **~10-15 second pause** while the model loads to VRAM
- After load: **~600-900 ms** from key release to text paste (no VAD / LLM yet — Phase 2/3 work)
- Window starts minimized; click the taskbar icon to see logs
- Close the window or `Ctrl+C` to quit

### Usage

1. Click in any app (Notepad, Slack, browser, etc.) so the cursor is there
2. **Hold `Left Ctrl + Space`** together
3. Speak (Spanish, English, or mixed — auto-detected)
4. **Release** either key → transcription pastes via clipboard + Ctrl+V

---

## Modify it

All defaults live in `src/miru_voice/main.py` and the four submodules. No config file yet (that's Phase 4 work). Edit the source and re-run.

### Change the hotkey

In `src/miru_voice/main.py`, find:

```python
listener = HotkeyListener(
    keys=["ctrl_l", "space"], mode="hold", on_event=self._on_hotkey
)
```

Replace `keys=...` with one of:

| Want | Use |
|---|---|
| Single Caps Lock | `keys="caps_lock"` |
| Right Ctrl (single) | `keys="ctrl_r"` |
| F12 function key | `keys="f12"` |
| AltGr / Right Alt | `keys="alt_gr"` |
| Right Ctrl + Space | `keys=["ctrl_r", "space"]` |
| Ctrl + Shift + Space | `keys=["ctrl_l", "shift_l", "space"]` |

Available single keys: `alt_l`, `alt_r`, `alt_gr`, `ctrl_l`, `ctrl_r`, `shift_l`, `shift_r`, `space`, `caps_lock`, `f9`, `f10`, `f12`. Full list in `src/miru_voice/hotkey.py:_KEY_MAP`.

`mode` options:
- `"hold"` — record while held (default, recommended)
- `"toggle"` — press to start, press again to stop

### Change the ASR model

In `src/miru_voice/asr.py`, the default is `Systran/faster-whisper-large-v3` (multilingual, ~800 MB, best accuracy). Swap for:

| Model | Size (int8) | Latency on RTX 3080 | Use case |
|---|---|---|---|
| `Systran/faster-whisper-large-v3` | 800 MB | ~600-900 ms | Default. Best accuracy ES + EN. |
| `Systran/faster-whisper-large-v3-turbo` | 800 MB | ~250-400 ms | Same quality, decoder distilled. **Worth trying.** |
| `Systran/faster-whisper-medium` | 470 MB | ~200-300 ms | Good quality, less VRAM. |
| `Systran/faster-whisper-small` | 240 MB | ~100-150 ms | Lower quality but very fast. |
| `Systran/faster-distil-whisper-large-v3` | 750 MB | ~150-250 ms | **English ONLY** — don't use if you need Spanish. |

Edit the default in the `ASR.__init__` signature:

```python
def __init__(
    self,
    model: str = "Systran/faster-whisper-large-v3-turbo",   # ← change here
    compute_type: str = "int8",
    device: str = "cuda",
    ...
```

Then pre-download:

```powershell
.\.venv\Scripts\python.exe -c "from faster_whisper import WhisperModel; WhisperModel('Systran/faster-whisper-large-v3-turbo', device='cuda', compute_type='int8')"
```

### Force a language (skip auto-detect)

Auto-detect adds ~50 ms and occasionally picks wrong on short utterances. Force a language in `src/miru_voice/main.py`:

```python
text = await asyncio.to_thread(self._asr.transcribe, audio, "es")  # or "en"
```

(Current call is `self._asr.transcribe, audio` — append the language arg.)

### Change paste behavior

In `src/miru_voice/main.py`, the orchestrator does `self._injector = TextInjector()` which defaults to `mode="auto"` (paste, fallback to typing on error). To force one or the other:

```python
self._injector = TextInjector(mode="paste")   # paste only — error if blocked
self._injector = TextInjector(mode="type")    # always type character-by-character (slower but works in any app)
```

Also: `restore_clipboard=False` skips the clipboard restore (faster, but wipes whatever you had copied before).

### Change the silence threshold

In `src/miru_voice/main.py`, `_transcribe_and_inject` skips recordings with RMS < 0.005. If your mic is quiet, lower it:

```python
if rms < 0.001:   # was 0.005
    log.info("silence skip (rms=%.4f)", rms)
    return
```

### Where are the logs

Right now, only console output (the window the app runs in). Phase 4 will add a rotating log file at `%APPDATA%\miru-voice\logs\miru-voice.log`.

---

## Troubleshooting

**`cublas64_12.dll not found`** → Redo the step-3 cuBLAS DLL copy after each venv rebuild.

**`Could not load library libcudnn_ops.so.X`** → Install cuDNN for CUDA 12 (full toolkit install, or `pip install nvidia-cudnn-cu12` and copy DLLs the same way as cuBLAS).

**App ready but `Left Ctrl + Space` does nothing** → Run `scripts/debug_keys.py` and check what your keys report. Some keyboards (Spanish layout) send `alt_gr` instead of `alt_r`. Edit `_KEY_MAP` if needed.

**Recording start/stop logs but no transcription** → Mic is silent. Run `scripts/debug_audio.py` to check RMS. Common cause: default input is the wrong device. Set `device=N` in `AudioCapture()` constructor with N from the device list debug_audio prints.

**`PortAudioError -9984 Incompatible host API`** → Already handled by automatic fallback (commit `a06476d`). If it still happens, check the device's host API isn't fully broken.

**App pastes English when you spoke Spanish** → Wrong model. Verify `src/miru_voice/asr.py` uses `Systran/faster-whisper-large-v3` (or any non-distil variant). `distil-whisper-large-v3` is English-only.

**Multiple miru-voice processes running** → Each click of the taskbar pin launches a new instance. Check Task Manager → kill duplicates. Singleton lock is Phase 2 work.

---

## Test

```powershell
.\.venv\Scripts\python.exe -m pytest -v -m "not slow"   # unit tests only
.\.venv\Scripts\python.exe -m pytest -v -m slow          # also runs the ASR tests (loads model)
```

8 fast tests + 2 slow ASR tests. All should pass.

---

## Status

- [x] Phase 1: MVP — hotkey + ASR + paste
- [ ] Phase 2: VAD + regex postprocess + tray icon
- [ ] Phase 3: LLM postprocess + voice commands + app context
- [ ] Phase 4: Packaging (`.exe` via PyInstaller), config file, rotating logs

Roadmap and design in `../docs/superpowers/`.
