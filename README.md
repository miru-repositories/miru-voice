# Dictado

Local push-to-talk dictation app inspired by [Wispr Flow](https://wisprflow.ai/), but runs 100% on your machine — no cloud, no recurring cost, audio never leaves your device.

Hold a hotkey, speak, release. Text pastes into whatever app is focused.

## Repository layout

This repo contains two separate implementations — one per platform — because the audio capture, text injection, and ASR backends differ enough that a single codebase would be more friction than benefit.

```
dictado/
├── windows/   →  Windows version (NVIDIA CUDA, faster-whisper GPU)
├── macos/     →  macOS version (Apple Silicon, faster-whisper CPU)
└── docs/      →  Design specs and implementation plans (shared)
```

Each subfolder is a self-contained Python project with its own `pyproject.toml`, `src/`, `tests/`, and `README.md`. Pick the one for your OS.

## Quick start

**Windows (NVIDIA GPU required):**
```powershell
cd windows
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
python -m dictado.main
```

**macOS (Apple Silicon recommended):**
```bash
cd macos
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m dictado.main
```

See [`windows/README.md`](windows/README.md) or [`macos/README.md`](macos/README.md) for the full setup including CUDA workaround (Windows) and Accessibility permission (macOS).

## Status

- **Windows**: Phase 1 MVP working end-to-end (hotkey + ASR + paste). Validated on RTX 3080.
- **macOS**: Phase 1 port done, not yet validated on hardware. Targets Apple Silicon.

Phases 2-4 (VAD, LLM postprocess, packaging) not yet implemented on either side. See `docs/superpowers/plans/` for the full roadmap.

## Design

The full architectural design and decision log lives in `docs/superpowers/specs/2026-05-11-dictado-local-design.md`. The implementation plan with task-by-task breakdown is in `docs/superpowers/plans/2026-05-11-dictado-local-app.md`.

Core stack on both platforms:
- `sounddevice` for audio capture
- `faster-whisper` (CTranslate2 backend) for ASR
- `pynput` for global hotkey + (on macOS) keystroke simulation
- `silero-vad` (Phase 2) for end-of-speech detection
- `llama-cpp-python` + Phi-3-mini Q4 (Phase 3) for grammar/filler correction

Platform-specific:
- **Windows**: pywin32 + ctypes SendInput for clipboard + Ctrl+V; CUDA for ASR
- **macOS**: pyperclip + pynput Cmd+V; CPU for ASR (Metal not supported by CTranslate2 — swap to whisper.cpp or mlx-whisper for GPU)
