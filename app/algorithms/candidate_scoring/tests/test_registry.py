from __future__ import annotations

import pytest

from app.algorithms.candidate_scoring import EvaluatorKey, EvaluatorRegistry
from app.algorithms.candidate_scoring.exceptions import EvaluatorRegistrationError

from .fakes import FakeEvaluator


def test_registry_registers_and_retrieves_evaluator_by_stable_key() -> None:
    evaluator = FakeEvaluator("alpha")
    registry = EvaluatorRegistry((evaluator,))

    assert registry.contains(EvaluatorKey("alpha")) is True
    assert registry.get(EvaluatorKey("alpha")) is evaluator


def test_registry_rejects_duplicate_keys() -> None:
    with pytest.raises(EvaluatorRegistrationError, match="already registered"):
        EvaluatorRegistry((FakeEvaluator("duplicate"), FakeEvaluator("duplicate")))


def test_registry_reports_missing_key() -> None:
    registry = EvaluatorRegistry()

    with pytest.raises(EvaluatorRegistrationError, match="No evaluator is registered"):
        registry.get(EvaluatorKey("missing"))
