import matplotlib.pyplot as plt
import matplotlib.patches as patches
import os
import uuid

def plot_refine_floor_plan(stage1_rooms, stage2_rooms, stage3_rooms):
    """
    Plots three refinement stages side-by-side with Y=0 at the bottom.
    """
    output_dir = "/home/mithila/ssd_projects/fpg-server/test/outputs/refine"
    
    # Ensure directory exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    stages_data = [stage1_rooms, stage2_rooms, stage3_rooms]
    titles = ["Stage 1: Initial", "Stage 2: Refined", "Stage 3: Final"]
    
    fig, axes = plt.subplots(1, 3, figsize=(24, 10))
    
    # Floor plan color palette
    colors = {
        "bedroom": "#AEC6CF",
        "bathroom": "#CFCFCF",
        "kitchen": "#FFB347",
        "attachedBathroom": "#BDBDBD",
        "veranda": "#77DD77",
        "garage": "#838996",
        "diningRoom": "#FDFD96",
        "livingRoom": "#FFB7CE",
        "hallway": "#E6E6FA",
        "verandaOutdoorSpace": "#C1E1C1"
    }

    for i, rooms in enumerate(stages_data):
        ax = axes[i]
        for room in rooms:
            # Convert to float for safety
            x, y = float(room['x']), float(room['y'])
            w = float(room['x_end']) - x
            h = float(room['y_end']) - y
            
            # Create rectangle
            rect = patches.Rectangle(
                (x, y), w, h, 
                linewidth=2, 
                edgecolor='#333333', 
                facecolor=colors.get(room['type'], '#FFFFFF'), 
                alpha=0.8
            )
            ax.add_patch(rect)
            
            # Add label in the center
            label = room['name'].replace('_for_', '\n')
            ax.text(
                x + w/2, y + h/2, label, 
                ha='center', va='center', 
                fontsize=8, fontweight='bold', 
                color='black', wrap=True
            )

        ax.set_title(titles[i], fontsize=16, pad=20)
        
        # Axis setup
        ax.set_xlim(-5, 105)
        ax.set_ylim(-5, 135) # Y increases upwards; 0 is at the bottom
        ax.set_aspect('equal')
        
        # Removed ax.invert_yaxis() to keep Y=0 at the bottom
        
        ax.grid(True, linestyle=':', alpha=0.6)
        ax.set_xlabel('X')
        if i == 0:
            ax.set_ylabel('Y (Bottom-Up)')

    plt.tight_layout()
    
    # Save with unique name
    unique_id = uuid.uuid4().hex[:8]
    save_path = os.path.join(output_dir, f"refine_{unique_id}.png")
    
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close(fig)
    
    print(f"Refinement plot (standard orientation) saved to: {save_path}")
    return save_path