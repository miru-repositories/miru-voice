# Dictado — macOS (Apple Silicon)

Local push-to-talk dictation app for macOS. Audio never leaves your Mac.

## Requirements

- macOS 13+ (Ventura or newer) on Apple Silicon (M1/M2/M3/M4)
- Python 3.11+
- ~3GB free disk for the Whisper model

Intel Macs work but are slow — see "Performance" section below.

## Install

```bash
cd macos
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Grant Accessibility permission

pynput requires Accessibility access to register global hotkeys and simulate keystrokes:

1. Open **System Settings → Privacy & Security → Accessibility**
2. Click the **+** button
3. Add the Python binary you'll run dictado with (e.g. `macos/.venv/bin/python3.11`) OR the Terminal app you launch from
4. Toggle it ON

Without this permission, hotkeys won't fire and paste will silently fail.

## Run

```bash
source .venv/bin/activate
python -m dictado.main
```

Hold **Right Option (⌥)**, speak, release. Text pastes into the focused app via Cmd+V.

First run downloads `Systran/faster-whisper-large-v3` (~800MB) — takes a couple minutes.

## Hotkey alternatives

Default is **Right Option** (single key, no system conflict). To change, edit `src/dictado/main.py`:

```python
# Single key options
listener = HotkeyListener(keys="caps_lock", mode="hold", on_event=self._on_hotkey)
listener = HotkeyListener(keys="f13", mode="hold", on_event=self._on_hotkey)

# Combos (PRESS fires when ALL keys held)
listener = HotkeyListener(keys=["ctrl_l", "space"], mode="hold", on_event=self._on_hotkey)
```

Avoid `["cmd_l", "space"]` — conflicts with Spotlight. Avoid `["ctrl_l", "space"]` if you have multiple input sources (conflicts with IME switcher).

## Performance

ASR runs on CPU (CTranslate2 has no Metal backend on macOS).

| Mac | Default model latency for 5s utterance |
|---|---|
| M3/M4 Max/Pro | ~400-600ms ✓ |
| M2/M3 base | ~600-900ms ✓ |
| M1 base | ~800-1200ms ✓ (usable) |
| Intel i7/i9 8-core | ~3-5s ⚠ swap to `medium` |
| Intel i5 | ~5-10s ✗ swap to `small` |

To swap the model edit `src/dictado/asr.py` — change the default `model` param.

For better Apple Silicon performance, consider replacing the faster-whisper backend with `mlx-whisper` or `whisper.cpp` Metal (not done here — Phase 2 work).

## Test

```bash
pytest -v -m "not slow"
```

The `slow` marker covers tests that load the ASR model. Run with `-m slow` to include them (downloads model on first run).

## Status

- [x] Phase 1: MVP — hotkey + ASR + paste (Mac port from Windows version)
- [ ] Phase 2: VAD + regex postprocess + tray
- [ ] Phase 3: LLM postprocess + voice commands + app context
- [ ] Phase 4: Packaging (.app via py2app or Briefcase)

See top-level `../docs/superpowers/specs/` for the design.
