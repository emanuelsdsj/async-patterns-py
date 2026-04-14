"""
multiprocessing.shared_memory — zero-copy between processes

Normally, passing data between processes requires pickling (serialization).
For large arrays (think: image frames, sensor data, ML feature matrices),
that serialization cost is prohibitive.

shared_memory allocates a named memory block that multiple processes can
attach to directly — no copying. Workers read and write to the same bytes.

Introduced in Python 3.8. If you're doing anything with numpy arrays
across processes, this is worth knowing.

Note: shared memory has no built-in synchronization. You need to coordinate
access yourself (e.g., don't have two processes write to the same region).
"""

import struct
import time
from multiprocessing import Process, shared_memory
from multiprocessing.managers import SharedMemoryManager


# --- Basic shared memory usage ---

def writer_process(shm_name: str, size: int):
    """Attaches to existing shared memory and writes integers into it."""
    shm = shared_memory.SharedMemory(name=shm_name)
    for i in range(size):
        # Pack int into 4 bytes at position i*4
        struct.pack_into("i", shm.buf, i * 4, i * 100)
    shm.close()


def reader_process(shm_name: str, size: int, result_shm_name: str):
    """Reads from shared memory, computes sum, writes result back."""
    shm = shared_memory.SharedMemory(name=shm_name)
    result_shm = shared_memory.SharedMemory(name=result_shm_name)

    total = 0
    for i in range(size):
        value = struct.unpack_from("i", shm.buf, i * 4)[0]
        total += value

    struct.pack_into("q", result_shm.buf, 0, total)  # 'q' = 8-byte int
    shm.close()
    result_shm.close()


def basic_shared_memory():
    SIZE = 10
    # Each int is 4 bytes
    shm = shared_memory.SharedMemory(create=True, size=SIZE * 4)
    result_shm = shared_memory.SharedMemory(create=True, size=8)

    try:
        writer = Process(target=writer_process, args=(shm.name, SIZE))
        writer.start()
        writer.join()

        reader = Process(target=reader_process, args=(shm.name, SIZE, result_shm.name))
        reader.start()
        reader.join()

        total = struct.unpack_from("q", result_shm.buf, 0)[0]
        expected = sum(i * 100 for i in range(SIZE))
        print(f"  sum: {total} (expected {expected})")
    finally:
        shm.close()
        shm.unlink()
        result_shm.close()
        result_shm.unlink()


# --- SharedMemoryManager for higher-level usage ---

def process_chunk(shm_name: str, start: int, end: int, result_shm_name: str, result_offset: int):
    """Process a chunk of a shared array and write the partial sum."""
    shm = shared_memory.SharedMemory(name=shm_name)
    result_shm = shared_memory.SharedMemory(name=result_shm_name)

    partial_sum = 0
    for i in range(start, end):
        val = struct.unpack_from("i", shm.buf, i * 4)[0]
        partial_sum += val

    struct.pack_into("q", result_shm.buf, result_offset * 8, partial_sum)
    shm.close()
    result_shm.close()


def parallel_sum_with_shared_memory():
    """
    Classic pattern: shared read-only input, each worker writes to
    a non-overlapping region of a shared results buffer.
    No locks needed because writes don't overlap.
    """
    SIZE = 1000
    NUM_WORKERS = 4
    CHUNK = SIZE // NUM_WORKERS

    # Create and populate input array
    input_shm = shared_memory.SharedMemory(create=True, size=SIZE * 4)
    for i in range(SIZE):
        struct.pack_into("i", input_shm.buf, i * 4, i + 1)

    # Result buffer: one int64 per worker
    result_shm = shared_memory.SharedMemory(create=True, size=NUM_WORKERS * 8)

    try:
        workers = [
            Process(
                target=process_chunk,
                args=(input_shm.name, i * CHUNK, (i + 1) * CHUNK, result_shm.name, i)
            )
            for i in range(NUM_WORKERS)
        ]

        for w in workers:
            w.start()
        for w in workers:
            w.join()

        total = sum(
            struct.unpack_from("q", result_shm.buf, i * 8)[0]
            for i in range(NUM_WORKERS)
        )
        expected = SIZE * (SIZE + 1) // 2
        print(f"  parallel sum 1..{SIZE}: {total} (expected {expected})")
    finally:
        input_shm.close()
        input_shm.unlink()
        result_shm.close()
        result_shm.unlink()


def main():
    print("=== basic shared memory (write + read across processes) ===")
    basic_shared_memory()

    print("\n=== parallel sum with shared memory (no pickling) ===")
    t0 = time.perf_counter()
    parallel_sum_with_shared_memory()
    print(f"  elapsed: {time.perf_counter() - t0:.3f}s")


if __name__ == "__main__":
    main()
