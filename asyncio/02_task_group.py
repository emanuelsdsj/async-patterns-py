"""
asyncio.TaskGroup — structured concurrency (Python 3.11+)

TaskGroup is what you should use instead of gather() when correctness
matters more than convenience. The key difference:

- gather(): tasks are fire-and-forget, errors can leave orphaned tasks
- TaskGroup: if any task fails, ALL others are cancelled. No orphans.

This is the "structured concurrency" idea from Trio, now in stdlib.
Think of it like a context manager for tasks: everything that enters
must exit, no task outlives its group.
"""

import asyncio
import time


async def fetch(name: str, delay: float, should_fail: bool = False) -> str:
    try:
        await asyncio.sleep(delay)
        if should_fail:
            raise RuntimeError(f"{name} encountered an error")
        return f"{name} done"
    except asyncio.CancelledError:
        # This runs when the group cancels us due to another task failing
        print(f"  {name} was cancelled")
        raise


async def basic_task_group():
    """All tasks complete successfully."""
    async with asyncio.TaskGroup() as tg:
        t1 = tg.create_task(fetch("users", 0.3))
        t2 = tg.create_task(fetch("posts", 0.2))
        t3 = tg.create_task(fetch("tags", 0.1))
    # By here, all tasks are done — no need to await them separately
    return [t1.result(), t2.result(), t3.result()]


async def task_group_with_failure():
    """
    When one task fails, the group cancels the others.
    The exception is re-raised as ExceptionGroup.
    """
    print("  Starting tasks — task-2 will fail after 0.1s")
    try:
        async with asyncio.TaskGroup() as tg:
            t1 = tg.create_task(fetch("task-1", 0.5))        # will be cancelled
            t2 = tg.create_task(fetch("task-2", 0.1, True))  # fails
            t3 = tg.create_task(fetch("task-3", 0.3))        # will be cancelled
    except* RuntimeError as eg:
        # except* handles ExceptionGroup — Python 3.11+ syntax
        for exc in eg.exceptions:
            print(f"  caught: {exc}")


async def task_group_collect_results():
    """
    Pattern for collecting results from a task group.
    Since tg.create_task() returns a Task, store them and read .result() after.
    """
    tasks = {}

    async with asyncio.TaskGroup() as tg:
        for name, delay in [("alpha", 0.1), ("beta", 0.2), ("gamma", 0.15)]:
            tasks[name] = tg.create_task(fetch(name, delay))

    return {name: task.result() for name, task in tasks.items()}


async def main():
    print("=== basic task group ===")
    t0 = time.perf_counter()
    results = await basic_task_group()
    elapsed = time.perf_counter() - t0
    for r in results:
        print(f"  {r}")
    print(f"  total: {elapsed:.2f}s\n")

    print("=== task group with failure (structured cancellation) ===")
    await task_group_with_failure()

    print("\n=== collecting results ===")
    results = await task_group_collect_results()
    for name, result in results.items():
        print(f"  {name}: {result}")


if __name__ == "__main__":
    asyncio.run(main())
