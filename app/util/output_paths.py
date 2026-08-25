from __future__ import annotations

import os
import re
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[2]
_UNSAFE_COMPONENT = re.compile(r"[^A-Za-z0-9._-]+")


def get_output_root() -> Path:
    """Return the configured project output root without creating it."""

    configured_root = os.getenv("OUTPUT_ROOT")
    if configured_root:
        return Path(configured_root).expanduser().resolve()
    return PROJECT_ROOT / "output"


def utc_timestamp(value: datetime | None = None) -> str:
    """Return a compact, lexically sortable UTC timestamp."""

    current = value or datetime.now(UTC)
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    return current.astimezone(UTC).strftime("%Y%m%dT%H%M%S%fZ")


def safe_path_component(value: str) -> str:
    """Sanitize one user- or feature-provided path component."""

    cleaned = _UNSAFE_COMPONENT.sub("_", str(value).strip()).strip("._")
    if not cleaned:
        raise ValueError("path component cannot be empty")
    return cleaned


def create_run_directory(
    category: str,
    feature: str,
    run_name: str,
    *,
    run_timestamp: str | None = None,
    output_root: str | Path | None = None,
) -> Path:
    """Create a timestamped run folder below stable category/feature folders."""

    root = Path(output_root) if output_root is not None else get_output_root()
    timestamp = run_timestamp or utc_timestamp()
    return create_timestamped_directory(
        root / safe_path_component(category) / safe_path_component(feature),
        run_name,
        run_timestamp=timestamp,
    )


def create_timestamped_directory(
    base_directory: str | Path,
    run_name: str,
    *,
    run_timestamp: str | None = None,
) -> Path:
    """Create one timestamped runtime folder below a stable base directory."""

    timestamp = run_timestamp or utc_timestamp()
    directory = Path(base_directory) / (
        f"{safe_path_component(timestamp)}_{safe_path_component(run_name)}"
    )
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def create_artifact_path(
    directory: str | Path,
    descriptive_name: str,
    extension: str,
    *,
    timestamp: str | None = None,
    unique_id: str | None = None,
) -> Path:
    """Build a timestamped, collision-resistant artifact path in a run folder."""

    normalized_extension = extension.strip().lstrip(".")
    if not normalized_extension:
        raise ValueError("artifact extension cannot be empty")

    artifact_timestamp = timestamp or utc_timestamp()
    artifact_id = safe_path_component(unique_id or uuid4().hex[:8])
    filename = (
        f"{safe_path_component(artifact_timestamp)}_"
        f"{safe_path_component(descriptive_name)}_"
        f"{artifact_id}.{safe_path_component(normalized_extension)}"
    )
    return Path(directory) / filename
