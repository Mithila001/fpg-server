import matplotlib.pyplot as plt
import os
import datetime
from app.algorithms.fgp_score.score_functional.path_simulations.dev.engine import PathSimulationEngine

def run_path_simulation_dev(rooms, walls, floor_poly, output_dir="test/outputs/path_score"):
    os.makedirs(output_dir, exist_ok=True)
    engine = PathSimulationEngine(resolution=0.15)
    
    door_polys = [r.door_poly for r in rooms if hasattr(r, 'door_poly')]
    nav_mesh = engine.create_nav_mesh(floor_poly, walls, door_polys)
    engine.rasterize(nav_mesh)
    
    # Check initialization to satisfy Pylance
    if engine.grid is None or engine.traffic_map is None:
        return ""

    simulated_paths = []
    # (Assuming rooms have .type and .door_pos attributes)
    entry = next((r for r in rooms if r.type == "entry"), rooms[0])
    
    # Example Path: Entry to first available room
    for target in rooms[1:]:
        raw = engine.astar(entry.door_pos, target.door_pos)
        if raw:
            simulated_paths.append((f"To {target.type}", engine.smooth_path(raw), 'orange'))

    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(20, 7), facecolor='#121212')
    
    # Common extent for imshow
    res = engine.meta['res']
    h, w = engine.grid.shape
    extent = [
        engine.meta['min_x'], engine.meta['min_x'] + w * res,
        engine.meta['min_y'], engine.meta['min_y'] + h * res
    ]

    # Plot 1: Paths
    ax1.set_title("Paths", color='white')
    for _, path, clr in simulated_paths:
        px, py = zip(*path)
        ax1.plot(px, py, color=clr, linewidth=2)
    
    # Plot 2: Unused Space
    ax2.set_title("Dead Space", color='white')
    dead_space = (engine.traffic_map == 0) & (engine.grid == 0)
    ax2.imshow(dead_space, origin='lower', cmap='Blues', extent=extent)

    # Plot 3: Traffic Heatmap
    ax3.set_title("Traffic Intensity", color='white')
    ax3.imshow(engine.traffic_map, origin='lower', cmap='hot', extent=extent)
    
    for ax in [ax1, ax2, ax3]:
        ax.axis('off')
        ax.set_aspect('equal')

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    file_path = os.path.join(output_dir, f"{timestamp}.png")
    plt.savefig(file_path, facecolor='#121212')
    plt.close()
    return os.path.abspath(file_path)