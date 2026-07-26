from enum import StrEnum


class FeatureKey(StrEnum):
    APPLICATION = "application"
    PIPELINE = "pipeline"
    PREPROCESSING = "preprocessing"
    CANDIDATE_SEARCH = "candidate_search"
    CANDIDATE_SCORING = "candidate_scoring"
    FLOOR_PLAN_SOLVER = "floor_plan_solver"
    FLOOR_PLAN_POST_PROCESSING = "floor_plan_post_processing"
    FLOOR_PLAN_OPENINGS = "floor_plan_openings"
    FLOOR_PLAN_SCORING = "floor_plan_scoring"
    VISUALIZATION = "visualization"


class ArtifactFormat(StrEnum):
    JSON = "json"
    PNG = "png"


class ArtifactKind(StrEnum):
    EVENT_LOG = "event_log"
    DIAGNOSTIC = "diagnostic"
    SCORE_BREAKDOWN = "score_breakdown"
    FLOOR_PLAN_DATA = "floor_plan_data"
    VISUALIZATION = "visualization"
    FINAL_RESULT = "final_result"


class ArtifactScope(StrEnum):
    GLOBAL = "global"
    FLOW = "flow"
    SEARCH_TRIAL = "search_trial"
    CANDIDATE = "candidate"
    SOLVER_RUN = "solver_run"


class WriteMode(StrEnum):
    CREATE = "create"
    REPLACE = "replace"
