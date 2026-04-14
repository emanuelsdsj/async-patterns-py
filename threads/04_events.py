"""
Thread coordination — Event, Barrier, local()

Patterns for coordinating threads beyond just sharing data.

- Event:   "this happened" signal — one-time or repeated
- Barrier: "wait until everyone is ready" synchronization point
- local(): thread-local storage — each thread has its own copy
"""

import threading
import time
import random


def startup_gate():
    """
    Workers wait at a gate until the main thread signals them to start.
    Common pattern for batch jobs where setup must complete before processing.
    """
    gate = threading.Event()
    results = []
    lock = threading.Lock()

    def worker(wid: int):
        print(f"  worker-{wid} waiting at gate...")
        gate.wait()
        # All workers start processing simultaneously after gate.set()
        result = wid * 2
        with lock:
            results.append(result)
        print(f"  worker-{wid} done: {result}")

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(4)]
    for t in threads:
        t.start()

    time.sleep(0.1)
    print("  opening gate!")
    gate.set()

    for t in threads:
        t.join()

    return results


def shutdown_signal():
    """
    Event as a cancellation/stop signal. Workers check it periodically.
    Cleaner than a global flag because Event is thread-safe.
    """
    stop = threading.Event()
    processed = []
    lock = threading.Lock()

    def worker():
        count = 0
        while not stop.is_set():
            time.sleep(0.05)
            count += 1
            with lock:
                processed.append(count)

    t = threading.Thread(target=worker)
    t.start()

    time.sleep(0.3)
    stop.set()  # signal worker to stop
    t.join()

    print(f"  worker processed {len(processed)} items before shutdown")


def barrier_demo():
    """
    Barrier makes all threads wait until N have reached the barrier.
    The classic use case: parallel phases where each phase must complete
    fully before the next one starts.
    """
    NUM_THREADS = 4
    barrier = threading.Barrier(NUM_THREADS)
    phase_times = []
    lock = threading.Lock()

    def worker(wid: int):
        # Phase 1: independent work
        duration = random.uniform(0.05, 0.2)
        time.sleep(duration)
        print(f"  worker-{wid} done with phase 1 ({duration:.2f}s), waiting...")

        barrier.wait()  # wait for everyone to finish phase 1

        # Phase 2: starts only after ALL workers finished phase 1
        start = time.perf_counter()
        time.sleep(0.05)
        with lock:
            phase_times.append(time.perf_counter() - start)
        print(f"  worker-{wid} done with phase 2")

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(NUM_THREADS)]
    t0 = time.perf_counter()
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    print(f"  total time: {time.perf_counter() - t0:.2f}s")


def thread_local_demo():
    """
    threading.local() gives each thread its own namespace.
    Classic use: per-thread DB connections, per-request context in web servers.
    Threads don't see each other's data.
    """
    local_data = threading.local()

    def worker(wid: int):
        local_data.connection_id = f"conn-{wid}-{threading.get_ident()}"
        local_data.request_count = 0

        for _ in range(3):
            time.sleep(0.01)
            local_data.request_count += 1

        print(f"  worker-{wid}: {local_data.connection_id}, requests: {local_data.request_count}")

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Main thread has no local_data attributes set
    print(f"  main thread has connection_id: {hasattr(local_data, 'connection_id')}")


def main():
    print("=== startup gate (Event as start signal) ===")
    startup_gate()

    print("\n=== shutdown signal (Event as stop flag) ===")
    shutdown_signal()

    print("\n=== barrier (phase synchronization) ===")
    barrier_demo()

    print("\n=== thread-local storage ===")
    thread_local_demo()


if __name__ == "__main__":
    main()
