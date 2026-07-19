from app.algorithms.floor_plan_preprocessing.normalization import prepare_reference_data
from app.algorithms.floor_plan_preprocessing.validation import validate_reference_data
from app.pipeline.generation.context import load_generation_reference_data


def test_packaged_generation_reference_data_is_valid():
    reference_data = load_generation_reference_data()

    assert reference_data.room_sizes
    assert reference_data.room_relations
    validate_reference_data(prepare_reference_data(reference_data))
