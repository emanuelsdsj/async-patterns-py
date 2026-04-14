"""
asyncio.Semaphore — limiting concurrency

The classic "max N concurrent connections" pattern. Without a semaphore,
gather() with 1000 tasks spawns 1000 concurrent connections — which will
get you rate-limited, OOM'd, or both.

A semaphore is a counter. acquire() decrements it (blocks at 0),
release() increments it. Wrapping tasks with it ensures at most N
run at the same time.
"""

import asyncio
import time


async def fetch(session_id: int, url: str, delay: float) -> str:
    await asyncio.sleep(delay)
    return f"[session {session_id}] {url}"


async def without_semaphore(urls: list[str]):
    """All 20 tasks fire at the same time. Fine for 20, catastrophic for 10000."""
    tasks = [fetch(i, url, 0.2) for i, url in enumerate(urls)]
    return await asyncio.gather(*tasks)


async def with_semaphore(urls: list[str], max_concurrent: int = 5):
    """At most max_concurrent tasks run at the same time."""
    sem = asyncio.Semaphore(max_concurrent)

    async def bounded_fetch(session_id: int, url: str) -> str:
        async with sem:
            # Only max_concurrent coroutines can be inside here simultaneously
            return await fetch(session_id, url, 0.2)

    tasks = [bounded_fetch(i, url) for i, url in enumerate(urls)]
    return await asyncio.gather(*tasks)


async def connection_pool_simulation():
    """
    Simulates a database connection pool with max 3 connections.
    Shows how semaphore gates access to a limited resource.
    """
    MAX_CONNECTIONS = 3
    sem = asyncio.Semaphore(MAX_CONNECTIONS)
    active = 0

    async def query(query_id: int, duration: float) -> str:
        nonlocal active
        async with sem:
            active += 1
            print(f"  query-{query_id} started  (active connections: {active})")
            await asyncio.sleep(duration)
            active -= 1
            print(f"  query-{query_id} finished (active connections: {active})")
            return f"result-{query_id}"

    queries = [(i, 0.1 + (i % 3) * 0.05) for i in range(8)]
    results = await asyncio.gather(*[query(qid, dur) for qid, dur in queries])
    return results


async def main():
    urls = [f"https://api.example.com/item/{i}" for i in range(20)]

    print("=== without semaphore (20 concurrent) ===")
    t0 = time.perf_counter()
    await without_semaphore(urls)
    print(f"  total: {time.perf_counter() - t0:.2f}s\n")

    print("=== with semaphore (max 5 concurrent) ===")
    t0 = time.perf_counter()
    await with_semaphore(urls, max_concurrent=5)
    print(f"  total: {time.perf_counter() - t0:.2f}s\n")

    print("=== connection pool (max 3 connections) ===")
    await connection_pool_simulation()


if __name__ == "__main__":
    asyncio.run(main())
