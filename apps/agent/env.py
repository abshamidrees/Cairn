"""Load .env.local into the environment.

The scripts read secrets from `os.environ`, and the brief keeps them in
`.env.local`. Without this the two never meet, and the failure looks like a
missing key rather than a file nobody read.

Deliberately tiny and dependency-free. Values already set in the real
environment win, so an explicit export always beats the file.
"""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT = ROOT / ".env.local"


def load(path: Path | None = None) -> int:
    """Read KEY=value lines into os.environ. Returns how many were set."""
    source = path or DEFAULT
    if not source.exists():
        return 0

    loaded = 0
    for raw in source.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if not key or not value or key in os.environ:
            continue
        os.environ[key] = value
        loaded += 1
    return loaded
