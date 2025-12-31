import matplotlib.pyplot as plt
import matplotlib.patches as patches
import os
from datetime import datetime


def show_plotter(all_vars, solver, LAND_WIDTH, LAND_HEIGHT):
    """
    Display the floor plan in a matplotlib window.
    
    Parameters:
    - all_vars: Dictionary containing room variables
    - solver: The CP-SAT solver with solution
    - LAND_WIDTH: Width of the land
    - LAND_HEIGHT: Height of the land
    """
    fig, ax = plt.subplots()
    ax.set_xlim(0, LAND_WIDTH)
    ax.set_ylim(0, LAND_HEIGHT)
    ax.set_aspect('equal')
    
    colors = ['#ff9999', '#66b3ff', '#99ff99', '#ffcc99']
    
    for i, (name, v) in enumerate(all_vars.items()):
        # Extract numerical values from the solver
        x_val = solver.Value(v['x'])
        y_val = solver.Value(v['y'])
        w_val = solver.Value(v['w'])
        h_val = solver.Value(v['h'])
        
        print(f"{name}: x={x_val}, y={y_val}, w={w_val}, h={h_val}")
        
        # Draw Rectangle
        rect = patches.Rectangle((x_val, y_val), w_val, h_val, 
                               linewidth=2, edgecolor='black', 
                               facecolor=colors[i % len(colors)])
        ax.add_patch(rect)
        ax.text(x_val + w_val/2, y_val + h_val/2, name, 
               ha='center', va='center', fontsize=9, 
               color='black', weight='bold')


    plt.title("Generated Floor Plan (Geometric CSP)")
    plt.show()



def save_plotter(all_vars, solver, LAND_WIDTH, LAND_HEIGHT, batchNo, plot_title, output_subfolder):
    """
    Save the floor plan to a specific subfolder.
    """
    # Ensure the specific batch folder exists
    if not os.path.exists(output_subfolder):
        os.makedirs(output_subfolder)
    
    # Generate unique timestamp for the filename to avoid overwriting
    now = datetime.now()
    timestamp = f"{now.hour:02d}.{now.minute:02d}.{now.second:02d}.{now.microsecond // 1000:03d}"
    
    # Create filename
    filename = f"Batch_{batchNo:02d}_{timestamp}.png"
    filepath = os.path.join(output_subfolder, filename)
    
    # Create the plot
    fig, ax = plt.subplots()
    ax.set_xlim(0, LAND_WIDTH)
    ax.set_ylim(0, LAND_HEIGHT)
    ax.set_aspect('equal')
    
    colors = ['#ff9999', '#66b3ff', '#99ff99', '#ffcc99']
    
    for i, (name, v) in enumerate(all_vars.items()):
        x_val = solver.Value(v['x'])
        y_val = solver.Value(v['y'])
        w_val = solver.Value(v['w'])
        h_val = solver.Value(v['h'])
        
        rect = patches.Rectangle((x_val, y_val), w_val, h_val, 
                               linewidth=2, edgecolor='black', 
                               facecolor=colors[i % len(colors)])
        ax.add_patch(rect)
        ax.text(x_val + w_val/2, y_val + h_val/2, name, 
                ha='center', va='center', fontsize=9, 
                color='black', weight='bold')

    plt.title(plot_title)
    plt.savefig(filepath, dpi=300, bbox_inches='tight')
    plt.close(fig)
    
    print(f"Floor plan saved to: {filepath}")
