
class BaseTracker:
    def __init__(self):
        self.logs = []

    def _add_log(self, stage, message, status):
        entry = f"[{status}] {stage}: {message}"
        self.logs.append(entry)
        # Optional: still print to console immediately if it's a critical error
        if status == "❌":
            print(f"DEBUG ALERT: {entry}")

class ErrorTracker(BaseTracker):
    """Focuses on tracking and displaying ONLY things that went wrong."""
    
    def log_error(self, stage, message):
        """Specifically for hard failures or logic gaps."""
        self._add_log(stage, message, "❌")

    def log_skip(self, stage, message):
        """Specifically for when a constraint is ignored (Silent Failure)."""
        self._add_log(stage, message, "⚠️")

    def show_error_summary(self):
        # Filter logs to show only Warnings and Errors
        error_logs = [l for l in self.logs if "❌" in l or "⚠️" in l]  # noqa: E741
        
        if not error_logs:
            print("\n✅ SETUP CHECK: No execution errors or skips detected.")
            return

        print("\n" + "!"*45)
        print("🛠️  CRITICAL EXECUTION & SKIP SUMMARY")
        print("!"*45)
        for log in error_logs:
            print(log)
        print("!"*45 + "\n")

# Global instance
tracker = ErrorTracker()