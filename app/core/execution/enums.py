from enum import StrEnum


class PipelineStage(StrEnum):
    REQUEST_VALIDATION = "request_validation"
    PREPROCESSING = "preprocessing"
    CANDIDATE_SEARCH = "candidate_search"
    CANDIDATE_SCORING = "candidate_scoring"
    SOLVER = "solver"
    REFINEMENT = "refinement"
    POST_PROCESSING = "post_processing"
    OPENINGS = "openings"
    FLOOR_PLAN_SCORING = "floor_plan_scoring"
    VISUALIZATION = "visualization"
    FINALIZATION = "finalization"
