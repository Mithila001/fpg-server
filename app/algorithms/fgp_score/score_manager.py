# This is the public facing entry file for FPG Scoring System.

# post_processed_floor_plan is list[ProcessedRoomData]

# We will strictly work with only Rectilinear Polygons for scoring.

from app.algorithms.types.domain import ProcessedRoomData


def score_manager(post_processed_floor_plan: list[ProcessedRoomData]) :
    """Main entry point for the FPG scoring system V2."""
    # app/algorithms/fgp_score/score_critical can only 25 score points Max.
    
    
    
    
def _score_critical():
    """Scores critical rules and returns the score out of 25"""
    # Examples: Room Adjacency, Minimum Area Coverage, Hallway Rules
    pass