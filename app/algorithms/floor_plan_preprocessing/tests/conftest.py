import pytest

from .builders import build_preprocessing_input


@pytest.fixture
def preprocessing_input():
    return build_preprocessing_input()