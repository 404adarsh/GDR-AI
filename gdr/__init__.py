"""GDR AI - Jarvis-style personal assistant for Linux, Windows, macOS, and Android."""

import os
import sys

# Ensure repository root is always present in sys.path even when run from subdirectories
_PKG_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_PKG_DIR)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

__version__ = "0.1.0"

