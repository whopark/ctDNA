#!/usr/bin/env python3
"""
Frozen-path helper for PyInstaller bundled exe.

When running as a frozen exe, bundled data files live under sys._MEIPASS.
When running as normal Python, files are relative to the repo root.
"""

import sys
import os

def is_frozen() -> bool:
    """Return True if running inside a PyInstaller bundle."""
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


def bundle_dir() -> str:
    """Return the directory where bundled data files live."""
    if is_frozen():
        return sys._MEIPASS  # type: ignore[attr-defined]
    return os.path.dirname(os.path.abspath(__file__))


def data_path(filename: str) -> str:
    """Resolve a bundled data file path (e.g. 'template.docx', 'kb.json')."""
    return os.path.join(bundle_dir(), filename)


def writable_kb_path() -> str:
    """Return a writable path for kb.json.

    In frozen mode, the bundle dir is read-only, so kb.json is copied to
    the exe's directory on first run.  In normal mode, use the repo root.
    """
    if is_frozen():
        exe_dir = os.path.dirname(sys.executable)
        return os.path.join(exe_dir, "kb.json")
    return data_path("kb.json")
