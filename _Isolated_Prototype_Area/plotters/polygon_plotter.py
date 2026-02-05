"""
Unified Polygon Plotter Module
================================
A reusable, OOP-based polygon visualization tool with batch processing capabilities.

Features:
- Single and batch polygon plotting
- Automatic file organization with timestamped folders
- Configurable save/show modes
- Vertex and edge-midpoint annotations
- Equal-aspect coordinate grid with axis highlighting
"""

import string
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import MultipleLocator
from matplotlib.figure import Figure
from matplotlib.axes import Axes
from typing import Sequence, Tuple, Union, Optional, List
import os
from datetime import datetime


Coordinate = Tuple[Union[float, int], Union[float, int]]


class PolygonPlotter:
    """
    A plotter class for visualizing polygons with annotations.

    Supports both single-plot and batch-plot workflows with automatic
    file organization and timestamped output.
    """

    # Fixed colors for first 3 polygons (Red, Green, Blue)
    FIXED_COLORS = ["tab:red", "tab:green", "tab:blue"]

    def __init__(
        self,
        output_base_dir: str = "./plotters/output",
        single_output_dir_name: str = "single_saved_images",
    ):
        """
        Initialize the PolygonPlotter.

        Args:
            output_base_dir: Base directory for all output images.
            single_output_dir_name: Directory name (under `output_base_dir`) to use
                for single-file saves when `output_path` is not provided.
        """
        self.output_base_dir = output_base_dir
        self.single_output_dir_name = single_output_dir_name
        self.batch_folder = None  # Set during batch operations
        self.last_saved_file: Optional[str] = (
            None  # most-recent single-save path (if any)
        )

        # Get default matplotlib color cycle for polygons beyond the first 3
        prop_cycle = plt.rcParams["axes.prop_cycle"]
        default_colors = prop_cycle.by_key()["color"]
        self.colors = self.FIXED_COLORS + default_colors

    def polygon_line_plotter_single(
        self,
        coordinates_list: Sequence[Sequence[Coordinate]],
        output_path: Optional[str] = None,
        show: bool = False,
        title: str = "Polygon Visualization",
        figsize: Tuple[int, int] = (8, 8),
    ) -> Tuple[Figure, Axes]:
        """
        Plot a single set of polygons.

        Args:
            coordinates_list: List of polygons, each polygon is a list of (x, y) tuples.
            output_path: If provided, save the figure to this path.
            show: If True, display the plot interactively.
            title: Title for the plot.
            figsize: Figure size in inches.

        Returns:
            Tuple of (figure, axes) objects for further customization.
        """
        # Create figure and axes
        fig, ax = plt.subplots(figsize=figsize)

        # Configure the plot appearance
        self._setup_axes(ax, title)

        # Plot the polygons
        all_x, all_y = self._plot_polygons_core(ax, coordinates_list)

        # Adjust plot limits based on data
        self._adjust_limits(ax, all_x, all_y)

        # Add legend inside the plot area
        ax.legend(
            loc="upper right",
            fontsize=8,
            frameon=True,
            fancybox=True,
            shadow=True,
            edgecolor="black",
            borderpad=0.5,
            labelspacing=0.5,
        )

        # Handle output
        # If caller supplied an explicit path, use it. Otherwise save into a
        # per-plotter default folder (`output_base_dir/<single_output_dir_name>/`).
        if output_path is None:
            # create default single-file directory and a timestamped filename
            single_dir = os.path.join(self.output_base_dir, self.single_output_dir_name)
            os.makedirs(single_dir, exist_ok=True)
            filename = self.file_name_generator(0, 1)
            output_path = os.path.join(single_dir, filename)

        if output_path:
            plt.tight_layout()
            # Make images readable in thumbnails/viewers and avoid over-cropping.
            # Use a moderate DPI and a small pad so thin lines/annotations remain visible.
            fc = fig.get_facecolor() if hasattr(fig, "get_facecolor") else None
            plt.savefig(
                output_path,
                dpi=150,
                bbox_inches="tight",
                pad_inches=0.08,
                facecolor=fc,
            )
            # record path for callers/tests
            try:
                self.last_saved_file = os.path.abspath(output_path)
            except Exception:
                self.last_saved_file = output_path
            print(f"Plot saved: {output_path}")

        if show:
            plt.show()
        else:
            plt.close(fig)

        return fig, ax

    def polygon_line_plotter_batch(
        self,
        polygons_batch: Sequence[Sequence[Sequence[Coordinate]]],
        batch_no: int,
        show: bool = False,
        titles: Optional[List[str]] = None,
    ) -> List[str]:
        """
        Process and save multiple polygon sets in a batch operation.

        Creates a timestamped folder and saves each polygon set with
        sequential numbering.

        Args:
            polygons_batch: List of polygon sets to plot.
            batch_no: Batch identifier number.
            show: If True, display each plot (not recommended for large batches).
            titles: Optional list of titles for each plot.

        Returns:
            List of file paths where images were saved.
        """
        # Create batch folder
        batch_folder = self._create_batch_folder()

        saved_files = []

        for image_no, coordinates_list in enumerate(polygons_batch, start=1):
            # Generate filename
            filename = self.file_name_generator(batch_no, image_no)
            output_path = os.path.join(batch_folder, filename)

            # Generate title
            if titles and image_no - 1 < len(titles):
                title = titles[image_no - 1]
            else:
                title = f"Batch {batch_no} - Image {image_no}"

            # Use single plotter to generate the image
            self.polygon_line_plotter_single(
                coordinates_list=coordinates_list,
                output_path=output_path,
                show=show,
                title=title,
            )

            saved_files.append(output_path)

        print(f"Batch complete: {len(saved_files)} images saved to {batch_folder}")
        return saved_files

    def file_name_generator(self, batch_no: int, image_no: int) -> str:
        """
        Generate a standardized filename for batch operations.

        Format: YYYYMMDD-HHMMSSmm_<batchNo>_<imageNo>.png
        Where mm is milliseconds (3 digits).

        Args:
            batch_no: Batch identifier number.
            image_no: Image sequence number within the batch.

        Returns:
            Formatted filename string.
        """
        now = datetime.now()

        # Format: YYYYMMDD-HHMMSSmm
        date_part = now.strftime("%Y%m%d-%H%M%S")
        milliseconds = f"{now.microsecond // 1000:03d}"
        timestamp = f"{date_part}{milliseconds}"

        # Combine with batch and image numbers
        filename = f"{timestamp}_{batch_no:02d}_{image_no:03d}.png"

        return filename

    def _create_batch_folder(self) -> str:
        """
        Create a timestamped folder for batch output.

        Folder format: YYYYMMDD-HH-MM-SS

        Returns:
            Absolute path to the created folder.
        """
        now = datetime.now()
        folder_name = now.strftime("%Y%m%d-%H-%M-%S")
        folder_path = os.path.join(self.output_base_dir, folder_name)

        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            print(f"Created batch folder: {folder_path}")

        self.batch_folder = folder_path
        return folder_path

    def _setup_axes(self, ax: Axes, title: str):
        """
        Configure axes appearance with grid, ticks, and labels.

        Args:
            ax: Matplotlib axes object to configure.
            title: Plot title.
        """
        ax.set_title(title)
        ax.set_xlabel("X Coordinate")
        ax.set_ylabel("Y Coordinate")

        # Configure ticks at every integer
        ax.xaxis.set_major_locator(MultipleLocator(1.0))
        ax.yaxis.set_major_locator(MultipleLocator(1.0))
        ax.xaxis.set_minor_locator(MultipleLocator(1.0))
        ax.yaxis.set_minor_locator(MultipleLocator(1.0))

        # Grid styling
        ax.grid(
            which="major",
            visible=True,
            linestyle="-",
            alpha=0.4,
            color="gray",
            linewidth=0.5,
        )

        # Highlight x=0 and y=0 axes
        ax.axhline(0, color="black", linewidth=0.8, linestyle="-", zorder=2)
        ax.axvline(0, color="black", linewidth=0.8, linestyle="-", zorder=2)

        # Equal aspect ratio
        ax.set_aspect("equal", adjustable="box")

        # Make sure spines are visible (helps viewers show a frame for small/tightly-cropped plots)
        # Some test stubs / minimal axes implementations may not provide `spines`;
        # guard against that to keep the code robust in both real and mocked envs.
        if hasattr(ax, "spines") and getattr(ax, "spines") is not None:
            for spine in ax.spines.values():
                spine.set_visible(True)
                spine.set_linewidth(0.8)
                spine.set_color("black")

    def _plot_polygons_core(
        self, ax: Axes, coordinates_list: Sequence[Sequence[Coordinate]]
    ) -> Tuple[List[float], List[float]]:
        """
        Core polygon plotting logic with annotations.

        Args:
            ax: Matplotlib axes to draw on.
            coordinates_list: List of polygons to plot.

        Returns:
            Tuple of (all_x_coords, all_y_coords) for limit calculation.
        """
        all_x = []
        all_y = []
        labels = string.ascii_uppercase

        for i, poly_coords in enumerate(coordinates_list):
            if not poly_coords:
                continue

            # Select color
            color = self.colors[i % len(self.colors)]

            # Convert to numpy array
            coords_array = np.array(poly_coords)
            x_coords = coords_array[:, 0]
            y_coords = coords_array[:, 1]

            # Draw polygon edges (closed loop)
            x_closed = np.append(x_coords, x_coords[0])
            y_closed = np.append(y_coords, y_coords[0])

            ax.plot(
                x_closed,
                y_closed,
                marker=None,
                linestyle="-",
                color=color,
                linewidth=2.5,
                zorder=4,
                solid_capstyle="round",
                label=f"Polygon {i + 1}",
            )

            # Draw vertices (larger + edged so they remain visible on white backgrounds)
            ax.scatter(
                x_coords,
                y_coords,
                facecolor=color,
                edgecolors="black",
                marker="o",
                s=80,
                linewidths=0.6,
                zorder=6,
            )

            # Annotate vertices (P1-1, P1-2, ...)
            for j, (x, y) in enumerate(poly_coords):
                point_label = f"P{i + 1}-{j + 1}"
                ax.annotate(
                    point_label,
                    (x, y),
                    textcoords="offset points",
                    xytext=(5, 5),
                    ha="left",
                    color=color,
                    fontsize=8,
                )

            # Annotate edge midpoints (P1-A, P1-B, ...)
            polygon_number = i + 1
            for j in range(len(poly_coords)):
                (x1, y1) = poly_coords[j]
                (x2, y2) = poly_coords[(j + 1) % len(poly_coords)]

                # Calculate midpoint
                mid_x = (x1 + x2) / 2
                mid_y = (y1 + y2) / 2

                # Generate label
                segment_char = labels[j] if j < len(labels) else str(j + 1)
                line_label = f"P{polygon_number}-{segment_char}"

                # Annotate with background box
                ax.annotate(
                    line_label,
                    (mid_x, mid_y),
                    textcoords="offset points",
                    xytext=(0, 0),
                    ha="center",
                    va="center",
                    color="black",
                    bbox=dict(
                        boxstyle="round,pad=0.3", fc="yellow", alpha=0.6, ec="none"
                    ),
                    fontsize=9,
                )

            # Collect coordinates for limit calculation
            all_x.extend(x_coords)
            all_y.extend(y_coords)

        return all_x, all_y

    def _adjust_limits(self, ax: Axes, all_x: List[float], all_y: List[float]):
        """
        Adjust plot limits with padding based on data bounds.

        Args:
            ax: Matplotlib axes to adjust.
            all_x: All x-coordinates from plotted data.
            all_y: All y-coordinates from plotted data.
        """
        if all_x and all_y:
            x_min, x_max = np.min(all_x), np.max(all_x)
            y_min, y_max = np.min(all_y), np.max(all_y)

            padding = 1.5

            ax.set_xlim(np.floor(x_min) - padding, np.ceil(x_max) + padding)
            ax.set_ylim(np.floor(y_min) - padding, np.ceil(y_max) + padding)


# Convenience functions for backward compatibility
def plot_polygons(coordinates_list: Sequence[Sequence[Coordinate]], show: bool = True):
    """
    Quick plot function for interactive use (backward compatible).

    Args:
        coordinates_list: List of polygons to plot.
        show: If True, display the plot.
    """
    plotter = PolygonPlotter()
    plotter.polygon_line_plotter_single(
        coordinates_list=coordinates_list, show=show, title="Polygon Plotting: R,G,B"
    )


# Example usage and testing
if __name__ == "__main__":
    # Sample polygon data
    poly1 = [(1, 1), (2, 6), (6, 6), (10, 1)]
    poly2 = [(-10, 10), (-4, 10), (-4, 2), (-10, 2)]
    poly3 = [(6, -2), (10, -5), (8, -10), (4, -8), (5, -4)]

    # Example 1: Single plot (display only)
    print("Example 1: Single plot display")
    plotter = PolygonPlotter()
    plotter.polygon_line_plotter_single(
        coordinates_list=[poly1, poly2, poly3],
        show=True,
        title="Example: Three Polygons",
    )

    # Example 2: Batch processing
    print("\nExample 2: Batch processing")
    batch_data = [[poly1], [poly1, poly2], [poly1, poly2, poly3]]

    plotter.polygon_line_plotter_batch(
        polygons_batch=batch_data, batch_no=1, show=False
    )
