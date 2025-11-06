from queuectl.core.storage import Storage
from queuectl.core.queue import Queue

def test_storage_basic(tmp_path):
    db = str(tmp_path / "test.db")
    store = Storage(db)
    q = Queue(store)
    job = q.enqueue({"id": "t1", "command": "echo hello"})
    assert job["id"] == "t1"
    items = q.list()
    assert any(j["id"] == "t1" for j in items)
