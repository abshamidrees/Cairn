"""The adapter boundary, enforced rather than asserted.

Only `apps/agent/memory/store.py` may import `sibyl_memory_client`. That rule is
what makes the deletion test a swap at one call site instead of a branch inside
the verdict engine, so it is worth a test that fails the day someone reaches
around it.
"""

from __future__ import annotations

import ast
from pathlib import Path

SDK = "sibyl_memory_client"

ROOT = Path(__file__).resolve().parent.parent
SEARCHED = ("apps", "packages", "scripts", "tests")

# The adapter itself, and the phase 0 gate whose whole purpose is to prove the
# SDK behaves offline with no credentials. The gate cannot go through the
# adapter without testing the adapter instead of the thing it wraps.
ALLOWED = {
    Path("apps/agent/memory/store.py"),
    Path("scripts/verify_memory.py"),
}


def _python_files() -> list[Path]:
    found: list[Path] = []
    for directory in SEARCHED:
        found.extend(p for p in (ROOT / directory).rglob("*.py") if "__pycache__" not in p.parts)
    return found


def _imports_sdk(path: Path) -> bool:
    """True only for a real import, so a mention in prose does not count."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(alias.name.split(".")[0] == SDK for alias in node.names):
                return True
        elif (
            isinstance(node, ast.ImportFrom)
            and node.module is not None
            and node.module.split(".")[0] == SDK
        ):
            return True
    return False


def test_only_the_adapter_imports_the_sdk() -> None:
    offenders = {path.relative_to(ROOT) for path in _python_files() if _imports_sdk(path)}
    assert offenders == ALLOWED, (
        "sibyl_memory_client must only be reached through apps/agent/memory/store.py"
    )


def test_the_adapter_is_where_the_allowlist_says_it_is() -> None:
    """Guards against the allowlist silently passing because a file was moved."""
    for allowed in ALLOWED:
        assert (ROOT / allowed).exists(), f"{allowed} is on the allowlist but does not exist"
