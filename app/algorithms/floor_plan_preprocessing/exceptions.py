from __future__ import annotations


class FloorPlanPreprocessingError(Exception):
    """Base class for expected preprocessing failures."""


class InputValidationError(FloorPlanPreprocessingError):
    pass


class NormalizationError(FloorPlanPreprocessingError):
    pass


class ReferenceDataError(FloorPlanPreprocessingError):
    pass


class BusinessRuleError(FloorPlanPreprocessingError):
    pass


class RoomPreparationError(FloorPlanPreprocessingError):
    pass


class RelationPreparationError(FloorPlanPreprocessingError):
    pass


class FloorPreparationError(FloorPlanPreprocessingError):
    pass


class ContextValidationError(FloorPlanPreprocessingError):
    pass


class OutputValidationError(FloorPlanPreprocessingError):
    pass
