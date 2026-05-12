"""pytest configuration.

If `miru_voice` is already importable (via `pip install -e .`) we do nothing.
Otherwise fall back to adding the in-tree `src/` to sys.path so tests run
without an editable install.
"""

import sys

try:
    import miru_voice  # noqa: F401  # editable install present
except ImportError:
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
