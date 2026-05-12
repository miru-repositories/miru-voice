# Contributing to Miru Voice

Thanks for considering a contribution. This repo has two independent implementations (Windows + macOS) that share design docs but no code. Contributions to either are welcome.

## Before you start

For non-trivial changes (new features, refactors), open an issue first to discuss the approach. For bug fixes, typo fixes, doc improvements, just send a PR.

## Dev setup

Pick the platform you're working on:

- **Windows**: see [`windows/README.md`](windows/README.md) for full setup including the cuBLAS DLL workaround
- **macOS**: see [`macos/README.md`](macos/README.md) for full setup including the Accessibility permission step

In both cases, after `pip install -e ".[dev]"`, you should be able to run:

```bash
pytest -m "not slow"
```

8 fast tests should pass. The 2 ASR tests under `-m slow` require GPU (Windows) or sufficient CPU (macOS) plus the downloaded Whisper model.

## Branch and commit conventions

- Branch off `main`, name branches `<type>/<short-description>` (e.g., `feat/vad-mid-press-flush`, `fix/wasapi-exclusive-fallback`).
- Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/): `<type>(<scope>): <subject>`.
  - Types we use: `feat`, `fix`, `refactor`, `docs`, `chore`, `test`, `build`.
  - Scope is optional but encouraged: `feat(hotkey): ...`, `fix(audio): ...`.
- Keep commits focused. If you find yourself writing "and also fix X" in the message, split it.

## Pull request process

1. Make sure tests pass locally: `pytest -m "not slow"`.
2. Make sure lint is clean: `ruff check src tests`.
3. Open the PR against `main`. Fill out the PR template.
4. CI will run on Windows + macOS runners (fast tests only — GPU/ASR tests are local-only).
5. A maintainer will review. Ask questions in the PR if anything is unclear.
6. After approval and green CI, the maintainer merges.

## Code style

- Python 3.11+ syntax. Type hints where they clarify (especially in public APIs).
- 100-char line limit (enforced by ruff).
- Prefer small, focused files. If a file grows past ~150 lines and does multiple things, propose a split.
- Don't add comments that restate the code. Comments should explain *why*, not *what*.
- No emoji in source files or commits (unless the task specifically calls for it).

## Tests

- Unit tests use mocks for OS-level APIs (`win32clipboard`, `pyperclip`, `sounddevice.InputStream`, etc.). Don't add tests that need real hardware unless marked `@pytest.mark.slow`.
- Async tests use `pytest-asyncio` with `asyncio_mode = "auto"` (already configured).
- TDD is the default: failing test first, then implementation. Look at the commit history for examples.

## Cross-platform considerations

If you're working on `windows/`, don't add Windows-specific dependencies to `macos/pyproject.toml` (or vice versa). The platforms are deliberately split to keep each `pyproject.toml` clean.

If your change is conceptual (e.g., a new VAD strategy), implement it in both `windows/` and `macos/` in the same PR. The two implementations share design but not code — keep them in step.

## Reporting bugs

Use the bug report issue template. Include:
- OS + version
- GPU (Windows) or chip (macOS)
- Python version (`python --version`)
- Exact command you ran
- Expected vs. actual behavior
- Logs from the console
- Output of `pip freeze` if you suspect a dependency issue

## Reporting security issues

See [`SECURITY.md`](SECURITY.md). **Do not file public issues for security vulnerabilities.**

## Questions

Open a [GitHub Discussion](https://github.com/miru-repositories/miru-voice/discussions) (if enabled) or a regular issue tagged `question`.
