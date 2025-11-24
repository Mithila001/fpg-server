from fpg import generate_floor_plan
from plotter import show_plotter, save_plotter




def main():
    result = generate_floor_plan()

    if result['success']:
        show_plotter(result['all_vars'], result['solver'], 
                     result['LAND_WIDTH'], result['LAND_HEIGHT'])


def batchRun():
    NUM_GENERATIONS = 10
    print(f"Starting batch generation of {NUM_GENERATIONS} floor plans...")
    print("-" * 60)
    
    successful_count = 0
    failed_count = 0

    for batch in range(NUM_GENERATIONS):
        print(f"\nGenerating floor plan {batch + 1}/{NUM_GENERATIONS} (Batch #{batch})...")
        result = generate_floor_plan()
        
        if result['success']:
            save_plotter(result['all_vars'], result['solver'], 
                        result['LAND_WIDTH'], result['LAND_HEIGHT'], 
                        batchNo=batch)
            successful_count += 1
            print(f"✓ Batch {batch} saved successfully!")
        else:
            failed_count += 1
            print(f" Batch {batch} failed to generate a valid solution.")
    
    print("\n" + "=" * 60)
    print(f"Generation Complete!")
    print(f"  Successful: {successful_count}/{NUM_GENERATIONS}")
    print(f"  Failed: {failed_count}/{NUM_GENERATIONS}")
    print("=" * 60)


if __name__ == "__main__":
    batchRun()