from pathlib import Path


SELECTED_PATHS = (
    Path("app/pipeline/generation"),
    Path("app/algorithms/candidate_scoring"),
    Path("app/algorithms/candidate_search"),
    Path("app/algorithms/floor_plan_solver"),
    Path("app/algorithms/floor_plan_scoring"),
    Path("app/algorithms/floor_plan_openings"),
    Path("app/algorithms/floor_plan_post_processing"),
    Path("app/algorithms/floor_plan_preprocessing"),
)

FORBIDDEN_IMPORT_TEXT = (
    "Restructure_Data",
    "app.algorithms.fpg_",
    "app.algorithms.fgp_",
    "from app.algorithms.types import",
    "import app.algorithms.types.",
)


def test_new_generation_path_has_no_legacy_imports():
    violations = []
    for base in SELECTED_PATHS:
        for path in base.rglob("*.py"):
            source = path.read_text(encoding="utf-8")
            for forbidden in FORBIDDEN_IMPORT_TEXT:
                if forbidden in source:
                    violations.append(f"{path}: {forbidden}")

    assert violations == []
