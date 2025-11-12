import string
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import MultipleLocator 
from typing import Sequence, Tuple, Union
import os
from datetime import datetime

Coordinate = Tuple[Union[float, int], Union[float, int]]

def plot_polygon_images_save(coordinates_list: Sequence[Sequence[Coordinate]], plot_number: int):
    """
    Plots a list of polygons and saves the image to a file instead of displaying it.

    The file is saved in the './output_images' folder with the format: 
    plot_<number>__<millisecond>-<second>-<minutes>-<hours>-<day>-<month>-<year>.png

    Args:
        coordinates_list: A list of polygons, where each polygon is a sequence of (x, y) coordinates.
        plot_number: A number to include in the output filename (e.g., loop iteration count).
    """
    
    # --- File Path and Name Generation ---
    OUTPUT_FOLDER = './output_images'
    
    # Ensure the output directory exists
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)
        
    # Get current time for a unique, time-stamped filename
    now = datetime.now()
    
    # Format the time part: <millisecond>-<second>-<minutes>-<hours>-<day>-<month>-<year>
    time_str = now.strftime("%f-%S-%M-%H-%d-%m-%Y")
    
    # Create the full filename
    filename = f"plot_{plot_number}__{time_str}.png"
    filepath = os.path.join(OUTPUT_FOLDER, filename)
    
    # 1. Setup Fixed and Default Colors
    FIXED_COLORS = ['tab:red', 'tab:green', 'tab:blue']
    prop_cycle = plt.rcParams['axes.prop_cycle']
    default_colors = prop_cycle.by_key()['color']
    colors = FIXED_COLORS + default_colors
    
    # 2. Setup Figure
    # We explicitly create the figure and axes
    fig, ax = plt.subplots(figsize=(8, 8))
    ax.set_title(f"Polygon Plot: Plot {plot_number}")
    ax.set_xlabel("X Coordinate")
    ax.set_ylabel("Y Coordinate")
    
    # Configure Ticks and Grid
    ax.xaxis.set_major_locator(MultipleLocator(1.0))
    ax.yaxis.set_major_locator(MultipleLocator(1.0))
    ax.xaxis.set_minor_locator(MultipleLocator(1.0))
    ax.yaxis.set_minor_locator(MultipleLocator(1.0))
    ax.grid(which='major', visible=True, linestyle='-', alpha=0.4, color='gray', linewidth=0.5)
    
    # Highlight x=0 and y=0 lines
    ax.axhline(0, color='black', linewidth=0.5, linestyle='-', zorder=2)
    ax.axvline(0, color='black', linewidth=0.5, linestyle='-', zorder=2)
    ax.set_aspect('equal', adjustable='box') 

    # 3. Plotting Logic (Same as original)
    all_x = []
    all_y = []

    for i, poly_coords in enumerate(coordinates_list):
        if not poly_coords:
            continue
            
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
        
        # Plot points
        ax.scatter(
            x_coords, 
            y_coords, 
            color=color, 
            marker='o', 
            s=50, 
            zorder=5 
        )
        
        # Annotate Points (P1-1, P1-2, etc.)
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

        # Annotate Segments (P1-A, P1-B, etc.)
        labels = string.ascii_uppercase
        polygon_number = i + 1
        for j in range(len(poly_coords)):
            (x1, y1) = poly_coords[j]
            (x2, y2) = poly_coords[(j + 1) % len(poly_coords)]
            
            mid_x = (x1 + x2) / 2
            mid_y = (y1 + y2) / 2
            
            segment_char = labels[j] if j < len(labels) else str(j + 1)
            line_label = f"P{polygon_number}-{segment_char}"
            
            ax.annotate(
                line_label, 
                (mid_x, mid_y), 
                textcoords="offset points", 
                xytext=(0, 0), 
                ha='center', 
                va='center',
                color='black', 
                bbox=dict(boxstyle="round,pad=0.3", fc="yellow", alpha=0.6, ec="none"), 
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
        loc='center left',      
        bbox_to_anchor=(1.05, 0.5), 
        borderaxespad=0.          
    )
    
    # 5. Save the figure instead of showing it
    # Tight layout helps fit the legend within the saved image boundaries
    plt.tight_layout(rect=(0, 0, 0.9, 1)) 
    plt.savefig(filepath)
    plt.close(fig) # Important: Close the figure to free up memory when running in a loop

    print(f"Plot saved successfully as: {filepath}")