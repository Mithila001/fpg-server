from __future__ import annotations

import ast
from pathlib import Path


ALGORITHMS_ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_ROOTS = {
    "app.core",
    "app.artifacts",
    "app.util",
    "app.pipeline",
    "app.services",
    "app.routes",
    "app.streaming",
    "app.visualization",
    "app.generation_metadata",
    "app.data",
    "fastapi",
    "pydantic",
}


def _production_modules() -> tuple[Path, ...]:
    return tuple(
        path
        for path in ALGORITHMS_ROOT.rglob("*.py")
        if "tests" not in path.parts
        and "__pycache__" not in path.parts
        and path.name != "debug.py"
    )


def test_algorithm_production_imports_are_relocatable() -> None:
    violations: list[str] = []
    for path in _production_modules():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            imported: tuple[str, ...] = ()
            if isinstance(node, ast.Import):
                imported = tuple(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                imported = (node.module,)
            for name in imported:
                if name == "app" or name.startswith("app."):
                    violations.append(f"{path.relative_to(ALGORITHMS_ROOT)}: {name}")
                elif any(
                    name == root or name.startswith(f"{root}.")
                    for root in FORBIDDEN_ROOTS
                ):
                    violations.append(f"{path.relative_to(ALGORITHMS_ROOT)}: {name}")
    assert not violations, "\n".join(violations)


def test_algorithm_observability_and_debug_packages_are_absent() -> None:
    assert not tuple(ALGORITHMS_ROOT.glob("*/logging/*.py"))
    assert not tuple(ALGORITHMS_ROOT.glob("*/tests/debug.py"))
