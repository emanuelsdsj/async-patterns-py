"""
asyncio.gather — fan-out parallel execution

The most common asyncio pattern. You have N independent tasks and want
to run them all at the same time instead of one after another.

gather() vs create_task():
- gather() is convenient but all tasks run in the same scope
- if one raises, the others keep running (unless return_exceptions=False)
- use TaskGroup (02_task_group.py) when you want structured cancellation
"""

import asyncio
import time


async def fetch(url: str, delay: float) -> str:
    """Simulates an HTTP request with variable latency."""
    await asyncio.sleep(delay)
    return f"response from {url} ({delay}s)"


async def sequential():
    """The naive approach — wait for each one before starting the next."""
    urls = [
        ("https://api.example.com/users", 0.3),
        ("https://api.example.com/posts", 0.5),
        ("https://api.example.com/comments", 0.2),
    ]
    results = []
    for url, delay in urls:
        result = await fetch(url, delay)
        results.append(result)
    return results


async def parallel():
    """gather() runs all coroutines concurrently — total time is max(delays), not sum."""
    results = await asyncio.gather(
        fetch("https://api.example.com/users", 0.3),
        fetch("https://api.example.com/posts", 0.5),
        fetch("https://api.example.com/comments", 0.2),
    )
    return results


async def parallel_with_errors():
    """
    return_exceptions=True prevents a single failure from cancelling everything.
    Without it, if one task raises, gather() immediately propagates the exception
    and the other tasks are abandoned (but not cancelled — they keep running orphaned).
    """
    async def maybe_fail(name: str, should_fail: bool):
        await asyncio.sleep(0.1)
        if should_fail:
            raise ValueError(f"{name} failed")
        return f"{name} ok"

    results = await asyncio.gather(
        maybe_fail("task-1", False),
        maybe_fail("task-2", True),   # this one fails
        maybe_fail("task-3", False),
        return_exceptions=True,        # don't cancel others on failure
    )

    for i, r in enumerate(results):
        if isinstance(r, Exception):
            print(f"  task-{i+1}: ERROR — {r}")
        else:
            print(f"  task-{i+1}: {r}")


async def dynamic_gather():
    """Building the task list dynamically — common when you don't know N upfront."""
    items = ["item-a", "item-b", "item-c", "item-d", "item-e"]

    async def process(item: str) -> str:
        await asyncio.sleep(0.1)
        return f"processed {item}"

    results = await asyncio.gather(*[process(item) for item in items])
    return results


async def main():
    print("=== sequential ===")
    t0 = time.perf_counter()
    results = await sequential()
    elapsed = time.perf_counter() - t0
    for r in results:
        print(f"  {r}")
    print(f"  total: {elapsed:.2f}s\n")

    print("=== parallel (gather) ===")
    t0 = time.perf_counter()
    results = await parallel()
    elapsed = time.perf_counter() - t0
    for r in results:
        print(f"  {r}")
    print(f"  total: {elapsed:.2f}s\n")

    print("=== gather with errors (return_exceptions=True) ===")
    await parallel_with_errors()

    print("\n=== dynamic gather ===")
    results = await dynamic_gather()
    for r in results:
        print(f"  {r}")


if __name__ == "__main__":
    asyncio.run(main())
