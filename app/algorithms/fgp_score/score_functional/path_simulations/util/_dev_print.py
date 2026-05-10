from typing import Any


def dev_print(tag: str, data: Any):
    """
    Centralized logging utility for development.
    Toggling DISPLAY_LOGS to False will silence all dev_print calls.
    """
    DISPLAY_LOGS = True

    if DISPLAY_LOGS:
        print(f"[{tag}] {data}")
