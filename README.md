# Miru Voice

[![CI](https://github.com/miru-repositories/miru-voice/actions/workflows/ci.yml/badge.svg)](https://github.com/miru-repositories/miru-voice/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

Local push-to-talk dictation app inspired by [Wispr Flow](https://wisprflow.ai/), running 100% on your machine — no cloud, no recurring cost, audio never leaves your device.

Hold a hotkey, speak, release. Text gets pasted into whatever app is focused.

---

## What you need (per OS)

### Windows

| What | Minimum | Why |
|---|---|---|
| OS | Windows 10 (1909+) / 11 | tested on Win 11 |
| GPU | NVIDIA, **≥8 GB VRAM** | runs Whisper-large-v3 in CUDA int8 |
| Driver | NVIDIA 525+ (CUDA 12.x) | required for ctranslate2 GPU |
| Python | 3.11+ | tested on 3.12 |
| Free disk | ~5 GB | venv + Whisper model |
| Mic | any working input | dictation input |
| Extra setup | copy cuBLAS DLLs into venv | one-line workaround, in [`windows/README.md`](windows/README.md) |

**No NVIDIA GPU?** Skip — CTranslate2 only supports CUDA on Windows. CPU is too slow on Windows hardware.

### macOS

| What | Minimum | Why |
|---|---|---|
| OS | macOS 12 Monterey | tested target macOS 14+ |
| Architecture | x86_64 (Intel) | works but slow — prefer Apple Silicon |
| | **arm64 (Apple Silicon M1+)** | runs Whisper-large-v3 in CPU int8 with usable latency |
| Python | 3.11+ | `brew install python@3.12` |
| Free disk | ~3 GB | venv + Whisper model |
| Mic | any working input | dictation input |
| Permissions | grant **Accessibility** to your Python binary | required for global hotkey + paste simulation |

ASR runs CPU-only on macOS (CTranslate2 has no Metal backend). On Apple Silicon CPU it's still fast enough; on Intel Macs you'll want to swap to a smaller Whisper model — see the platform README.

---

## Quick start

Pick your OS folder. Each is a self-contained Python project.

### Windows

```powershell
cd windows
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -e ".[dev]"
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install nvidia-cublas-cu12
# copy cuBLAS DLLs (one-time):
Copy-Item ".\.venv\Lib\site-packages\nvidia\cublas\bin\cublas64_12.dll", `
          ".\.venv\Lib\site-packages\nvidia\cublas\bin\cublasLt64_12.dll" `
          ".\.venv\Lib\site-packages\ctranslate2\"
python -m miru_voice.main
```

Then hold **Left Ctrl + Space**, speak, release.

### macOS

```bash
cd macos
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]"
# grant Accessibility permission to .venv/bin/python3.x — see macos/README.md
python -m miru_voice.main
```

Then hold **Right Option (⌥)**, speak, release.

---

## How to customize

Both versions expose the same knobs. Per-OS details are in [`windows/README.md`](windows/README.md#modify-it) and [`macos/README.md`](macos/README.md#modify-it). Quick reference:

| What | Where | How |
|---|---|---|
| Change hotkey | `src/miru_voice/main.py` | swap `keys=...` arg of `HotkeyListener` |
| Change Whisper model | `src/miru_voice/asr.py` | edit `model` default; supports large-v3, large-v3-turbo, medium, small, base |
| Force a language | `src/miru_voice/main.py` | pass `"es"` or `"en"` as 2nd arg of `self._asr.transcribe` |
| Force paste vs typing | `src/miru_voice/main.py` | `TextInjector(mode="paste" | "type" | "auto")` |
| Silence threshold | `src/miru_voice/main.py` | `if rms < 0.005:` — lower if your mic is quiet |
| Hotkey behavior | `src/miru_voice/main.py` | `mode="hold"` (default) or `mode="toggle"` |

---

## Repository layout

```
miru-voice/
├── windows/   →  Windows version (NVIDIA CUDA, faster-whisper GPU, pywin32 paste)
├── macos/     →  macOS version (Apple Silicon, faster-whisper CPU, pyperclip paste)
└── docs/      →  Design specs and implementation plans (shared)
```

The two versions are deliberately **not** a single codebase with platform detection — keeping them separate means each can adopt platform-native optimizations (CUDA vs MLX, Win32 SendInput vs Cmd+V, WASAPI vs CoreAudio) without `if sys.platform` ladders. They share design documents in `docs/`.

---

## Status

- **Windows** — Phase 1 MVP working end-to-end. Validated on RTX 3080 + Logitech C920.
- **macOS** — Phase 1 port written but **not yet validated on hardware**.

Phases 2-4 not yet started on either side:
- Phase 2 — silero-vad for automatic end-of-speech, regex filler removal, system tray icon with state
- Phase 3 — Phi-3-mini LLM grammar correction, voice commands (`"nueva línea"`, `"coma"`), per-app behavior rules
- Phase 4 — `.exe` / `.app` bundle, config file in `%APPDATA%` / `~/Library`, rotating logs

Full plan in [`docs/superpowers/plans/2026-05-11-dictado-local-app.md`](docs/superpowers/plans/2026-05-11-dictado-local-app.md) (kept under its original filename — historical record of when the project was called "dictado").

---

## Stack

| Layer | Library | Notes |
|---|---|---|
| Audio capture | `sounddevice` | WASAPI exclusive (Win) / CoreAudio (Mac) |
| ASR | `faster-whisper` (CTranslate2) | int8 on CUDA (Win) / int8 on CPU (Mac) |
| Hotkey | `pynput` | global listener, supports single keys + combos |
| Paste | `pywin32` + ctypes SendInput (Win); `pyperclip` + pynput Cmd+V (Mac) | |
| VAD (Phase 2) | `silero-vad` | runs on CPU, ~5 ms per chunk |
| LLM (Phase 3) | `llama-cpp-python` + Phi-3-mini Q4 | CUDA on Win, Metal on Mac |
| Tray (Phase 2) | `pystray` + Pillow | cross-platform |

See the platform READMEs for the full troubleshooting + tuning playbooks.

---

## Contributing

PRs welcome. See [`CONTRIBUTING.md`](CONTRIBUTING.md) for dev setup, commit conventions, and the PR process. Bug reports and feature requests use the templates under `.github/ISSUE_TEMPLATE/`. By participating you agree to the [Code of Conduct](CODE_OF_CONDUCT.md).

Security issues: see [`SECURITY.md`](SECURITY.md) — please use GitHub's private vulnerability reporting, not public issues.

## License

MIT — see [`LICENSE`](LICENSE). Copyright © 2026 Miru.
