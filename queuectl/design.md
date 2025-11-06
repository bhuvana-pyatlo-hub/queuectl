# Architecture Design Document — queuectl

## 1. Introduction

This document provides a detailed and systematic overview of queuectl’s architecture to help users, reviewers, and developers fully understand the system’s structure, workflow, and design decisions. It explains how jobs flow through the queue, how workers process jobs, usage of priority and scheduling, the retry/backoff mechanism, logging, and metrics collection.

---

## 2. System Overview

queuectl is a CLI-driven background job queue system designed for reliable asynchronous execution of shell commands. It provides:

- Persistent job storage with SQLite
- Multiple job states and transitions
- Worker concurrency with safe job claiming
- Job priorities and scheduled execution support
- Job retries with exponential backoff
- Dead Letter Queue for permanently failed jobs
- Job output logging and runtime metrics for monitoring

The system balances simplicity, durability, and operational robustness.

---

## 3. Core Components and Their Interactions

### 3.1 Job Storage (SQLite)

- Stores jobs with all metadata: id, command, state, attempts, max retries, timestamps, `run_at`, priority, and timeout.
- Provides atomic operations for inserting, updating, and fetching jobs.
- Includes separate tables for DLQ, logs, and runtime metrics.
- Ensures consistency and durability even under concurrent worker access using threading locks.

### 3.2 Queue and Job Lifecycle

- **States:** `pending` → `processing` → (`completed` / `failed` / `dead`)
- Jobs start as `pending` when enqueued.
- Workers fetch jobs ready for execution (respecting priority and scheduled run time).
- On successful completion, job transitions to `completed`.
- On failure, job increments attempts; retries with backoff or moves to DLQ if max retries reached.

### 3.3 Worker Model

- Multiple workers run as independent processes.
- Workers poll the queue for the next suitable `pending` job, atomically locking it for processing.
- Jobs run as shell commands with configurable timeouts.
- Workers log stdout/stderr and record execution time.
- Failed jobs trigger retry logic with exponential backoff delays.
- Supports graceful shutdown.

### 3.4 Priority and Scheduling

- Jobs have integer `priority` (default 10); lower numbers are higher priority.
- Queue `fetch_next_pending` orders jobs by ascending priority, then creation time.
- Jobs can be scheduled via `run_at` timestamp; workers run jobs only after scheduled time.

### 3.5 Error Handling and Retry Policy

- Workers detect failure by non-zero exit codes or timeouts.
- Retry attempts are incremented; backoff delay calculated via exponential formula capped by max backoff.
- Maximum retry count enforced; exceeded jobs are moved to DLQ.
- DLQ allows manual retry or investigation.

### 3.6 Logging and Metrics

- Job outputs (stdout and stderr) are saved to a logs table with timestamps.
- Runtime durations recorded for each job execution.
- Logs and metrics accessible via CLI for debugging and performance monitoring.

---

## 4. Workflow Summary

The complete job lifecycle and system workflow are documented in `queuectl_workflow.png` located in the project root directory. This diagram illustrates:

- Job states and transitions
- Worker interaction with the queue
- Retry and backoff mechanisms  
- Dead Letter Queue handling
- Component interactions

---

## 5. Design Decisions and Trade-offs

- **SQLite chosen for simplicity and reliability** over distributed DBs; may limit scalability for very high loads.
- **Atomic DB operations** to prevent race conditions instead of complex distributed locks.
- **Shell commands execution** enables maximal flexibility, but requires careful input validation externally to avoid security risks.
- **Exponential backoff** balances retry aggressiveness and system stability.
- **Scheduling with polling** may introduce slight delays; acceptable for most use cases.
- **Separate DLQ history** ensures fault isolation and manual intervention capabilities.

---

## 6. Summary

This architecture provides a balanced solution for robust, auditable background job processing. It carefully manages concurrency, persistence, scheduling, and operational insights, enabling users and operators to run, monitor, and troubleshoot jobs effectively.

---

*This document helps users and reviewers clearly understand how queuectl works, what each component does, and how data and control flow through the system in detail.*
