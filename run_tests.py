import subprocess
import sys
import time
import os


# python run_tests.py
def print_header(title):
    print("\n" + "=" * 60)
    print(f" {title.upper()} ".center(60, "="))
    print("=" * 60 + "\n")


def run_test_section(name, command):
    print(f"[*] Running: {name}...")
    start_time = time.time()

    # Set PYTHONPATH to current directory
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()

    result = subprocess.run(command, capture_output=True, text=True, env=env)
    duration = time.time() - start_time

    if result.returncode == 0:
        print(f"[\033[92mPASS\033[0m] {name} completed in {duration:.2f}s")
        return True, result.stdout
    else:
        print(f"[\033[91mFAIL\033[0m] {name} failed in {duration:.2f}s")
        return False, result.stdout + "\n" + result.stderr


def main():
    print_header("House Plan Generator - Thesis Test Suite")
    print(f"Execution started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Environment: Python {sys.version.split()[0]}\n")

    test_file = "test/unit/test_thesis_core.py"

    # Try to find pytest in .venv
    venv_pytest = os.path.join(".venv", "Scripts", "pytest.exe")
    if not os.path.exists(venv_pytest):
        venv_pytest = "pytest"  # Fallback to global

    phases = [
        (
            "Phase 1: DB Constraint Integrity",
            [venv_pytest, f"{test_file}::test_phase_1_db_constraint_integrity", "-v"],
        ),
        (
            "Phase 2: Requirement Normalization",
            [venv_pytest, f"{test_file}::test_phase_2_requirement_normalization", "-v"],
        ),
        (
            "Phase 3: Land Geometry Processing",
            [venv_pytest, f"{test_file}::test_phase_3_land_geometry_processing", "-v"],
        ),
        (
            "Phase 4: Full Pipeline Smoke Test",
            [
                venv_pytest,
                f"{test_file}::test_phase_4_generation_pipeline_smoke_test",
                "-v",
            ],
        ),
    ]

    results = []
    for name, cmd in phases:
        success, output = run_test_section(name, cmd)
        results.append((name, success))
        if not success:
            print("\nError Details:")
            print("-" * 20)
            print(output)
            print("-" * 20)

    print_header("Final Summary")
    all_passed = True
    for name, success in results:
        status = "\033[92mPASSED\033[0m" if success else "\033[91mFAILED\033[0m"
        print(f"{name:<40} : {status}")
        if not success:
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print(" SUCCESS: All core system aspects are functional. ".center(60, " "))
    else:
        print(" WARNING: Some tests failed. Check logs for details. ".center(60, " "))
    print("=" * 60 + "\n")


if __name__ == "__main__":
    try:
        # Check if colorama is available for Windows color support
        import colorama

        colorama.init()
    except ImportError:
        pass

    main()
