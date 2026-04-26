import json
import os
from datetime import datetime


def debug_log_data(data, tag="NO_TAG"):
    """
    Log data with a specific tag to identify the source or type of log.
    """
    # 1. Get the directory where dev_print.py is located
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # 2. Navigate up to project root (fpg-server)
    project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))

    # 3. Define the logs directory
    log_dir = os.path.join(project_root, "logs")

    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_file_path = os.path.join(log_dir, "debug_logs.jsonl")

    # Structure the log entry: timestamp, then tag, then the data
    log_entry = {"timestamp": datetime.now().isoformat(), "tag": tag, "payload": data}

    try:
        with open(log_file_path, "a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    log_entry,
                    # Handle custom classes/objects like FpgRequirements
                    default=lambda o: o.__dict__ if hasattr(o, "__dict__") else str(o),
                    ensure_ascii=False,
                )
                + "\n"
            )
    except Exception as e:
        print(f"Failed to log data: {e}")
