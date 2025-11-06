from queuectl.core.storage import Storage
from queuectl.core.queue import Queue

def test_retry_logic_basic(tmp_path):
    db = str(tmp_path / "test2.db")
    store = Storage(db)
    q = Queue(store)
    job = q.enqueue({"id": "retry1", "command": "false"}, max_retries=2)
    for i in range(2):
        job["state"] = "pending"
        job["attempts"] = i
        store.upsert_job(job)
        next_job = store.fetch_next_pending()
        if next_job:
            store.update_job(next_job)
