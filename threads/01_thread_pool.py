"""
ThreadPoolExecutor — the right default for I/O-bound sync code

When you can't use asyncio (legacy library, sync framework, etc.),
ThreadPoolExecutor is the go-to. Threads share memory, so no serialization
overhead — but the GIL means they don't help for CPU-bound work.

map() vs submit():
- map(): simpler, blocks until all done, results in order
- submit(): returns Future immediately, more control, results as they complete
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading


def fetch_sync(url: str, delay: float) -> str:
    """Simulates a blocking HTTP call."""
    time.sleep(delay)
    thread_name = threading.current_thread().name
    return f"{url} [{thread_name}]"


def process_item(item: int) -> int:
    time.sleep(0.05)
    return item * item


def map_example():
    """
    executor.map() — clean and simple. Results come back in submission order,
    not completion order. Blocks until all tasks finish.
    """
    urls = [(f"https://api.example.com/{i}", 0.1) for i in range(6)]

    with ThreadPoolExecutor(max_workers=3) as executor:
        # map unpacks arguments when you pass an iterable of tuples with starmap-style
        results = list(executor.map(lambda args: fetch_sync(*args), urls))

    return results


def submit_as_completed():
    """
    submit() + as_completed() — process results as they finish.
    Good when you want to start doing something with results immediately,
    or when tasks have very different durations.
    """
    tasks = {
        "fast": 0.1,
        "medium": 0.3,
        "slow": 0.5,
        "instant": 0.05,
    }

    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_name = {
            executor.submit(fetch_sync, f"https://api/{name}", delay): name
            for name, delay in tasks.items()
        }

        for future in as_completed(future_to_name):
            name = future_to_name[future]
            result = future.result()
            print(f"  completed: {name} → {result}")


def submit_with_error_handling():
    """
    Futures capture exceptions — they don't raise until you call .result().
    This is useful when you want to process partial results even if some fail.
    """
    def maybe_fail(n: int) -> int:
        time.sleep(0.05)
        if n == 3:
            raise ValueError(f"item {n} is cursed")
        return n * 10

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(maybe_fail, i): i for i in range(6)}

        for future in as_completed(futures):
            item = futures[future]
            try:
                result = future.result()
                print(f"  item {item}: {result}")
            except ValueError as e:
                print(f"  item {item}: ERROR — {e}")


def callback_example():
    """
    Futures support add_done_callback(). The callback runs in the thread
    that completed the future (not the main thread) — watch for thread safety.
    """
    results = []
    lock = threading.Lock()

    def on_done(future):
        with lock:
            results.append(future.result())

    with ThreadPoolExecutor(max_workers=3) as executor:
        for i in range(5):
            f = executor.submit(process_item, i)
            f.add_done_callback(on_done)

    # Results arrive in arbitrary order
    print(f"  results (unordered): {sorted(results)}")


def main():
    print("=== executor.map() ===")
    t0 = time.perf_counter()
    results = map_example()
    elapsed = time.perf_counter() - t0
    for r in results:
        print(f"  {r}")
    print(f"  total: {elapsed:.2f}s\n")

    print("=== submit() + as_completed() ===")
    submit_as_completed()

    print("\n=== error handling with futures ===")
    submit_with_error_handling()

    print("\n=== done callbacks ===")
    callback_example()


if __name__ == "__main__":
    main()
