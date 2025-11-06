import subprocess
import shlex
import time
from multiprocessing import Event
from typing import Dict, Any
from queuectl.core.storage import Storage
from queuectl.core.queue import Queue
from queuectl.core.backoff import exponential_backoff
from datetime import datetime

class Worker:
    def __init__(self, storage: Storage, worker_id: int, stop_event: Event,
                 base_backoff: int, max_backoff: int, max_retries: int):
        self.storage = storage
        self.queue = Queue(storage)
        self.worker_id = worker_id
        self.stop_event = stop_event
        self.base_backoff = base_backoff
        self.max_backoff = max_backoff
        self.max_retries = max_retries

    def run_command(self, command: str, timeout: int) -> (int, str, str):
        try:
            args = command if isinstance(command, list) else shlex.split(command)
            proc = subprocess.run(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout
            )
            return proc.returncode, proc.stdout, proc.stderr
        except subprocess.TimeoutExpired:
            return -2, "", "Process timed out"
        except FileNotFoundError:
            return 127, "", "Command not found"
        except Exception as e:
            return 1, "", str(e)

    def _execute_and_handle(self, job: Dict[str, Any]) -> None:
        timeout = job.get("timeout_seconds") or 30  # default 30 sec
        start_time = time.time()
        code, stdout, stderr = self.run_command(job["command"], timeout)
        runtime = time.time() - start_time

        # Save logs
        self.storage.insert_job_log(job["id"], stdout, stderr)
        # Save runtime metric
        self.storage.insert_job_metric(job["id"], runtime)

        now = datetime.utcnow().isoformat()
        if code == 0:
            job["state"] = "completed"
            job["updated_at"] = now
            job["last_error"] = None
            self.storage.update_job(job)
        else:
            attempts = int(job.get("attempts", 0)) + 1
            job["attempts"] = attempts
            error_msg = f"Exit code {code}" if code >=0 else stderr or "Timeout"
            if attempts >= int(job.get("max_retries", self.max_retries)):
                self.storage.move_to_dlq(job, last_error=error_msg)
            else:
                delay = exponential_backoff(attempts, self.base_backoff, self.max_backoff)
                if delay > 0:
                    time.sleep(min(delay, self.max_backoff))
                job["state"] = "pending"
                job["updated_at"] = now
                job["last_error"] = error_msg
                self.storage.upsert_job(job)

    def run(self):
        while not self.stop_event.is_set():
            job = self.queue.fetch_next()
            if not job:
                time.sleep(0.2)
                continue
            self._execute_and_handle(job)
