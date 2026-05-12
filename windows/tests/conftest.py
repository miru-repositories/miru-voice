"""pytest configuration.

If `dictado` is already importable (via `pip install -e .`) we do nothing.
Otherwise fall back to adding the in-tree `src/` to sys.path so tests run
without an editable install.
"""

import sys

try:
    import dictado  # noqa: F401  # editable install present
except ImportError:
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def pytest_sessionfinish(session, exitstatus):
    """Work around ctranslate2 CUDA teardown abort on Windows.

    On Windows, ctranslate2's CUDA context destructor calls abort() when tqdm
    daemon monitor threads are still alive during Python interpreter shutdown.
    Stopping those threads here and then calling os._exit() bypasses the normal
    shutdown sequence that triggers the crash, without affecting the reported
    exit code.  Only applied when GPU tests were actually collected.
    """
    import os
    import threading

    # Only apply the workaround if ctranslate2 was imported (GPU tests ran)
    if "ctranslate2" not in sys.modules:
        return

    # Stop any tqdm TMonitor threads (identified by the 'was_killed' Event)
    for t in threading.enumerate():
        if hasattr(t, "was_killed"):
            try:
                t.was_killed.set()
                t.join(timeout=1.0)
            except Exception:
                pass

    # Bypass Python's GC/atexit shutdown to avoid the ctranslate2 CUDA abort.
    os._exit(int(exitstatus))
