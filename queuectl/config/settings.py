import os
from typing import Any, Dict

DEFAULTS = {
    "DB_PATH": os.environ.get("QUEUECTL_DB", "queuectl.db"),
    "MAX_RETRIES": int(os.environ.get("QUEUECTL_MAX_RETRIES", "3")),
    "BACKOFF_BASE": int(os.environ.get("QUEUECTL_BACKOFF_BASE", "2")),
    "BACKOFF_MAX": int(os.environ.get("QUEUECTL_BACKOFF_MAX", "600")),
    "WORKER_COUNT": int(os.environ.get("QUEUECTL_WORKER_COUNT", "1")),
    "LOG_LEVEL": os.environ.get("QUEUECTL_LOG_LEVEL", "INFO"),
    "JOB_TIMEOUT": int(os.environ.get("QUEUECTL_JOB_TIMEOUT", "30")),  # default 30 seconds
    "DEFAULT_PRIORITY": int(os.environ.get("QUEUECTL_DEFAULT_PRIORITY", "10")),
}


class Settings:
    def __init__(self, overrides: Dict[str, Any] = None):
        self._values = dict(DEFAULTS)
        if overrides:
            self._values.update(overrides)

    def get(self, key: str) -> Any:
        return self._values.get(key)

    def set(self, key: str, value: Any) -> None:
        self._values[key] = value

    def as_dict(self) -> Dict[str, Any]:
        return dict(self._values)
