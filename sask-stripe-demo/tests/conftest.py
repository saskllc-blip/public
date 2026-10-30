"""Make the app folder importable when pytest runs from anywhere."""
from __future__ import annotations

import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]
for path in (APP_DIR, APP_DIR / "data"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
