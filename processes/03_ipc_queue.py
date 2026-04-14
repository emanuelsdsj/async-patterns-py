"""
Inter-process communication — Queue, Pipe, Manager

Three ways to pass data between processes:

Queue:   safe for multiple producers and consumers, based on a pipe + locks
Pipe:    faster but only for two endpoints (one reader, one writer)
Manager: shared Python objects (list, dict) via a proxy — convenient but slow

When to use which:
- Queue:   when you have multiple workers feeding results back
- Pipe:    when you have exactly two processes talking to each other
- Manager: when you need shared mutable state and convenience matters more than speed
"""

import time
from multiprocessing import Process, Queue, Pipe, Manager
import hashlib


def cpu_work(data: str) -> str:
    result = data.encode()
    for _ in range(50_000):
        result = hashlib.sha256(result).digest()
    return result.hex()[:8]


# --- Queue ---

def worker_with_queue(input_q: Queue, output_q: Queue):
    while True:
        item = input_q.get()
        if item is None:
            break
        result = cpu_work(item)
        output_q.put((item, result))


def queue_example():
    """Fan-out with queue: dispatch tasks to workers, collect results."""
    NUM_WORKERS = 3
    input_q: Queue = Queue()
    output_q: Queue = Queue()

    workers = [
        Process(target=worker_with_queue, args=(input_q, output_q))
        for _ in range(NUM_WORKERS)
    ]
    for w in workers:
        w.start()

    items = [f"item-{i}" for i in range(9)]
    for item in items:
        input_q.put(item)

    # Poison pills
    for _ in range(NUM_WORKERS):
        input_q.put(None)

    results = {}
    for _ in range(len(items)):
        key, value = output_q.get()
        results[key] = value

    for w in workers:
        w.join()

    return results


# --- Pipe ---

def pipe_worker(conn):
    """Receives items, processes them, sends results back."""
    while True:
        item = conn.recv()
        if item is None:
            break
        result = cpu_work(item)
        conn.send(result)
    conn.close()


def pipe_example():
    """
    Pipe creates two Connection objects: parent_conn and child_conn.
    duplex=True (default): both ends can send and receive.
    duplex=False: one-directional (child can only recv, parent can only send).
    """
    parent_conn, child_conn = Pipe()

    worker = Process(target=pipe_worker, args=(child_conn,))
    worker.start()

    items = [f"data-{i}" for i in range(5)]
    results = {}

    for item in items:
        parent_conn.send(item)
        result = parent_conn.recv()
        results[item] = result

    parent_conn.send(None)  # signal done
    worker.join()
    parent_conn.close()

    return results


# --- Manager ---

def manager_worker(shared_dict: dict, shared_list: list, key: str, value: str):
    """Writes directly to shared Manager objects."""
    result = cpu_work(value)
    shared_dict[key] = result
    shared_list.append(key)


def manager_example():
    """
    Manager objects look like normal Python dicts/lists but live in
    a separate process and are accessed via proxies. Convenient but
    each read/write is an IPC call — don't use for hot paths.
    """
    with Manager() as manager:
        shared_dict = manager.dict()
        shared_list = manager.list()

        workers = [
            Process(
                target=manager_worker,
                args=(shared_dict, shared_list, f"key-{i}", f"value-{i}")
            )
            for i in range(5)
        ]
        for w in workers:
            w.start()
        for w in workers:
            w.join()

        return dict(shared_dict), list(shared_list)


def main():
    print("=== Queue — fan-out with multiple workers ===")
    t0 = time.perf_counter()
    results = queue_example()
    elapsed = time.perf_counter() - t0
    for key, value in sorted(results.items()):
        print(f"  {key}: {value}")
    print(f"  total: {elapsed:.2f}s\n")

    print("=== Pipe — two-process communication ===")
    t0 = time.perf_counter()
    results = pipe_example()
    elapsed = time.perf_counter() - t0
    for key, value in sorted(results.items()):
        print(f"  {key}: {value}")
    print(f"  total: {elapsed:.2f}s\n")

    print("=== Manager — shared dict and list ===")
    result_dict, result_list = manager_example()
    print(f"  dict keys: {sorted(result_dict.keys())}")
    print(f"  list: {sorted(result_list)}")


if __name__ == "__main__":
    main()
