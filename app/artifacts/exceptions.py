class ArtifactError(Exception):
    """Base artifact persistence error."""


class ArtifactSerializationError(ArtifactError):
    """Raised when a value cannot be represented safely as JSON."""


class ArtifactWriteError(ArtifactError):
    """Raised when a requested artifact write is invalid."""
