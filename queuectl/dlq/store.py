from typing import List, Dict, Optional, Any
from queuectl.core.storage import Storage

class DLQStore:
    def __init__(self, storage: Storage):
        self.storage = storage

    def list_dlq(self) -> List[Dict[str, Any]]:
        return self.storage.load_dlq()

    def retry(self, dlq_job_id: str) -> Optional[Dict[str, Any]]:
        return self.storage.retry_dlq_item(dlq_job_id)
