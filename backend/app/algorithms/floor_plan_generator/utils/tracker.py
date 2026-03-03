class BaseTracker:
    def __init__(self):
        self.logs = []

    def _add_log(self, stage, message, status):
        entry = f"[{status}] {stage}: {message}"
        self.logs.append(entry)
        if status == "❌":
            print(f"DEBUG ALERT: {entry}")


class ErrorTracker(BaseTracker):
    """Tracks and surfaces things that went wrong during constraint setup."""

    def log_error(self, stage, message):
        self._add_log(stage, message, "❌")

    def log_skip(self, stage, message):
        self._add_log(stage, message, "⚠️")

    def show_error_summary(self):
        error_logs = [l for l in self.logs if "❌" in l or "⚠️" in l]  # noqa: E741

        if not error_logs:
            return

        for log in error_logs:
            print(log)

    def get_summary(self) -> list[str]:
        """Return all warning/error log entries."""
        return [l for l in self.logs if "❌" in l or "⚠️" in l]  # noqa: E741


# Global instance shared across the constraints module
tracker = ErrorTracker()
