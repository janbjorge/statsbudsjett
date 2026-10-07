"""core/ is the pure domain: standard library and other core modules only (hexagonal layout, see AGENTS.md)."""

import ast
from pathlib import Path

CORE = Path(__file__).parent.parent / "core"
ALLOWED = {"core", "dataclasses", "enum", "typing", "collections", "functools", "itertools", "math"}


def test_core_imports_nothing_from_outside() -> None:
    bad = []
    for path in CORE.glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""] if isinstance(node, ast.ImportFrom) else []
            bad += [f"{path.name}: {n}" for n in names if n.split(".")[0] not in ALLOWED]
    assert not bad, bad
