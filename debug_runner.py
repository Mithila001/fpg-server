"""Simple script to invoke debug_fp_formatter for VS Code debugging.

This file is intended to be created temporarily and deleted later.  It
imports :func:`debug_fp_formatter` from the frontend formatter debug module
and runs it when executed as a script.  You can set breakpoints here or in
`app/algorithms/fp_formatter_for_frontend/debug.py` and launch the debugger
from this file.
"""


from app.services.algorithm_manager import DEV_RUN


def main() -> None:
    # call the helper; the return value isn't used, but you can inspect it in
    # the debugger.
    DEV_RUN()


if __name__ == "__main__":
    main()
