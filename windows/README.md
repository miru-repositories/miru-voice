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
pip install torch --index-url https://download.pytorch.org/whl/cpu
# Phase 3 only:
# pip install --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu121/ llama-cpp-python
```

### CUDA runtime (faster-whisper)

If `faster-whisper` fails to load with `cublas64_12.dll not found`, install the cuBLAS runtime via pip and copy the DLLs into the `ctranslate2` package directory:

```powershell
pip install nvidia-cublas-cu12
$src = ".\.venv\Lib\site-packages\nvidia\cublas\bin"
$dst = ".\.venv\Lib\site-packages\ctranslate2"
Copy-Item "$src\cublas64_12.dll", "$src\cublasLt64_12.dll" $dst
```

This avoids requiring a full CUDA Toolkit install. `ctranslate2` registers its package dir with `os.add_dll_directory` so Windows finds the DLLs at runtime.

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

## Status

- [x] Phase 1: MVP — hotkey + ASR + paste
- [ ] Phase 2: VAD + regex postprocess + tray
- [ ] Phase 3: LLM postprocess + voice commands + app context
- [ ] Phase 4: Packaging
