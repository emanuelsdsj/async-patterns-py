"""
ProcessPoolExecutor — true parallelism for CPU-bound work

Processes bypass the GIL. Each worker is a separate Python interpreter,
so CPU-bound tasks actually run in parallel across cores.

The tradeoff: data is serialized (pickled) to cross process boundaries.
For large inputs/outputs, that overhead can swamp the gains.

Rules of thumb:
- Use threads for I/O-bound work
- Use processes for CPU-bound work where input/output data is not huge
- If you're passing around large numpy arrays, look into shared_memory (02_shared_memory.py)
"""

import time
import hashlib
import math
from concurrent.futures import ProcessPoolExecutor, as_completed


# Module-level functions only — lambdas and nested functions can't be pickled

def hash_data(data: str) -> str:
    """CPU-bound: hashes a string 200k times."""
    result = data.encode()
    for _ in range(200_000):
        result = hashlib.sha256(result).digest()
    return result.hex()[:12]


def is_prime(n: int) -> bool:
    """CPU-bound: naive primality test."""
    if n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False
    for i in range(3, int(math.sqrt(n)) + 1, 2):
        if n % i == 0:
            return False
    return True


def count_primes(start: int, end: int) -> int:
    """Count primes in a range — meant to be run in parallel chunks."""
    return sum(1 for n in range(start, end) if is_prime(n))


def sequential_hash(items: list[str]) -> list[str]:
    return [hash_data(item) for item in items]


def parallel_hash(items: list[str]) -> list[str]:
    with ProcessPoolExecutor() as pool:
        results = list(pool.map(hash_data, items))
    return results


def parallel_prime_count():
    """
    Split a large range into chunks and count primes in parallel.
    Each chunk runs on a different core.
    """
    total_range = (2, 500_000)
    num_workers = 4
    chunk_size = (total_range[1] - total_range[0]) // num_workers

    chunks = [
        (total_range[0] + i * chunk_size, total_range[0] + (i + 1) * chunk_size)
        for i in range(num_workers)
    ]

    with ProcessPoolExecutor(max_workers=num_workers) as pool:
        chunk_counts = list(pool.map(count_primes, *zip(*chunks)))

    return sum(chunk_counts)


def submit_with_progress():
    """
    submit() lets you track progress as futures complete.
    Useful for long-running jobs where you want incremental feedback.
    """
    items = [f"dataset-{i}" for i in range(8)]

    with ProcessPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(hash_data, item): item for item in items}

        completed = 0
        for future in as_completed(futures):
            item = futures[future]
            result = future.result()
            completed += 1
            print(f"  [{completed}/{len(items)}] {item}: {result}")


def main():
    items = [f"payload-{i}" for i in range(8)]

    print("=== sequential vs parallel hashing ===")
    t0 = time.perf_counter()
    sequential_hash(items)
    seq_time = time.perf_counter() - t0
    print(f"  sequential: {seq_time:.2f}s")

    t0 = time.perf_counter()
    parallel_hash(items)
    par_time = time.perf_counter() - t0
    print(f"  parallel:   {par_time:.2f}s")
    print(f"  speedup:    {seq_time / par_time:.1f}x\n")

    print("=== prime counting in parallel chunks ===")
    t0 = time.perf_counter()
    count = parallel_prime_count()
    elapsed = time.perf_counter() - t0
    print(f"  primes up to 500k: {count} ({elapsed:.2f}s)\n")

    print("=== submit with progress tracking ===")
    submit_with_progress()


if __name__ == "__main__":
    main()
