import matplotlib.pyplot as plt
import matplotlib.patches as patches
import os
from datetime import datetime

def show_plotter(rooms_list, solver, LAND_WIDTH, LAND_HEIGHT):
    """
    Display the floor plan in a matplotlib window using Room objects.
    """
    fig, ax = plt.subplots()
    ax.set_xlim(0, LAND_WIDTH)
    ax.set_ylim(0, LAND_HEIGHT)
    ax.set_aspect('equal')
    
    colors = ['#ff9999', '#66b3ff', '#99ff99', '#ffcc99', '#e377c2', '#bcbd22', '#17becf']
    
    for i, room in enumerate(rooms_list):
        # Extract numerical values directly from the room's attributes
        x_val = solver.Value(room.x)
        y_val = solver.Value(room.y)
        w_val = solver.Value(room.w)
        h_val = solver.Value(room.h)
        
        print(f"{room.name}: x={x_val}, y={y_val}, w={w_val}, h={h_val}")
        
        # Draw Rectangle
        rect = patches.Rectangle((x_val, y_val), w_val, h_val, 
                               linewidth=2, edgecolor='black', 
                               facecolor=colors[i % len(colors)])
        ax.add_patch(rect)
        
        # Add Label
        ax.text(x_val + w_val/2, y_val + h_val/2, room.name, 
               ha='center', va='center', fontsize=8, 
               color='black', weight='bold')

    plt.title("Generated Floor Plan (OOP Version)")
    plt.show()


def save_plotter(rooms_list, solver, LAND_WIDTH, LAND_HEIGHT, batchNo, plot_title, output_subfolder):
    """
    Save the floor plan to a specific subfolder using Room objects.
    """
    if not os.path.exists(output_subfolder):
        os.makedirs(output_subfolder)
    
    now = datetime.now()
    timestamp = now.strftime("%Y.%m.%d_%H.%M.%S") + f".{now.microsecond // 1000:03d}"
    
    filename = f"Batch_{batchNo:02d}_{timestamp}.png"
    filepath = os.path.join(output_subfolder, filename)
    
    fig, ax = plt.subplots()
    ax.set_xlim(0, LAND_WIDTH)
    ax.set_ylim(0, LAND_HEIGHT)
    ax.set_aspect('equal')
    
    colors = ['#ff9999', '#66b3ff', '#99ff99', '#ffcc99', '#e377c2', '#bcbd22', '#17becf']
    
    for i, room in enumerate(rooms_list):
        x_val = solver.Value(room.x)
        y_val = solver.Value(room.y)
        w_val = solver.Value(room.w)
        h_val = solver.Value(room.h)
        
        # Draw Rectangle
        rect = patches.Rectangle((x_val, y_val), w_val, h_val, 
                               linewidth=2, edgecolor='black', 
                               facecolor=colors[i % len(colors)])
        ax.add_patch(rect)
        
        # Add Label
        ax.text(x_val + w_val/2, y_val + h_val/2, room.name, 
                ha='center', va='center', fontsize=8, 
                color='black', weight='bold')

    plt.title(plot_title)
    plt.savefig(filepath, dpi=300, bbox_inches='tight')
    plt.close(fig)
    
    print(f"Floor plan saved to: {filepath}")