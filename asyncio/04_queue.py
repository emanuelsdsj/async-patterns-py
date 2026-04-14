"""
asyncio.Queue — producer/consumer with backpressure

Queue decouples producers from consumers. Producers push work items,
consumers pull and process them independently. The queue buffers between them.

The key parameter is maxsize:
- maxsize=0 (default): unbounded — producers never block, memory grows forever
- maxsize=N: producers block when full, providing natural backpressure

Use this when producers and consumers run at different speeds and you
don't want one side to overwhelm the other.
"""

import asyncio
import random
import time


async def basic_producer_consumer():
    """Single producer, single consumer."""
    queue: asyncio.Queue[str] = asyncio.Queue()

    async def producer():
        for i in range(5):
            item = f"item-{i}"
            await queue.put(item)
            print(f"  produced: {item}")
            await asyncio.sleep(0.05)
        await queue.put(None)  # sentinel to signal done

    async def consumer():
        while True:
            item = await queue.get()
            if item is None:
                break
            print(f"  consumed: {item}")
            await asyncio.sleep(0.1)  # slower than producer
            queue.task_done()

    await asyncio.gather(producer(), consumer())


async def multi_producer_consumer():
    """
    Multiple producers and consumers. Common in pipeline architectures.

    The trick with multiple consumers: use queue.join() + poison pills.
    Each consumer needs its own None to know when to stop.
    """
    NUM_PRODUCERS = 2
    NUM_CONSUMERS = 3
    queue: asyncio.Queue[str | None] = asyncio.Queue(maxsize=10)

    async def producer(pid: int):
        for i in range(4):
            item = f"p{pid}-item{i}"
            await queue.put(item)
            print(f"  [producer-{pid}] put {item} (queue size: {queue.qsize()})")
            await asyncio.sleep(random.uniform(0.02, 0.08))
        print(f"  [producer-{pid}] done")

    async def consumer(cid: int):
        while True:
            item = await queue.get()
            if item is None:
                queue.task_done()
                break
            print(f"  [consumer-{cid}] got {item}")
            await asyncio.sleep(random.uniform(0.05, 0.15))
            queue.task_done()
        print(f"  [consumer-{cid}] done")

    producers = [asyncio.create_task(producer(i)) for i in range(NUM_PRODUCERS)]
    consumers = [asyncio.create_task(consumer(i)) for i in range(NUM_CONSUMERS)]

    await asyncio.gather(*producers)

    # Send one poison pill per consumer
    for _ in range(NUM_CONSUMERS):
        await queue.put(None)

    await asyncio.gather(*consumers)
    await queue.join()


async def backpressure_demo():
    """
    maxsize creates backpressure: producer blocks when the queue is full.
    This prevents a fast producer from buffering infinite items in memory.
    """
    queue: asyncio.Queue[int] = asyncio.Queue(maxsize=3)

    async def fast_producer():
        for i in range(8):
            await queue.put(i)
            print(f"  produced {i} (queue: {queue.qsize()}/{queue.maxsize})")
        await queue.put(None)

    async def slow_consumer():
        while True:
            item = await queue.get()
            if item is None:
                break
            await asyncio.sleep(0.15)  # slow
            print(f"  consumed {item}")
            queue.task_done()

    await asyncio.gather(fast_producer(), slow_consumer())


async def main():
    print("=== basic producer/consumer ===")
    await basic_producer_consumer()

    print("\n=== multiple producers and consumers ===")
    await multi_producer_consumer()

    print("\n=== backpressure with maxsize=3 ===")
    await backpressure_demo()


if __name__ == "__main__":
    asyncio.run(main())
