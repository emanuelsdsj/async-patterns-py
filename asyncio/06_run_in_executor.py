"""
run_in_executor — calling blocking code from async

asyncio is single-threaded. A single blocking call (time.sleep, a sync DB
driver, file I/O) blocks the entire event loop — all other coroutines freeze.

The fix: offload to an executor (thread or process pool) and await the result.

- ThreadPoolExecutor: for I/O-bound blocking code (network, DB, file)
- ProcessPoolExecutor: for CPU-bound code (image processing, crypto, parsing)

The GIL means threads don't help with CPU-bound work — use processes for that.
"""

import asyncio
import time
import hashlib
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor


# --- Blocking functions (simulate sync libraries) ---

def blocking_io(name: str, duration: float) -> str:
    """Simulates a blocking I/O call (e.g., a sync DB driver, requests.get)."""
    time.sleep(duration)
    return f"{name} fetched"


def cpu_intensive(data: str) -> str:
    """Simulates CPU-bound work — hashing a string many times."""
    result = data.encode()
    for _ in range(100_000):
        result = hashlib.sha256(result).digest()
    return result.hex()[:16]


# --- Wrapping them in async ---

async def run_blocking_io_in_thread():
    """
    Default executor is a ThreadPoolExecutor. Good for blocking I/O.
    run_in_executor(None, ...) uses the default executor.
    """
    loop = asyncio.get_event_loop()

    # Sequential blocking calls would freeze the event loop
    # With run_in_executor they run in threads and the event loop stays alive
    results = await asyncio.gather(
        loop.run_in_executor(None, blocking_io, "users-db", 0.3),
        loop.run_in_executor(None, blocking_io, "posts-db", 0.2),
        loop.run_in_executor(None, blocking_io, "cache", 0.1),
    )
    return results


async def run_cpu_work_in_process():
    """
    ProcessPoolExecutor bypasses the GIL — actual parallelism for CPU-bound code.
    Note: the function must be picklable (no lambdas, no closures).
    """
    loop = asyncio.get_event_loop()
    inputs = ["data-a", "data-b", "data-c", "data-d"]

    with ProcessPoolExecutor() as pool:
        results = await asyncio.gather(*[
            loop.run_in_executor(pool, cpu_intensive, inp)
            for inp in inputs
        ])
    return results


async def custom_thread_pool():
    """
    Using a custom ThreadPoolExecutor with a fixed size.
    Useful when you want to limit concurrency for a specific type of work
    without a Semaphore.
    """
    loop = asyncio.get_event_loop()

    with ThreadPoolExecutor(max_workers=2) as pool:
        # max_workers=2 means only 2 threads run at the same time
        results = await asyncio.gather(*[
            loop.run_in_executor(pool, blocking_io, f"source-{i}", 0.1)
            for i in range(6)
        ])
    return results


async def main():
    print("=== blocking I/O in thread executor ===")
    t0 = time.perf_counter()
    results = await run_blocking_io_in_thread()
    elapsed = time.perf_counter() - t0
    for r in results:
        print(f"  {r}")
    print(f"  total: {elapsed:.2f}s (would be ~0.6s sequential)\n")

    print("=== CPU-bound work in process executor ===")
    t0 = time.perf_counter()
    results = await run_cpu_work_in_process()
    elapsed = time.perf_counter() - t0
    for r in results:
        print(f"  hash: {r}")
    print(f"  total: {elapsed:.2f}s\n")

    print("=== custom thread pool (max 2 workers) ===")
    t0 = time.perf_counter()
    results = await custom_thread_pool()
    elapsed = time.perf_counter() - t0
    for r in results:
        print(f"  {r}")
    print(f"  total: {elapsed:.2f}s")


if __name__ == "__main__":
    asyncio.run(main())
