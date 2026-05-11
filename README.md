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
