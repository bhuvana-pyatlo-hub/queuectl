import sqlite3
import threading
from datetime import datetime
from typing import Optional, List, Dict, Any

DB_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    command TEXT NOT NULL,
    state TEXT NOT NULL,
    attempts INTEGER NOT NULL,
    max_retries INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    last_error TEXT,
    run_at TEXT,
    priority INTEGER NOT NULL DEFAULT 10,
    timeout_seconds INTEGER DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS dlq (
    id TEXT PRIMARY KEY,
    command TEXT NOT NULL,
    attempts INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    last_error TEXT
);

CREATE TABLE IF NOT EXISTS job_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    stdout TEXT,
    stderr TEXT
);

CREATE TABLE IF NOT EXISTS job_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    runtime_seconds REAL NOT NULL
);
"""

class Storage:
    def __init__(self, db_path: str):
        self._db_path = db_path
        self._lock = threading.Lock()
        self._init_db()

    def _conn(self):
        return sqlite3.connect(self._db_path, check_same_thread=False)

    def _init_db(self):
        with self._conn() as conn:
            conn.executescript(DB_SCHEMA)
            conn.commit()

    def upsert_job(self, job: Dict[str, Any]) -> None:
        sql = """
        INSERT INTO jobs
        (id, command, state, attempts, max_retries, created_at, updated_at, last_error, run_at, priority, timeout_seconds)
        VALUES
        (:id, :command, :state, :attempts, :max_retries, :created_at, :updated_at, :last_error, :run_at, :priority, :timeout_seconds)
        ON CONFLICT(id) DO UPDATE SET
            command=excluded.command,
            state=excluded.state,
            attempts=excluded.attempts,
            max_retries=excluded.max_retries,
            created_at=excluded.created_at,
            updated_at=excluded.updated_at,
            last_error=excluded.last_error,
            run_at=excluded.run_at,
            priority=excluded.priority,
            timeout_seconds=excluded.timeout_seconds;
        """
        with self._lock, self._conn() as conn:
            conn.execute(sql, {
                "id": job["id"],
                "command": job["command"],
                "state": job["state"],
                "attempts": job.get("attempts", 0),
                "max_retries": job.get("max_retries", 3),
                "created_at": job.get("created_at"),
                "updated_at": job.get("updated_at"),
                "last_error": job.get("last_error"),
                "run_at": job.get("run_at"),
                "priority": job.get("priority", 10),
                "timeout_seconds": job.get("timeout_seconds"),
            })
            conn.commit()

    def fetch_next_pending(self) -> Optional[Dict[str, Any]]:
        with self._lock, self._conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, command, state, attempts, max_retries, created_at,
                    updated_at, last_error, run_at, priority, timeout_seconds
                FROM jobs
                WHERE state = 'pending' AND (run_at IS NULL OR run_at <= ?)
                ORDER BY priority ASC, created_at ASC
                LIMIT 1
            """, (datetime.utcnow().isoformat(),))
            row = cur.fetchone()
            if not row:
                return None
            (job_id, command, _, attempts, max_retries, created_at, _, last_error,
             run_at, priority, timeout_seconds) = row
            now = datetime.utcnow().isoformat()
            cur.execute("UPDATE jobs SET state = ?, updated_at = ? WHERE id = ?",
                       ("processing", now, job_id))
            conn.commit()
            return {
                "id": job_id,
                "command": command,
                "state": "processing",
                "attempts": attempts,
                "max_retries": max_retries,
                "created_at": created_at,
                "updated_at": now,
                "last_error": last_error,
                "run_at": run_at,
                "priority": priority,
                "timeout_seconds": timeout_seconds,
            }

    def update_job(self, job: Dict[str, Any]) -> None:
        with self._lock, self._conn() as conn:
            conn.execute("""
                UPDATE jobs SET state = ?, attempts = ?, updated_at = ?,
                last_error = ?, run_at = ?, priority = ?, timeout_seconds = ?
                WHERE id = ?
            """, (
                job["state"],
                job.get("attempts", 0),
                job.get("updated_at", datetime.utcnow().isoformat()),
                job.get("last_error"),
                job.get("run_at"),
                job.get("priority", 10),
                job.get("timeout_seconds"),
                job["id"],
            ))
            conn.commit()

    def list_jobs(self, state: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._lock, self._conn() as conn:
            cur = conn.cursor()
            if state:
                cur.execute("""
                    SELECT id, command, state, attempts, max_retries, created_at,
                        updated_at, last_error, run_at, priority, timeout_seconds
                    FROM jobs WHERE state = ?
                """, (state,))
            else:
                cur.execute("""
                    SELECT id, command, state, attempts, max_retries, created_at,
                        updated_at, last_error, run_at, priority, timeout_seconds
                    FROM jobs
                """)
            rows = cur.fetchall()
            return [
                {
                    "id": r[0],
                    "command": r[1],
                    "state": r[2],
                    "attempts": r[3],
                    "max_retries": r[4],
                    "created_at": r[5],
                    "updated_at": r[6],
                    "last_error": r[7],
                    "run_at": r[8],
                    "priority": r[9],
                    "timeout_seconds": r[10],
                }
                for r in rows
            ]

    def delete_job(self, job_id: str) -> None:
        with self._lock, self._conn() as conn:
            conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
            conn.commit()

    def move_to_dlq(self, job: Dict[str, Any], last_error: str) -> None:
        with self._lock, self._conn() as conn:
            conn.execute("DELETE FROM jobs WHERE id = ?", (job["id"],))
            conn.execute("""
                INSERT OR REPLACE INTO dlq (id, command, attempts, created_at, last_error)
                VALUES (:id, :command, :attempts, :created_at, :last_error)
            """, {
                "id": job["id"],
                "command": job["command"],
                "attempts": job.get("attempts", 0),
                "created_at": job.get("created_at") or job.get("updated_at"),
                "last_error": last_error,
            })
            conn.commit()

    def load_dlq(self) -> List[Dict[str, Any]]:
        with self._lock, self._conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, command, attempts, created_at, last_error FROM dlq")
            rows = cur.fetchall()
            return [
                {"id": r[0], "command": r[1], "attempts": r[2], "created_at": r[3], "last_error": r[4]}
                for r in rows
            ]

    def retry_dlq_item(self, dlq_job_id: str) -> Optional[Dict[str, Any]]:
        with self._lock, self._conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, command, attempts, created_at, last_error FROM dlq WHERE id = ?", (dlq_job_id,))
            row = cur.fetchone()
            if not row:
                return None
            job = {
                "id": row[0],
                "command": row[1],
                "attempts": row[2],
                "created_at": row[3],
                "last_error": row[4],
            }
            now = datetime.utcnow().isoformat()
            cur.execute("DELETE FROM dlq WHERE id = ?", (dlq_job_id,))
            cur.execute("""
                INSERT INTO jobs (id, command, state, attempts, max_retries, created_at, updated_at, last_error, run_at, priority, timeout_seconds)
                VALUES (?, ?, 'pending', ?, (SELECT COALESCE(MAX(max_retries), 3) FROM jobs), ?, ?, ?, NULL, ?, NULL)
            """, (
                job["id"], job["command"], job["attempts"], now, now, job["last_error"],
                10  # default priority after retry
            ))
            conn.commit()
            return job

    def insert_job_log(self, job_id: str, stdout: str, stderr: str):
        with self._lock, self._conn() as conn:
            conn.execute("""
                INSERT INTO job_logs (job_id, timestamp, stdout, stderr)
                VALUES (?, ?, ?, ?)
            """, (job_id, datetime.utcnow().isoformat(), stdout, stderr))
            conn.commit()

    def get_job_logs(self, job_id: str) -> List[Dict[str, Any]]:
        with self._lock, self._conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT timestamp, stdout, stderr FROM job_logs WHERE job_id = ? ORDER BY timestamp", (job_id,))
            rows = cur.fetchall()
            return [{"timestamp": r[0], "stdout": r[1], "stderr": r[2]} for r in rows]

    def insert_job_metric(self, job_id: str, runtime_seconds: float):
        with self._lock, self._conn() as conn:
            conn.execute("""
                INSERT INTO job_metrics (job_id, runtime_seconds)
                VALUES (?, ?)
            """, (job_id, runtime_seconds))
            conn.commit()

    def get_job_metrics(self, job_id: str) -> List[Dict[str, Any]]:
        with self._lock, self._conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT runtime_seconds FROM job_metrics WHERE job_id = ?", (job_id,))
            rows = cur.fetchall()
            return [{"runtime_seconds": r[0]} for r in rows]
