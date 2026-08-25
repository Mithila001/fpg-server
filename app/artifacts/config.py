from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ArtifactStorageConfig:
    output_root: Path
    application_logging_enabled: bool = True
    flow_logging_enabled: bool = True
    json_artifacts_enabled: bool = True
    png_artifacts_enabled: bool = True
    atomic_writes_enabled: bool = True

    @classmethod
    def from_environment(cls) -> "ArtifactStorageConfig":
        default_root = Path(__file__).resolve().parents[2] / "output"
        return cls(
            output_root=Path(os.getenv("OUTPUT_ROOT", default_root)).expanduser().resolve(),
            application_logging_enabled=_env_bool("APPLICATION_LOGGING_ENABLED", True),
            flow_logging_enabled=_env_bool("FLOW_LOGGING_ENABLED", True),
            json_artifacts_enabled=_env_bool("JSON_ARTIFACTS_ENABLED", True),
            png_artifacts_enabled=_env_bool("PNG_ARTIFACTS_ENABLED", True),
            atomic_writes_enabled=_env_bool("ATOMIC_WRITES_ENABLED", True),
        )


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}
