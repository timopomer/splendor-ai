"""Lint: forbid imports inside any __init__.py.

Rationale: avoid re-export patterns; force direct imports from concrete modules.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path


def file_has_imports(path: Path) -> bool:
    try:
        src = path.read_text(encoding="utf-8")
    except Exception:
        return False

    try:
        tree = ast.parse(src, filename=str(path))
    except SyntaxError:
        # Let ruff/pytest handle syntax; don't mask it here.
        return False

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            return True
        if isinstance(node, ast.ImportFrom):
            # Allow `from __future__ import annotations` only.
            if node.module == "__future__":
                continue
            return True
    return False


def main(argv: list[str]) -> int:
    root = Path(argv[1]).resolve() if len(argv) > 1 else Path.cwd().resolve()
    offenders: list[Path] = []
    for p in root.rglob("__init__.py"):
        # Skip virtualenvs / common build dirs just in case.
        if any(part in {".venv", "venv", "build", "dist", ".ruff_cache"} for part in p.parts):
            continue
        if file_has_imports(p):
            offenders.append(p)

    if offenders:
        print("Imports are forbidden in __init__.py files. Offenders:")
        for p in offenders:
            print(f"- {p}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))


