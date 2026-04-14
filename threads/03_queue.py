"""
queue.Queue — thread-safe message passing

Queue is the preferred way to communicate between threads. It handles
all the locking internally, so you don't have to think about it.

Three flavors:
- Queue:      FIFO (most common)
- LifoQueue:  LIFO / stack
- PriorityQueue: heap-based, smallest item first

queue.join() blocks until all items have been processed (task_done() called
for each). Useful for "wait until all work is done" patterns.
"""

import queue
import threading
import time
import random


def basic_queue():
    """Classic producer/consumer with queue.join() for completion tracking."""
    q: queue.Queue[int | None] = queue.Queue()

    def producer():
        for i in range(8):
            q.put(i)
            print(f"  produced {i}")
            time.sleep(0.02)
        q.put(None)  # sentinel

    def consumer():
        while True:
            item = q.get()
            if item is None:
                q.task_done()
                break
            time.sleep(0.06)
            print(f"  consumed {item}")
            q.task_done()

    t_prod = threading.Thread(target=producer)
    t_cons = threading.Thread(target=consumer)

    t_prod.start()
    t_cons.start()
    q.join()  # wait until all items are processed

    t_prod.join()
    t_cons.join()


def worker_pool():
    """
    Fixed pool of workers pulling from a shared queue.
    Each worker runs until it gets the sentinel (None).
    One sentinel per worker needed.
    """
    NUM_WORKERS = 3
    q: queue.Queue[tuple[int, float] | None] = queue.Queue()
    results = []
    results_lock = threading.Lock()

    def worker(wid: int):
        while True:
            item = q.get()
            if item is None:
                q.task_done()
                return
            task_id, duration = item
            time.sleep(duration)
            with results_lock:
                results.append((wid, task_id))
            print(f"  worker-{wid} finished task-{task_id}")
            q.task_done()

    workers = [threading.Thread(target=worker, args=(i,)) for i in range(NUM_WORKERS)]
    for w in workers:
        w.start()

    # Submit 10 tasks
    for i in range(10):
        q.put((i, random.uniform(0.05, 0.15)))

    # Send one sentinel per worker
    for _ in range(NUM_WORKERS):
        q.put(None)

    q.join()
    for w in workers:
        w.join()

    return results


def priority_queue_demo():
    """
    PriorityQueue processes smallest item first.
    Useful for task scheduling where some tasks are more urgent.
    Tuples compare element by element: (priority, task_id, data)
    """
    pq: queue.PriorityQueue[tuple[int, int, str]] = queue.PriorityQueue()

    # Add items with different priorities (lower = higher priority)
    tasks = [
        (3, 0, "low priority task"),
        (1, 1, "urgent task"),
        (2, 2, "medium task"),
        (1, 3, "also urgent"),
        (3, 4, "another low priority"),
    ]
    for task in tasks:
        pq.put(task)

    print("  processing order:")
    while not pq.empty():
        priority, task_id, description = pq.get()
        print(f"  [{priority}] task-{task_id}: {description}")


def queue_with_timeout():
    """
    put(block=True, timeout=N) and get(block=True, timeout=N) raise
    queue.Full / queue.Empty if they can't complete in time.
    Useful for bounded queues where you want to handle backpressure explicitly.
    """
    q: queue.Queue[int] = queue.Queue(maxsize=3)

    # Fill the queue
    for i in range(3):
        q.put(i)

    # Try to add one more — will fail
    try:
        q.put(99, timeout=0.1)
    except queue.Full:
        print(f"  queue is full ({q.qsize()}/{q.maxsize}), rejected item 99")

    # Drain it
    while not q.empty():
        print(f"  got: {q.get_nowait()}")

    # Try to get from empty queue
    try:
        q.get(timeout=0.1)
    except queue.Empty:
        print("  queue is empty, nothing to get")


def main():
    print("=== basic producer/consumer with queue.join() ===")
    basic_queue()

    print("\n=== worker pool ===")
    results = worker_pool()
    print(f"  processed {len(results)} tasks")

    print("\n=== priority queue ===")
    priority_queue_demo()

    print("\n=== queue with timeout ===")
    queue_with_timeout()


if __name__ == "__main__":
    main()
