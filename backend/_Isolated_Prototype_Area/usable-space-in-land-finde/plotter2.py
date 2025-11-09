import string
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import MultipleLocator 
from typing import Sequence, Tuple, Union

Coordinate = Tuple[Union[float, int], Union[float, int]]

def plot_polygons(coordinates_list: Sequence[Sequence[Coordinate]]):
    """
    Plots a list of polygons on a coordinate system with a fine-grained grid,
    integer axis labels, and highlighted x=0 and y=0 lines.
    
    The first three polygons are assigned fixed colors: Red, Blue, Green.
    Subsequent polygons use the default Matplotlib color cycle.
    """
    
    # 1. Setup Fixed and Default Colors
    # Fixed color list for the first 3 polygons
    FIXED_COLORS = ['tab:red', 'tab:green', 'tab:blue']
    
    # Get the default color cycle starting from the 4th color
    prop_cycle = plt.rcParams['axes.prop_cycle']
    default_colors = prop_cycle.by_key()['color']
    
    # Use the default colors from the 4th index onward for consistency
    # (Matplotlib's default cycle usually has 10 colors, ensuring variety)
    colors = FIXED_COLORS + default_colors
    
    # 2. Setup Figure
    fig, ax = plt.subplots(figsize=(8, 8))
    ax.set_title("Polygon Plotting: R,G,B")
    ax.set_xlabel("X Coordinate")
    ax.set_ylabel("Y Coordinate")
    
    # Configure Ticks and Grid (Major and minor ticks at every integer)
    ax.xaxis.set_major_locator(MultipleLocator(1.0))
    ax.yaxis.set_major_locator(MultipleLocator(1.0))
    ax.xaxis.set_minor_locator(MultipleLocator(1.0))
    ax.yaxis.set_minor_locator(MultipleLocator(1.0))
    
    # Grid Setup: Show grid lines barely visible
    ax.grid(which='major', visible=True, linestyle='-', alpha=0.4, color='gray', linewidth=0.5)
    
    # Highlight x=0 and y=0 lines (Increased linewidth for better highlight)
    ax.axhline(0, color='black', linewidth=0.5, linestyle='-', zorder=2, label='X=0 Axis')
    ax.axvline(0, color='black', linewidth=0.5, linestyle='-', zorder=2, label='Y=0 Axis')
    
    ax.set_aspect('equal', adjustable='box') 

    # 3. Plotting Logic
    all_x = []
    all_y = []

    for i, poly_coords in enumerate(coordinates_list):
        if not poly_coords:
            continue
            
        # Select color: uses FIXED_COLORS for i=0, 1, 2, then cycles through defaults
        color = colors[i % len(colors)]
        
        coords_array = np.array(poly_coords)
        x_coords = coords_array[:, 0]
        y_coords = coords_array[:, 1]
        
        # Draw polygon lines
        x_closed = np.append(x_coords, x_coords[0])
        y_closed = np.append(y_coords, y_coords[0])
        
        ax.plot(
            x_closed, 
            y_closed, 
            marker='', 
            linestyle='-', 
            color=color, 
            linewidth=2,
            label=f'Polygon {i+1} ({color.split(":")[-1].title() if i < 3 else "Default"})'
        )
        
        # Plot points and name them
        ax.scatter(
            x_coords, 
            y_coords, 
            color=color, 
            marker='o', # type: ignore 
            s=50, 
            zorder=5 
        )
        
        labels = string.ascii_uppercase
        polygon_number = i + 1
        
        for j, (x, y) in enumerate(poly_coords):
            point_label = f"P{i+1}-{j+1}"
            ax.annotate(
                point_label, 
                (x, y), 
                textcoords="offset points", 
                xytext=(5, 5), 
                ha='left', 
                color=color
            )

        # Iterate over the segments of the closed polygon
        # The loop runs from j=0 to N-1, where N is the number of vertices.
        # The last segment is from the last vertex (N-1) back to the first (0).
        for j in range(len(poly_coords)):
            # Get the current point (start of segment)
            (x1, y1) = poly_coords[j]
            
            # Get the next point (end of segment)
            # Use the modulo operator (%) to wrap around to the first point for the last segment
            (x2, y2) = poly_coords[(j + 1) % len(poly_coords)]
            
            # 1. Calculate the Midpoint (Center of the line segment)
            mid_x = (x1 + x2) / 2
            mid_y = (y1 + y2) / 2
            
            # 2. Determine the Label (A, B, C, ...)
            if j >= len(labels):
                segment_char = str(j + 1) # Fallback if more than 26 segments
            else:
                segment_char = labels[j]
            
            line_label = f"P{polygon_number}-{segment_char}"
            
            # 3. Annotate the Midpoint
            ax.annotate(
                line_label, 
                (mid_x, mid_y), 
                textcoords="offset points", 
                xytext=(0, 0), # Place label exactly at the midpoint
                ha='center', 
                va='center',
                color='black', # Use black for high visibility on the line
                bbox=dict(boxstyle="round,pad=0.3", fc="yellow", alpha=0.6, ec="none"), # Adds a background box
                fontsize=9
            )
            
        all_x.extend(x_coords)
        all_y.extend(y_coords)

    # 4. Adjust plot limits
    if all_x and all_y:
        x_min, x_max = np.min(all_x), np.max(all_x)
        y_min, y_max = np.min(all_y), np.max(all_y)
        
        padding = 1.5
        
        ax.set_xlim(np.floor(x_min) - padding, np.ceil(x_max) + padding)
        ax.set_ylim(np.floor(y_min) - padding, np.ceil(y_max) + padding)
        
    # Move the legend outside the plotting area
    ax.legend(
        loc='center left',      # Anchor point on the legend itself
        bbox_to_anchor=(1.05, 0.5), # (x, y) coordinates relative to the axes: 
                                    # 1.05 is just outside the right edge (1.0), 
                                    # 0.5 is the vertical center
        borderaxespad=0.          # No padding between the legend and the axes
    )
    plt.show()


# # --- Example Usage (Includes a 4th polygon to show the default color switch) ---
poly1 = [(1,1), (2,6), (6,6), (10,1)]         # Red
# poly2 = [(-10, 10), (-4, 10), (-4, 2), (-10, 2)] # Blue
# poly3 = [(6, -2), (10, -5), (8, -10), (4, -8), (5, -4)] # Green
# poly4 = [(-3, -3), (-1, -3), (-1, -1), (-3, -1)] # Will use the 4th default Matplotlib color (e.g., Purple)

polygons_to_plot = [poly1]

# plot_polygons(polygons_to_plot)