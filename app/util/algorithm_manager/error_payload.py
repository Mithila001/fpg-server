from typing import Any

def error_payload(message: str, status: str = "ERROR") -> dict[str, Any]:
    return {
        "status": status,
        "message": message,
        "union_results": None,
    }
