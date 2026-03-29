"""Debug entrypoint for usable-land shrink and boundary-rectangle plotting."""
from test.dev.plotter_land_boundary import run_plotter_land_boundary


def main() -> None:
    # call the helper; the return value isn't used, but you can inspect it in
    # the debugger.
    # DEV_RUN()
    run_plotter_land_boundary()


if __name__ == "__main__":
    main()
