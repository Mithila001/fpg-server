from __future__ import annotations

from pathlib import Path

import pytest

from app.artifacts import ArtifactStorage, ArtifactStorageConfig, FeatureKey
from app.util.logger import BaseLogger


def test_logging_failure_is_reported_without_escaping(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    storage = ArtifactStorage(ArtifactStorageConfig(output_root=tmp_path))
    monkeypatch.setattr(
        storage,
        "save_json",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("disk full")),
    )
    logger = BaseLogger(storage, console=False)

    result = logger.log(
        feature=FeatureKey.APPLICATION,
        event="test_failure",
    )

    assert result is None
    stderr = capsys.readouterr().err
    assert "logging_failure" in stderr
    assert "disk full" in stderr
