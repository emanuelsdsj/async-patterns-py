"""
asyncio timeouts and cancellation

Two ways to set deadlines in asyncio:
- asyncio.wait_for(coro, timeout): wraps a single coroutine
- asyncio.timeout(seconds): context manager, works for any block (Python 3.11+)

Cancellation is cooperative: CancelledError is injected at the next await.
Code that catches it must re-raise (or the cancellation is silently swallowed).
"""

import asyncio
import time


async def slow_operation(name: str, duration: float) -> str:
    try:
        print(f"  {name}: started, will take {duration}s")
        await asyncio.sleep(duration)
        print(f"  {name}: completed")
        return f"{name} result"
    except asyncio.CancelledError:
        print(f"  {name}: cancelled — running cleanup")
        # Do cleanup here (close connections, release resources, etc.)
        raise  # must re-raise so the cancellation propagates


async def wait_for_demo():
    """asyncio.wait_for — simple single-coroutine timeout."""

    # Success case
    try:
        result = await asyncio.wait_for(slow_operation("fast-op", 0.1), timeout=1.0)
        print(f"  result: {result}")
    except asyncio.TimeoutError:
        print("  timed out")

    # Timeout case
    try:
        result = await asyncio.wait_for(slow_operation("slow-op", 2.0), timeout=0.3)
        print(f"  result: {result}")
    except asyncio.TimeoutError:
        print("  slow-op timed out after 0.3s")


async def timeout_context_manager():
    """
    asyncio.timeout() — Python 3.11+. More flexible than wait_for because
    it can wrap any block of code, not just a single coroutine.
    """
    try:
        async with asyncio.timeout(0.5):
            await slow_operation("op-a", 0.2)
            await slow_operation("op-b", 0.2)  # this one gets cancelled
            await slow_operation("op-c", 0.2)  # never reached
    except asyncio.TimeoutError:
        print("  block timed out — op-b or op-c didn't finish")


async def timeout_reschedule():
    """
    asyncio.timeout() lets you check and reschedule the deadline.
    Useful for operations where you want to extend time based on progress.
    """
    deadline = asyncio.get_event_loop().time() + 0.4

    try:
        async with asyncio.timeout_at(deadline) as cm:
            await asyncio.sleep(0.2)
            print(f"  checkpoint reached, extending deadline")
            cm.reschedule(asyncio.get_event_loop().time() + 0.4)  # extend
            await asyncio.sleep(0.3)
            print("  completed after extension")
    except asyncio.TimeoutError:
        print("  timed out even after extension")


async def cancel_task_manually():
    """
    Cancelling a task directly. This is how you implement things like
    "cancel all pending tasks on shutdown".
    """
    task = asyncio.create_task(slow_operation("background-task", 5.0))

    await asyncio.sleep(0.2)
    print("  cancelling task...")
    task.cancel()

    try:
        await task
    except asyncio.CancelledError:
        print("  task was cancelled cleanly")


async def main():
    print("=== asyncio.wait_for ===")
    await wait_for_demo()

    print("\n=== asyncio.timeout (context manager) ===")
    await timeout_context_manager()

    print("\n=== rescheduling deadline ===")
    await timeout_reschedule()

    print("\n=== manual task cancellation ===")
    await cancel_task_manually()


if __name__ == "__main__":
    asyncio.run(main())
