# async-patterns-py

Personal reference for Python concurrency patterns. Every file runs standalone and shows the pattern in action with real output.

I keep coming back to the same questions — "should I use gather or TaskGroup here?", "will threads help or is this GIL-limited?", "how do I do producer/consumer without a race condition?" — so I decided to write them all down in one place with code that actually runs.

## Structure

```
asyncio/     — event loop patterns
threads/     — threading primitives and thread pools
processes/   — multiprocessing and IPC
benchmarks/  — actual numbers for i/o-bound and cpu-bound work
```

## Quick reference

**I/O-bound work** (network, DB, disk):
- Sync code → `ThreadPoolExecutor`
- Async code → `asyncio.gather` or `TaskGroup`
- High concurrency → asyncio with `Semaphore`

**CPU-bound work** (parsing, hashing, computation):
- `ProcessPoolExecutor` — bypasses the GIL
- Threads won't help (GIL serializes CPU execution)

**Rule of thumb**: if you're waiting → threads or asyncio. If you're computing → processes.

## asyncio

| File | Pattern | When to use |
|------|---------|-------------|
| `01_gather.py` | `asyncio.gather` | Fan-out: run N independent coroutines in parallel |
| `02_task_group.py` | `TaskGroup` | Structured concurrency: cancel everything if one fails |
| `03_semaphore.py` | `Semaphore` | Limit concurrent connections / rate limiting |
| `04_queue.py` | `asyncio.Queue` | Producer/consumer with backpressure |
| `05_timeout.py` | `wait_for` / `timeout` | Deadlines, cancellation, cleanup |
| `06_run_in_executor.py` | `run_in_executor` | Calling blocking sync code from async |

`gather` vs `TaskGroup`: gather is convenient but orphans tasks on failure. TaskGroup cancels everything when one fails — use it when correctness matters.

## threads

| File | Pattern | When to use |
|------|---------|-------------|
| `01_thread_pool.py` | `ThreadPoolExecutor` | Parallel blocking I/O in sync code |
| `02_locks.py` | `Lock`, `RLock`, `Condition` | Shared mutable state |
| `03_queue.py` | `queue.Queue` | Thread-safe message passing |
| `04_events.py` | `Event`, `Barrier`, `local()` | Coordination: start signals, phase sync, per-thread state |

## processes

| File | Pattern | When to use |
|------|---------|-------------|
| `01_process_pool.py` | `ProcessPoolExecutor` | CPU-bound fan-out |
| `02_shared_memory.py` | `shared_memory` | Zero-copy large data between processes |
| `03_ipc_queue.py` | `Queue`, `Pipe`, `Manager` | Inter-process communication |

## benchmarks

```bash
python3 benchmarks/io_bound.py
python3 benchmarks/cpu_bound.py
```

Sample results on a 4-core machine:

**I/O-bound** (20 ops × 50ms):
```
sequential         1.002s
threads            0.105s   → 9.6x faster
asyncio            0.051s   → 19.6x faster
```

**CPU-bound** (8 tasks, prime counting):
```
sequential         0.488s
threads            0.495s   → 0.98x  ← GIL, no gain
processes          0.172s   → 2.83x  ← real parallelism
```

## Running

No dependencies outside stdlib. Python 3.11+ required (TaskGroup, asyncio.timeout).

```bash
python3 asyncio/01_gather.py
python3 threads/02_locks.py
python3 processes/01_process_pool.py
# etc.
```

---
tested on Python 3.11+

<!-- yolo -->
