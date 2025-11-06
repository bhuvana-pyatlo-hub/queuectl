# queuectl

queuectl is a lightweight, reliable job queue system designed to simplify asynchronous task processing. It supports key features such as retries with exponential backoff, dead letter queues (DLQ) for permanently failed jobs, job prioritization, scheduled execution, detailed job logging, and runtime metrics. This system enables multiple workers to safely process jobs concurrently, ensuring no duplication or race conditions.

---

## Setup Instructions


Follow these steps to set up queuectl and run it locally:

### 1. Clone the repository

``` 

git clone https://github.com/bhuvana-pyatlo-hub/queuectl.git

```
### 2. Change to a correct Directory

```

cd queuectl

```

### 3. Create and activate a Python virtual environment

- **On Windows (Git Bash):**


``` 

python -m venv venv
source venv/bin/activate

```
### 4. Install dependencies

```

pip install -r requirements.txt

```

---

## Usage Examples and Commands

This section explains each CLI command with examples and detailed descriptions of their functionality.

### Enqueue a job

```

python -m queuectl.cli enqueue '{"id":"job1","command":"echo Hello World"}'

```

- **Output**

```
Enqueued: job1
```

- **What it does:** Adds a new job with ID `job1` that runs the shell command `echo Hello World`.
- **Feature:** Jobs are added to the queue in `pending` state, awaiting processing by workers.

---

### Enqueue a job with priority

```

python -m queuectl.cli enqueue '{"id":"job_high","command":"echo High priority job","priority":1}'

python -m queuectl.cli enqueue '{"id":"job_low","command":"echo Low priority job","priority":20}'

```
- **Output:** 

```

job2 enqueued with priority 2
job3 enqueued with priority 20

```
- **What it does:** Sets jobs with explicit priority; lower `priority` values denote higher priority.
- **Feature:** Ensures important jobs get processed before less critical ones.

---

### Enqueue a scheduled job

```

future_time=$(date -u -d '+1 minute' +"%Y-%m-%dT%H:%M:%S")
python -m queuectl.cli enqueue "{"id":"job_scheduled","command":"echo Scheduled job","run_at":"$future_time"}"

```
- **Output:** 

```

 job_scheduled scheduled for 2025-11-06T10:45:00Z.

```
- **What it does:** Adds a job that will execute only at or after the given `run_at` UTC timestamp.
- **Feature:** Enables delay or scheduling of jobs for future execution.

---

### Start workers

```

python -m queuectl.cli worker start --count 3

```
- **Output:**

```
Starting 3 worker(s)...
Worker 1 started job2 (PID 976)
Worker 2 started job1 (PID 15776)
Worker 3 started job3 (PID 32076)          

```
- **What it does:** Starts 3 concurrent worker processes that fetch and execute jobs from the queue.
- **Feature:** Workers honor job priority, scheduled times, manage retries with exponential backoff, and enforce timeouts.

---

### List jobs by state
- **Command:**

```
python -m queuectl.cli list --state 'state_name'

```
- **Example:**

```

python -m queuectl.cli list --state completed

```
- **Output:**

```
{
    "id": "job1",
    "command": "echo Hello World",
    "state": "completed",
    "attempts": 0,
    "max_retries": 3,
    "created_at": "2025-11-06T05:52:23.367289",
    "updated_at": "2025-11-06T06:04:48.673919",
    "last_error": null,
    "run_at": null,
    "priority": 10,
    "timeout_seconds": null
  },
  {
    "id": "job2",
    "command": "echo This is a high priority job",
    "state": "completed",
    "attempts": 0,
    "max_retries": 3,
    "created_at": "2025-11-06T05:55:48.369774",
    "updated_at": "2025-11-06T06:04:48.649293",
    "last_error": null,
    "run_at": null,
    "priority": 1,
    "timeout_seconds": null
  },
  {
    "id": "job3",
    "command": "echo This is a low priority job",
    "state": "completed",
    "attempts": 0,
    "max_retries": 3,
    "created_at": "2025-11-06T06:04:24.864423",
    "updated_at": "2025-11-06T06:04:48.693338",
    "last_error": null,
    "run_at": null,
    "priority": 20,
    "timeout_seconds": null
  }

```

- **What it does:** Lists jobs filtered by specified states: `pending`, `processing`, `completed`, or `failed`.
- **Feature:** Helps monitor the lifecycle and progress of jobs.

---

### View logs for a job

```

python -m queuectl.cli logs job1

```
- **Output:**

```

Logs for job job1:

[2025-11-06T06:04:48.632970] stdout:
Hello World

Average runtime: 0.56s over 2 runs.

```

- **What it does:** Fetches and displays stdout and stderr logs produced during job execution.
- **Feature:** Provides detailed insight into job output and debugging info.

---

### View Dead Letter Queue (DLQ)

``` 

python -m queuectl.cli dlq list

```
- **Output:**

```
[
  {
    "id": "job_fail",
    "command": "exit 1",
    "attempts": 3,
    "created_at": "2025-11-06T03:25:09.086269",
    "id": "job_fail",
    "command": "exit 1",
    "attempts": 3,
    "created_at": "2025-11-06T03:25:09.086269",
    "last_error": "Exit code 127"
  },
  {
    "id": "job_timeout",
    "command": "sleep 10",
    "attempts": 3,
    "created_at": "2025-11-06T03:35:43.063726",
    "last_error": "Process timed out"
    "id": "job_fail",
    "command": "exit 1",
    "attempts": 3,
    "created_at": "2025-11-06T03:25:09.086269",
    "last_error": "Exit code 127"
  }
]

```

- **What it does:** Lists all jobs that failed after reaching the maximum number of retry attempts and have been moved to DLQ.
- **Feature:** Identifies jobs requiring manual intervention or investigation.


---

### Configuration parameter

```

python -m queuectl.cli config set max_retries 5

```
- **Ouptut:**

```

Config set max_retries = 5

```
- **What it does:** Dynamically sets the `max_retries` configuration parameter to 5.
- **Feature:** Allows tuning system behavior without code changes or restarts.

---

### Job Timeout Handling

Enqueue a job with a timeout of 5 seconds; the command sleeps 10 seconds and will timeout:

```
python -m queuectl.cli enqueue '{"id":"timeout_job","command":"sleep 10","timeout_seconds":5}'

```

```
python -m queuectl.cli worker start --count 1

```

```
python -m queuectl.cli logs timeout_job

```

- **Output**

```
Enqueued: timeout_job

```

```
Logs for job timeout_job:

Process timed out
[2025-11-06T06:44:20.071386] stdout:
Average runtime: 5.06s over 3 runs.

```
- **What it does:** Allows specifying a maximum execution time (`timeout_seconds`) for a job. If the job runs longer than this limit, it is forcefully terminated to prevent workers from hanging indefinitely.
- **Feature:** Improves system stability by avoiding stuck jobs.  Enables automatic retries with backoff after timeouts to enhance job success
---

### 5. Metrics or Execution Stats

View job status summary (provides counts of jobs per state and number of workers running):

```
python -m queuectl.cli status

```
- **Output:**

```
Job counts: {'pending': 0, 'processing': 0, 'completed': 0, 'failed': 0, 'dead': 0}
Workers: 1

```
- **What it does:** Displays a summary of job counts by state (`pending`, `processing`, `completed`, `failed`, `dead`) and reports the number of active workers.
- **Feature:** Provides insights into queue workload and system health. Helps with monitoring job throughput, failures, and backlog for operational decisions.

---

## Architecture Overview

- **Job States:** Jobs progress through states: `pending` → `processing` → `completed` or `failed`.
- **Persistence:** All job metadata, logs, and metrics are stored persistently in an SQLite database to survive restarts.
- **Concurrency:** Multiple workers safely fetch jobs atomically from the database to avoid duplicate processing.
- **Retry Mechanism:** Failed jobs automatically retry using exponential backoff until the `max_retries` limit is reached.
- **Dead Letter Queue:** Jobs that fail beyond retries move to DLQ for manual review.
- **Priority & Scheduling:** Jobs respect user-set priority numbers, running higher priority jobs first, and scheduled jobs run only when their `run_at` timestamp arrives.
- **Logging & Metrics:** Workers log stdout/stderr output and update runtime statistics for monitoring.
- **Timeouts:** Jobs have configurable execution timeouts, force-killing hung commands.

---

## Assumptions & Trade-offs

- **SQLite database:** Chosen for ease of use, durability, and simple atomic operations. Trade-off is limited scalability under high concurrency or distributed environments.
- **Shell command execution:** Flexibility to run arbitrary commands, but requires external input sanitization for security.
- **Backoff algorithm:** Exponential backoff reduces system overload but may delay urgent retries.
- **Single-database coordination:** Simplifies job locking and concurrency but may bottleneck with many workers.
- **Scheduling granularity:** Dependent on worker polling intervals; precise timing not guaranteed.

---

## Testing Instructions

1. **Basic job processing:**
   - Enqueue simple jobs and verify they complete successfully.
2. **Failure and retry:**
   - Enqueue jobs designed to fail (e.g., invalid commands), observe retries and final DLQ placement.
3. **Priority enforcement:**
   - Enqueue multiple jobs with varying priorities; confirm higher priority jobs run first.
4. **Scheduled jobs:**
   - Enqueue jobs with future `run_at` times and confirm execution only occurs after that time.
5. **Concurrency and safety:**
   - Start multiple workers and ensure no duplicated job executions and consistent state transitions.
6. **Log output validation:**
   - Use `logs` command to verify job output correctness.
7. **Dynamic configuration:**
   - Change parameters at runtime (e.g., max retries) and observe expected behavior changes.
8. **Worker lifecycle:**
   - Test graceful stopping of workers during processing with `worker stop`.
9. **Persistence:**
   - Restart workers and/or the system, confirm jobs resume correctly with no loss.
  
---
## Demo Video

A working CLI demonstration showcasing queuectl's core features is available below:

[![queuectl Demo Video](https://img.shields.io/badge/Watch_Demo-Video-blue?style=for-the-badge)](https://amritacampusamaravati-my.sharepoint.com/:v:/g/personal/av_en_u4aie22030_av_students_amrita_edu/EZ_QtI3osP5GjKoFsJKa6s0BpZ4MIB8dB4_UiTIlbTxPBg?e=LKAe3d)

----


This README fully addresses setup, usage, architecture, assumptions, trade-offs, and testing to provide users and reviewers with a comprehensive understanding of queuectl, its commands, and its features.


