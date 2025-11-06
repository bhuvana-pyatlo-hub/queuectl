from datetime import datetime
from typing import Dict, Any, Optional, List
from .storage import Storage

class JobState:
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD = "dead"

class Queue:
    def __init__(self, storage: Storage):
        self.storage = storage

    def enqueue(self, payload: Dict[str, Any], max_retries: int = 3) -> Dict[str, Any]:
        now = datetime.utcnow().isoformat()
        job = {
            "id": payload.get("id") or f"job-{datetime.utcnow().timestamp()}",
            "command": payload["command"],
            "state": JobState.PENDING,
            "attempts": 0,
            "max_retries": max_retries,
            "created_at": now,
            "updated_at": now,
            "last_error": None,
            "run_at": payload.get("run_at"),
            "priority": payload.get("priority", 10),
            "timeout_seconds": payload.get("timeout_seconds"),
        }
        self.storage.upsert_job(job)
        return job

    def fetch_next(self) -> Optional[Dict[str, Any]]:
        return self.storage.fetch_next_pending()

    def update(self, job: Dict[str, Any]) -> None:
        self.storage.update_job(job)

    def list(self, state: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.storage.list_jobs(state)
