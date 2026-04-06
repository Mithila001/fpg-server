"""Custom exceptions for Optuna optimization workflow."""


class TrialTimeoutError(Exception):
    """Raised when trial optimization exceeds timeout without finding feasible result."""

    def __init__(self, elapsed_time: float, timeout_seconds: int):
        """
        Initialize TrialTimeoutError.

        Args:
            elapsed_time: Actual time elapsed before timeout (in seconds)
            timeout_seconds: The configured timeout limit (in seconds)
        """
        self.elapsed_time = elapsed_time
        self.timeout_seconds = timeout_seconds
        message = f"Did not find a feasible result within {timeout_seconds} seconds"
        super().__init__(message)
