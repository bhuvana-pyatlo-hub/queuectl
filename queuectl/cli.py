import argparse
import json
import sys
import time
import multiprocessing
from queuectl.config.settings import Settings
from queuectl.core.storage import Storage
from queuectl.core.queue import Queue
from queuectl.dlq.store import DLQStore
from queuectl.core.worker import Worker

def worker_target(stop_event, worker_id):
    settings = Settings()
    storage = Storage(settings.get("DB_PATH"))
    w = Worker(
        storage=storage,
        worker_id=worker_id,
        stop_event=stop_event,
        base_backoff=settings.get("BACKOFF_BASE"),
        max_backoff=settings.get("BACKOFF_MAX"),
        max_retries=settings.get("MAX_RETRIES"),
    )
    w.run()

def run_workers(count):
    multiprocessing.set_start_method('spawn', force=True)
    stop_events = [multiprocessing.Event() for _ in range(count)]
    workers = []
    ctx = multiprocessing.get_context("spawn")
    for i in range(count):
        p = ctx.Process(target=worker_target, args=(stop_events[i], i + 1))
        p.start()
        workers.append(p)
        print(f"Worker {i+1} started (PID {p.pid})")
    print("Workers started. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutdown requested. Stopping workers...")
        for ev in stop_events:
            ev.set()
        for p in workers:
            p.join(timeout=5)
        print("All workers stopped.")

def main():
    parser = argparse.ArgumentParser(
        prog="queuectl",
        description="CLI-based background job queue system."
    )
    sub = parser.add_subparsers(dest="cmd")

    enq = sub.add_parser("enqueue", help="Enqueue a new job.")
    enq.add_argument("payload", type=str, help='JSON payload e.g. \'{"id":"job1","command":"sleep 2"}\'')

    w = sub.add_parser("worker", help="Manage workers.")
    w_sub = w.add_subparsers(dest="action")
    w_start = w_sub.add_parser("start", help="Start workers.")
    w_start.add_argument("--count", type=int, default=1)
    w_stop = w_sub.add_parser("stop", help="Stop all workers gracefully.")

    st = sub.add_parser("status", help="Show status of jobs and workers.")

    lst = sub.add_parser("list", help="List jobs by state.")
    lst.add_argument("--state", choices=["pending", "processing", "completed", "failed", "dead"])

    dlq = sub.add_parser("dlq", help="DLQ operations.")
    dlq_sub = dlq.add_subparsers(dest="dlq_cmd")
    dlq_sub.add_parser("list", help="List DLQ items.")
    dlq_retry = dlq_sub.add_parser("retry", help="Retry a DLQ item by id.")
    dlq_retry.add_argument("id")

    cfg = sub.add_parser("config", help="Configuration management.")
    cfg_sub = cfg.add_subparsers(dest="cfg_cmd")
    cfg_set = cfg_sub.add_parser("set", help="Set a config value.")
    cfg_set.add_argument("key")
    cfg_set.add_argument("value")
    
    logs = sub.add_parser("logs", help="Show job execution logs.")
    logs.add_argument("job_id", type=str, help="Job ID to show logs and metrics.")

    args = parser.parse_args()

    settings = Settings()
    storage = Storage(settings.get("DB_PATH"))
    q = Queue(storage)

    if args.cmd == "enqueue":
        payload_str = args.payload.strip()
        if payload_str.startswith("'") and payload_str.endswith("'"):
            payload_str = payload_str[1:-1]
        try:
            payload = json.loads(payload_str)
        except Exception as e:
            print(f"\nERROR: Invalid JSON payload for enqueue!\nPayload received: {repr(payload_str)}\nException: {e}\n")
            sys.exit(1)
        job = q.enqueue(payload)
        print(f"Enqueued: {job['id']}")
        return

    if args.cmd == "list":
        state = args.state
        items = q.list(state)
        print(json.dumps(items, indent=2))
        return

    if args.cmd == "status":
        items = q.list()
        counts = {"pending":0, "processing":0, "completed":0, "failed":0, "dead":0}
        for it in items:
            counts[it["state"]] = counts.get(it["state"], 0) + 1
        print("Job counts:", counts)
        print(f"Workers: {settings.get('WORKER_COUNT')}")
        return

    if args.cmd == "dlq":
        dlq_store = DLQStore(storage)
        if args.dlq_cmd == "list":
            items = dlq_store.list_dlq()
            print(json.dumps(items, indent=2))
            return
        if args.dlq_cmd == "retry":
            item = dlq_store.retry(args.id)
            print(f"Retried DLQ item: {args.id} -> requeued." if item else "DLQ item not found.")
            return

    if args.cmd == "config":
        if args.cfg_cmd == "set":
            key, value = args.key, args.value
            if value.isdigit():
                value_parsed = int(value)
            elif value.lower() in ("true", "false"):
                value_parsed = value.lower() == "true"
            else:
                value_parsed = value
            settings.set(key, value_parsed)
            print(f"Config set {key} = {value_parsed}")
            return

    if args.cmd == "worker":
        if args.action == "start":
            if __name__ != "__main__":
                return  # prevent recursive spawn
            run_workers(args.count)
            return
        if args.action == "stop":
            print("Graceful stop not implemented; use Ctrl+C where workers started.")
            return

    if args.cmd == "logs":
        logs = storage.get_job_logs(args.job_id)
        metrics = storage.get_job_metrics(args.job_id)
        print(f"Logs for job {args.job_id}:")
        for log in logs:
            print(f"[{log['timestamp']}] stdout:\n{log['stdout']}")
            if log["stderr"]:
                print(f"stderr:\n{log['stderr']}")
        if metrics:
            avg_runtime = sum(m["runtime_seconds"] for m in metrics) / len(metrics)
            print(f"Average runtime: {avg_runtime:.2f}s over {len(metrics)} runs.")
        else:
            print("No runtime metrics found.")
        return

    print("No valid command provided. Run with -h for help.")

if __name__ == "__main__":
    main()

