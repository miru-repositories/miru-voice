# Miru Voice — macOS

Local push-to-talk dictation. Hold a hotkey, speak, release. Text gets pasted via Cmd+V into the focused app. 100% on-device — audio never leaves your Mac.

> **Status:** Port from the Windows version. Code is written but **not yet validated on real hardware**. Expect minor rough edges; please report what you find.

---

## Prerequisites

| Requirement | Minimum | Recommended | How to check |
|---|---|---|---|
| OS | macOS 12 Monterey | macOS 14+ Sonoma | Apple menu → About This Mac |
| Architecture | x86_64 (Intel) | **arm64 (Apple Silicon)** | `uname -m` → `arm64` ✓ |
| Python | 3.11 | 3.12 | `python3 --version` |
| Free disk | ~3 GB | — | for venv + Whisper model |
| Microphone | Any working input | — | System Settings → Sound → Input |
| Accessibility | Must be granted to Python | — | System Settings → Privacy & Security → Accessibility |
| Homebrew | optional | yes (for `python@3.12`) | `brew --version` |

**On Intel Mac**: works but ASR runs on CPU only and is **slow**. See [Performance](#performance) and [Modify](#modify-it) — you'll want a smaller Whisper model.

**On Apple Silicon (M1+)**: CPU is fast enough for `large-v3` to feel real-time. Even better performance is possible with `mlx-whisper` or `whisper.cpp` Metal — see [Modify](#modify-it).

---

## Install

Open Terminal at the `macos/` folder of this repo.

### 1. Install Python 3.11+ if you don't have it

Easiest with Homebrew:

```bash
brew install python@3.12
```

### 2. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

(The `source` line activates the venv. You'll re-run it every new Terminal session.)

### 3. Install dependencies

```bash
pip install --upgrade pip
pip install -e ".[dev]"
```

This installs `sounddevice`, `faster-whisper`, `pynput`, `pyperclip`, `silero-vad`, and dev tools. Total ~1 GB.

`pyperclip` on macOS uses the system `pbcopy`/`pbpaste` binaries — already on every Mac, no extra steps.

### 4. Grant Accessibility permission

pynput needs Accessibility access to:
- Register the global hotkey (otherwise key presses don't reach the listener)
- Simulate the Cmd+V keystroke (otherwise paste silently fails)

Steps:
1. Open **System Settings → Privacy & Security → Accessibility**
2. Click the **+** button
3. Navigate to your venv's Python and add it:
   `/path/to/your/miru-voice/macos/.venv/bin/python3.12`
4. Toggle the new entry **ON**

Alternative: instead of adding the Python binary, add the **Terminal** app (or **iTerm**, **VS Code**, whatever you launch `python -m miru_voice.main` from). Easier but coarser (gives any tool you run that permission).

After granting permission, you may need to **quit and reopen** Terminal for it to take effect.

### 5. Microphone permission

The first time you run miru-voice, macOS will ask for microphone access. Click **OK**. If you accidentally clicked "Don't Allow", re-enable in **System Settings → Privacy & Security → Microphone**.

### 6. First run downloads the Whisper model

`Systran/faster-whisper-large-v3` is ~800 MB. Pre-download:

```bash
python -c "from faster_whisper import WhisperModel; WhisperModel('Systran/faster-whisper-large-v3', device='cpu', compute_type='int8'); print('OK')"
```

Cached at `~/.cache/huggingface/`. Takes 2-5 minutes depending on network.

---

## Run

```bash
source .venv/bin/activate
python -m miru_voice.main
```

You'll see:
```
... INFO ready — hold Right Option (⌥) to dictate. Ctrl+C to quit.
```

### Usage

1. Click in any app where you want text (TextEdit, Slack, Notes, browser, etc.)
2. **Hold the Right Option key (⌥)** on the right side of the spacebar
3. Speak (Spanish, English, or mixed — auto-detected)
4. **Release** → transcription pastes via Cmd+V

### What to expect

- First press: **~5-15 second pause** while Whisper loads to RAM
- After load on Apple Silicon: **~600-1000 ms** from release to paste
- Console shows logs; `Ctrl+C` quits

### Create a Dock shortcut (optional)

There's no `.app` bundle yet (Phase 4 work), but you can create a simple alias:

```bash
# Save this as a shell script and drop it into /Applications/Miru Voice.command
#!/usr/bin/env bash
cd "/path/to/your/miru-voice/macos"
source .venv/bin/activate
python -m miru_voice.main
```

Then `chmod +x Miru Voice.command` and drag onto the Dock. Clicking it opens Terminal and starts miru-voice. Not pretty, but works.

For a real `.app` bundle, see [Phase 4 status](#status).

---

## Modify it

All defaults live in `src/miru_voice/main.py` and the submodules. No config file yet (Phase 4). Edit the source and re-run.

### Change the hotkey

In `src/miru_voice/main.py`, find:

```python
listener = HotkeyListener(keys="alt_r", mode="hold", on_event=self._on_hotkey)
```

Replace `keys=...` with one of:

| Want | Use | Caveat |
|---|---|---|
| Caps Lock (single) | `keys="caps_lock"` | macOS toggles caps; tap-vs-hold can feel weird |
| F13 / F14 (single) | `keys="f13"` | Only on extended keyboards |
| Left Option (single) | `keys="alt_l"` | |
| Right Cmd (single) | `keys="cmd_r"` | |
| Ctrl + Space | `keys=["ctrl_l", "space"]` | **Conflicts with IME switcher** if you have multiple input sources |
| Cmd + Shift + D | `keys=["cmd_l", "shift_l", "d"]` | Letter keys not yet in map — add to `_KEY_MAP` first |

Available single keys: `alt_l`, `alt_r`, `ctrl_l`, `ctrl_r`, `cmd_l`, `cmd_r`, `shift_l`, `shift_r`, `space`, `caps_lock`, `f12`, `f13`, `f14`. Full list in `src/miru_voice/hotkey.py:_KEY_MAP`.

**Avoid these combos** (system-reserved on macOS):
- `["cmd_l", "space"]` — Spotlight
- `["ctrl_l", "space"]` — IME switcher (if multiple input sources)
- `["cmd_l", "tab"]` — App switcher
- `["fn"]` alone — Dictation (Apple's, conflicts with us)

`mode` options:
- `"hold"` — record while held (default, recommended)
- `"toggle"` — press to start, press again to stop

### Change the ASR model

Default `Systran/faster-whisper-large-v3` (multilingual, ~800 MB) is the best quality. On slower hardware, swap down:

| Model | Size (int8) | Latency (M1 base) | Latency (Intel i7) | Use case |
|---|---|---|---|---|
| `Systran/faster-whisper-large-v3` | 800 MB | ~800-1200 ms | ~3-5 s | Default. Best quality. |
| `Systran/faster-whisper-large-v3-turbo` | 800 MB | ~300-500 ms | ~1-2 s | **Try this on Apple Silicon.** Same quality, faster decoder. |
| `Systran/faster-whisper-medium` | 470 MB | ~200-400 ms | ~1-2 s | Good quality, faster. |
| `Systran/faster-whisper-small` | 240 MB | ~100-200 ms | ~500 ms | Best for old Intel Macs. WER ~15 % ES. |
| `Systran/faster-whisper-base` | 145 MB | ~50-100 ms | ~200 ms | Acceptable for testing, lower quality. |
| `Systran/faster-distil-whisper-large-v3` | 750 MB | — | — | **English ONLY** — don't use if you need Spanish. |

Edit the default in `src/miru_voice/asr.py`:

```python
def __init__(
    self,
    model: str = "Systran/faster-whisper-large-v3-turbo",   # ← change here
    compute_type: str = "int8",
    device: str = "cpu",
    ...
```

Then pre-download:

```bash
python -c "from faster_whisper import WhisperModel; WhisperModel('Systran/faster-whisper-large-v3-turbo', device='cpu', compute_type='int8')"
```

### Switch ASR backend to mlx-whisper or whisper.cpp (Apple Silicon only)

CTranslate2 (what faster-whisper uses) has no Metal backend on macOS, so ASR is CPU-only. Two faster options on Apple Silicon:

**`mlx-whisper`** (Apple's MLX framework, native Metal):
```bash
pip install mlx-whisper
```
Then replace `src/miru_voice/asr.py` to call `mlx_whisper.transcribe(...)` instead. Expected ~2-3x speedup over faster-whisper CPU on M1+.

**`whisper.cpp`** (mature C++ with Metal):
```bash
brew install whisper-cpp
```
Then shell out to the `whisper` binary or use `pywhispercpp` bindings. More fiddly to integrate but production-proven.

Both are beyond Phase 1 scope — flagged here for future tuning.

### Force a language (skip auto-detect)

Auto-detect occasionally picks wrong on short utterances. In `src/miru_voice/main.py`:

```python
text = await asyncio.to_thread(self._asr.transcribe, audio, "es")   # or "en"
```

(Append `"es"` or `"en"` as the second arg.)

### Change paste behavior

In `src/miru_voice/main.py`, `self._injector = TextInjector()` defaults to `mode="auto"` (paste, fallback to typing on error). Force one:

```python
self._injector = TextInjector(mode="paste")   # paste only — raise on failure
self._injector = TextInjector(mode="type")    # always type character-by-character (works in any app)
```

`restore_clipboard=False` skips restoring your prior clipboard content (faster but lossy).

### Change the silence threshold

In `src/miru_voice/main.py`, the orchestrator skips audio with RMS < 0.005. If your mic is quiet:

```python
if rms < 0.001:   # was 0.005
    log.info("silence skip (rms=%.4f)", rms)
    return
```

### Where are the logs

Console output only — the Terminal where you ran `python -m miru_voice.main`. Phase 4 will add a rotating log at `~/Library/Logs/miru-voice/miru-voice.log`.

---

## Troubleshooting

**App ready but Right Option does nothing** → Accessibility permission missing. Re-check System Settings, and **quit/reopen Terminal** for it to apply.

**Paste silently fails** → Same Accessibility permission. Without it, pynput's keyboard simulation is a no-op.

**Microphone permission popup never showed** → First launch should trigger it. If it didn't, you may have denied a previous attempt. Reset in System Settings → Privacy & Security → Microphone.

**Recording start/stop logs but no transcription** → Mic is silent or wrong device. Run a quick capture test:

```bash
python -c "import sounddevice as sd; print(sd.query_devices())"
```

Find your mic in the list and set its index in `AudioCapture(device=N)` if not default.

**App pastes English when you spoke Spanish** → Wrong model. Verify `src/miru_voice/asr.py` uses `Systran/faster-whisper-large-v3` (or any non-distil variant). `distil-whisper-large-v3` is English-only.

**`pyperclip.PyperclipException`** → On macOS this means `pbcopy`/`pbpaste` aren't accessible (very rare, usually a corrupted PATH). Reset shell PATH or specify full path in pyperclip config.

**Latency feels slow on M1** → Try `large-v3-turbo` (see [Change the ASR model](#change-the-asr-model)). 2x speedup, same quality.

---

## Test

```bash
pytest -v -m "not slow"   # unit tests only (no model load)
pytest -v -m slow         # includes ASR tests (loads model on first run)
```

11 fast tests + 2 slow ASR tests. All should pass.

---

## Status

- [x] Phase 1: MVP port from Windows version (not yet hardware-validated)
- [ ] Phase 2: VAD + regex postprocess + tray icon
- [ ] Phase 3: LLM postprocess + voice commands + app context
- [ ] Phase 4: `.app` bundle (py2app / Briefcase), config file, rotating logs

Design and roadmap in `../docs/superpowers/`.
