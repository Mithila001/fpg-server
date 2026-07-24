## Goal: Vitalising all scoring feature appropriately
I want to visualize all the Scoring Feature under candidate Search and Floor Plan Solver Scoring.

Here these are the important things to consider.
- For the visualization, we need additional data compare to existing data like `floor plan` data. from each of these evaluations. We might have to call these visualization function directly from each evolution. OR, We can standardize the each scoring (both in Candidate Search and Floor Plan Scoring) to return a another parameter called visualization_data (or better name) with each evaluation having its own contract/type  

Example:
```
// an evaluation file
class <visualization data contract name >:
    <name>: <type>
    <name>: <type>
    <name>: <type>

<The evaluation code>

<return the data WITH visualization helpful data>


// in the evaluation manager file
import the <visualization data contract name >
import the visualization function for specific visualization
call it with visualization data + typical already have floor plan data if wanted.
done.
```

All these scoring related files can be place to `app/visualization/features/score/candidate_search_score`, `app/visualization/features/score/floor_plan_score` 
With each evaluation code in per each file.

## Visualization Info for each section
### Candidate Search
#### exterior_clearance
Show the each selected point area of the clearance space

#### relationship_quality
In a single evaluation run, there will be few images. 
1. First image show plots of the Relation weights.
2. Second image show relationship evaluation score where lower score red and good score green

#### spatial_distribution
In a Single image, Do a Heat map/infrared heat map kind of visuals where too much distance and appropriate distance are shown based on hint points.

#### zone_suitability
A single image that mark red or green of each point (with label) showing if the point withing the zone or not.

### Floor Plan Scoring
#### bedroom_quality
No need visualization
#### enclosed_voids
Red mark voids if exist
#### inward_recess
Mark Inward Pockets
#### geometry_integrity
No need visualization
#### kitchen_dining
No need visualization
#### living_room_balance
No need visualization
#### required_adjacency
No need visualization


Overall Goal is to Visualize and evaluate from my eyes that scoring working as I expected