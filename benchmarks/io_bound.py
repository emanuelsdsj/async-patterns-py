"""
Benchmark: I/O-bound work — sequential vs threads vs asyncio

The question answered here: when your bottleneck is waiting (network, DB, disk),
which concurrency approach gives you the best throughput?

Expected results:
- Sequential: slowest — waits for each operation to complete
- Threads:    much faster — multiple I/O waits in parallel (GIL released during I/O)
- Asyncio:    similar to threads or faster — no thread overhead, single event loop

Both threads and asyncio are good for I/O. Asyncio tends to win at very
high concurrency (thousands of connections) because threads have memory and
scheduling overhead. For moderate concurrency (tens to hundreds), they're similar.
"""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor

# Simulates I/O latency without actually hitting the network.
# In a real benchmark you'd use actual HTTP calls, but for reproducibility
# we simulate 50ms per operation.
OPERATION_COUNT = 20
IO_LATENCY = 0.05  # 50ms per operation


# --- Implementations ---

def blocking_io_call(op_id: int) -> str:
    """Simulates a blocking network/DB call."""
    time.sleep(IO_LATENCY)
    return f"result-{op_id}"


async def async_io_call(op_id: int) -> str:
    """Simulates an async network/DB call."""
    await asyncio.sleep(IO_LATENCY)
    return f"result-{op_id}"


def run_sequential() -> list[str]:
    return [blocking_io_call(i) for i in range(OPERATION_COUNT)]


def run_threads(max_workers: int = 10) -> list[str]:
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        results = list(pool.map(blocking_io_call, range(OPERATION_COUNT)))
    return results


async def run_asyncio() -> list[str]:
    return await asyncio.gather(*[async_io_call(i) for i in range(OPERATION_COUNT)])


async def run_asyncio_semaphore(max_concurrent: int = 10) -> list[str]:
    """Asyncio with a semaphore to limit concurrency — more realistic."""
    sem = asyncio.Semaphore(max_concurrent)

    async def bounded(op_id: int) -> str:
        async with sem:
            return await async_io_call(op_id)

    return await asyncio.gather(*[bounded(i) for i in range(OPERATION_COUNT)])


# --- Runner ---

def benchmark(label: str, fn, *args):
    t0 = time.perf_counter()
    if asyncio.iscoroutinefunction(fn):
        result = asyncio.run(fn(*args))
    else:
        result = fn(*args)
    elapsed = time.perf_counter() - t0
    print(f"  {label:<40} {elapsed:.3f}s  ({len(result)} results)")
    return elapsed


def main():
    theoretical_sequential = OPERATION_COUNT * IO_LATENCY
    theoretical_parallel = IO_LATENCY  # if all run at once

    print(f"Benchmark: {OPERATION_COUNT} I/O operations × {IO_LATENCY*1000:.0f}ms each")
    print(f"  theoretical sequential: {theoretical_sequential:.2f}s")
    print(f"  theoretical parallel:   {theoretical_parallel:.2f}s")
    print()

    seq_time = benchmark("sequential", run_sequential)
    thr_time = benchmark("threads (10 workers)", run_threads, 10)
    asy_time = benchmark("asyncio (unlimited)", run_asyncio)
    asy_sem  = benchmark("asyncio (semaphore=10)", run_asyncio_semaphore, 10)

    print()
    print(f"  speedup threads vs sequential:  {seq_time / thr_time:.1f}x")
    print(f"  speedup asyncio vs sequential:  {seq_time / asy_time:.1f}x")
    print(f"  threads vs asyncio:             {thr_time / asy_time:.2f}x")


if __name__ == "__main__":
    main()
