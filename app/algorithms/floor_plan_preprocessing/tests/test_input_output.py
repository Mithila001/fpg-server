from app.algorithms.floor_plan_preprocessing import (
    PreparedGenerationInput,
    prepare_generation_input,
)
from app.algorithms.types_new import FloorPlanGenerationSpec


def test_prepare_generation_input_returns_expected_contract(
    preprocessing_input,
):
    result = prepare_generation_input(preprocessing_input)

    assert isinstance(result, PreparedGenerationInput)
    assert isinstance(
        result.generation_spec,
        FloorPlanGenerationSpec,
    )
    assert result.generation_spec.floor is not None
    assert len(result.generation_spec.rooms) > 0
    assert result.report is not None