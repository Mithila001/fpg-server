from __future__ import annotations

import ast
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[2]
def _imports(path: Path) -> tuple[str, ...]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return tuple(names)


def test_algorithm_features_use_their_logging_package() -> None:
    violations: list[str] = []
    for path in (APP_ROOT / "algorithms").rglob("*.py"):
        if "logging" in path.parts or "tests" in path.parts:
            continue
        for imported in _imports(path):
            if imported.startswith("app.util.logger"):
                violations.append(
                    f"{path.relative_to(APP_ROOT)} imports {imported}; "
                    "use the feature logging package"
                )
    assert not violations, "\n".join(violations)


def test_algorithm_implementations_do_not_import_artifact_storage() -> None:
    violations: list[str] = []
    for path in (APP_ROOT / "algorithms").rglob("*.py"):
        if "logging" in path.parts or "tests" in path.parts:
            continue
        for imported in _imports(path):
            if imported.startswith("app.artifacts"):
                violations.append(
                    f"{path.relative_to(APP_ROOT)} imports {imported}; "
                    "use the feature logging package"
                )
    assert not violations, "\n".join(violations)


def test_shared_infrastructure_has_no_feature_dependencies() -> None:
    forbidden = {
        "logger": ("app.algorithms", "app.pipeline", "app.visualization"),
        "artifacts": (
            "app.algorithms",
            "app.pipeline",
            "app.visualization",
            "app.util.logger",
        ),
    }
    violations: list[str] = []
    for package, prefixes in forbidden.items():
        package_root = APP_ROOT / ("util/logger" if package == "logger" else package)
        for path in package_root.rglob("*.py"):
            for imported in _imports(path):
                if imported.startswith(prefixes):
                    violations.append(
                        f"{path.relative_to(APP_ROOT)} imports forbidden {imported}"
                    )
    assert not violations, "\n".join(violations)


def test_features_do_not_import_other_feature_loggers() -> None:
    violations: list[str] = []
    for path in (APP_ROOT / "algorithms").rglob("*.py"):
        relative = path.relative_to(APP_ROOT / "algorithms")
        owner = relative.parts[0]
        for imported in _imports(path):
            marker = ".logging"
            if imported.startswith("app.algorithms.") and marker in imported:
                imported_owner = imported.split(".")[2]
                if imported_owner != owner:
                    violations.append(
                        f"{path.relative_to(APP_ROOT)} imports {imported}"
                    )
    assert not violations, "\n".join(violations)


def test_pipeline_persistence_is_owned_by_pipeline_logging_package() -> None:
    violations: list[str] = []
    root = APP_ROOT / "pipeline" / "generation"
    for path in root.rglob("*.py"):
        if "logging" in path.parts or "tests" in path.parts:
            continue
        for imported in _imports(path):
            if imported.startswith(("app.artifacts", "app.util.logger")):
                violations.append(
                    f"{path.relative_to(APP_ROOT)} imports infrastructure {imported}"
                )
    assert not violations, "\n".join(violations)


def test_visualization_has_one_filesystem_export_boundary() -> None:
    violations: list[str] = []
    root = APP_ROOT / "visualization"
    for path in root.rglob("*.py"):
        if "tests" in path.parts or "playground" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "savefig"
                and path.name != "output_manager.py"
            ):
                violations.append(
                    f"{path.relative_to(APP_ROOT)} calls savefig outside output manager"
                )
    assert not violations, "\n".join(violations)


def test_jsonl_is_not_supported_anywhere_in_application_code() -> None:
    violations: list[str] = []
    for path in APP_ROOT.rglob("*.py"):
        if path == Path(__file__):
            continue
        if "jsonl" in path.read_text(encoding="utf-8").lower():
            violations.append(str(path.relative_to(APP_ROOT)))
    assert not violations, "JSONL references remain:\n" + "\n".join(violations)


def test_flow_identity_does_not_use_uuid_or_job_id_for_naming() -> None:
    execution_root = APP_ROOT / "core" / "execution"
    naming_sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in execution_root.glob("*.py")
    ).lower()
    assert "uuid" not in naming_sources
    assert "flow_job" not in naming_sources
