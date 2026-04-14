"""
Benchmark: CPU-bound work — sequential vs threads vs processes

The question answered here: when your bottleneck is computation (not I/O),
does concurrency actually help — and which kind?

Expected results:
- Sequential:  baseline
- Threads:     similar to sequential — the GIL serializes CPU execution
- Processes:   significantly faster — real parallelism across cores

This is the GIL in action. Threads in Python can only run one at a time
for CPU-bound work. Processes get their own GIL, so they truly run in parallel.

The crossover point: if your work is mostly I/O with some CPU, threads are fine.
If your work is CPU-heavy (parsing, hashing, numerical computation, ML), use processes.
"""

import hashlib
import math
import time
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor


TASK_COUNT = 8


# Must be module-level for pickling (ProcessPoolExecutor requirement)

def cpu_task(n: int) -> int:
    """
    CPU-bound: count primes up to n.
    Takes ~150-300ms depending on hardware.
    """
    count = 0
    for candidate in range(2, n):
        if candidate == 2:
            count += 1
            continue
        if candidate % 2 == 0:
            continue
        is_prime = True
        for divisor in range(3, int(math.sqrt(candidate)) + 1, 2):
            if candidate % divisor == 0:
                is_prime = False
                break
        if is_prime:
            count += 1
    return count


def run_sequential(n: int) -> list[int]:
    return [cpu_task(n) for _ in range(TASK_COUNT)]


def run_threads(n: int, max_workers: int = 4) -> list[int]:
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        return list(pool.map(cpu_task, [n] * TASK_COUNT))


def run_processes(n: int, max_workers: int = 4) -> list[int]:
    with ProcessPoolExecutor(max_workers=max_workers) as pool:
        return list(pool.map(cpu_task, [n] * TASK_COUNT))


def benchmark(label: str, fn, *args) -> float:
    t0 = time.perf_counter()
    result = fn(*args)
    elapsed = time.perf_counter() - t0
    print(f"  {label:<40} {elapsed:.3f}s  (result: {result[0]})")
    return elapsed


def main():
    # Tune this so one task takes ~200-300ms on your machine
    N = 80_000

    print(f"Benchmark: {TASK_COUNT} CPU-bound tasks (prime count up to {N})")
    print()

    seq_time = benchmark("sequential", run_sequential, N)
    thr_time = benchmark("threads (4 workers)", run_threads, N, 4)
    prc_time = benchmark("processes (4 workers)", run_processes, N, 4)

    print()
    print(f"  threads vs sequential:   {seq_time / thr_time:.2f}x  ← GIL, no real gain")
    print(f"  processes vs sequential: {seq_time / prc_time:.2f}x  ← real parallelism")
    print(f"  processes vs threads:    {thr_time / prc_time:.2f}x")
    print()
    print("  Note: process speedup is limited by number of cores and pickling overhead.")


if __name__ == "__main__":
    main()
