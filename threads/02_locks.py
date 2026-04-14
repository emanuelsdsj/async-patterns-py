"""
Thread synchronization — Lock, RLock, Event, Condition

Threads share memory, which is convenient until two of them write to the same
variable at the same time. These primitives coordinate access.

Lock:   mutual exclusion — only one thread at a time
RLock:  reentrant lock — same thread can acquire multiple times
Event:  one-shot signal — "this thing happened"
Condition: Event + Lock — wait for a condition to become true
"""

import threading
import time
import random


# --- Lock ---

def lock_demo():
    """
    Without a lock, concurrent increments to a shared counter get lost
    due to race conditions (read-modify-write is not atomic).
    """
    counter = 0
    lock = threading.Lock()

    def increment_unsafe(n: int):
        nonlocal counter
        for _ in range(n):
            # Race condition: read → modify → write, not atomic
            counter += 1

    def increment_safe(n: int):
        nonlocal counter
        for _ in range(n):
            with lock:
                counter += 1

    # Unsafe version
    counter = 0
    threads = [threading.Thread(target=increment_unsafe, args=(1000,)) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    print(f"  unsafe counter (expected 5000): {counter}")

    # Safe version
    counter = 0
    threads = [threading.Thread(target=increment_safe, args=(1000,)) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    print(f"  safe counter   (expected 5000): {counter}")


# --- RLock ---

class BankAccount:
    """
    RLock allows a thread that already holds the lock to acquire it again.
    Useful in class methods that call other methods on the same instance.
    Without RLock, transfer() would deadlock calling deposit() and withdraw().
    """

    def __init__(self, balance: float):
        self.balance = balance
        self._lock = threading.RLock()  # reentrant

    def deposit(self, amount: float):
        with self._lock:
            self.balance += amount

    def withdraw(self, amount: float):
        with self._lock:
            if self.balance < amount:
                raise ValueError("insufficient funds")
            self.balance -= amount

    def transfer_to(self, other: "BankAccount", amount: float):
        with self._lock:          # acquire lock once...
            self.withdraw(amount) # ...withdraw() acquires again (OK with RLock)
            other.deposit(amount) # deposit() on other account acquires other's lock


def rlock_demo():
    # Large initial balances so we never hit zero during concurrent transfers
    acc_a = BankAccount(100_000.0)
    acc_b = BankAccount(100_000.0)
    total = acc_a.balance + acc_b.balance

    def do_transfers():
        for _ in range(50):
            acc_a.transfer_to(acc_b, 10.0)
            acc_b.transfer_to(acc_a, 10.0)

    threads = [threading.Thread(target=do_transfers) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    print(f"  acc_a: {acc_a.balance:.1f}, acc_b: {acc_b.balance:.1f}")
    print(f"  total preserved: {acc_a.balance + acc_b.balance:.1f} (expected {total:.1f})")


# --- Event ---

def event_demo():
    """
    Event signals that something happened. Threads can wait() for it.
    Good for "start signal" or "work is ready" scenarios.
    """
    ready = threading.Event()
    results = []

    def worker(worker_id: int):
        ready.wait()  # blocks until ready.set() is called
        result = worker_id * worker_id
        results.append(result)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
    for t in threads:
        t.start()

    time.sleep(0.05)
    print("  releasing all workers...")
    ready.set()  # all waiting threads wake up simultaneously

    for t in threads:
        t.join()
    print(f"  results: {sorted(results)}")


# --- Condition ---

def condition_demo():
    """
    Condition is an Event with a Lock built in. Use it when you need to
    wait for a specific state change, not just a one-time signal.
    Classic pattern: producer notifies consumers when data is available.
    """
    condition = threading.Condition()
    buffer = []
    MAX_BUFFER = 3

    def producer():
        for i in range(7):
            with condition:
                while len(buffer) >= MAX_BUFFER:
                    condition.wait()  # wait for space
                buffer.append(i)
                print(f"  produced {i}, buffer: {buffer}")
                condition.notify_all()
            time.sleep(0.02)

    def consumer(cid: int):
        consumed = 0
        while consumed < 3:
            with condition:
                while not buffer:
                    condition.wait()  # wait for items
                item = buffer.pop(0)
                consumed += 1
                print(f"  consumer-{cid} got {item}, buffer: {buffer}")
                condition.notify_all()
            time.sleep(0.04)

    threads = [
        threading.Thread(target=producer),
        threading.Thread(target=consumer, args=(0,)),
        threading.Thread(target=consumer, args=(1,)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()


def main():
    print("=== Lock — race condition vs safe counter ===")
    lock_demo()

    print("\n=== RLock — reentrant locking in BankAccount ===")
    rlock_demo()

    print("\n=== Event — start signal ===")
    event_demo()

    print("\n=== Condition — producer/consumer with state ===")
    condition_demo()


if __name__ == "__main__":
    main()
