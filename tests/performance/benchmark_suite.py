import time
import asyncio
import sqlite3
import json
from core.ai_context import ContextBuilder
from core.builders.token_optimizer import TokenOptimizer, ModelCapabilities
from core.background_queue import BackgroundQueue
from pathlib import Path
import os

# --- 1. SQLite WAL vs Non-WAL ---
def run_sqlite_benchmark(db_path, wal_mode=False, iterations=1000):
    if os.path.exists(db_path):
        os.remove(db_path)
    
    conn = sqlite3.connect(db_path)
    if wal_mode:
        conn.execute("PRAGMA journal_mode=WAL")
    
    conn.execute("CREATE TABLE test_bench (id INTEGER PRIMARY KEY, data TEXT)")
    
    start_time = time.time()
    for i in range(iterations):
        conn.execute("INSERT INTO test_bench (data) VALUES (?)", (f"data_{i}",))
    conn.commit()
    write_time = time.time() - start_time
    
    start_time = time.time()
    c = conn.cursor()
    c.execute("SELECT * FROM test_bench")
    c.fetchall()
    read_time = time.time() - start_time
    
    conn.close()
    return write_time, read_time

# --- 2. Memory Metrics ---
def run_memory_metrics_benchmark():
    optimizer = TokenOptimizer()
    resolved_context = {
        "device_state": {f"dev_{i}": {"state": "off"} for i in range(100)},
        "summary": "This is a summary of the house.",
        "working_memory": [{"role": "user", "content": "Bật đèn"} for _ in range(10)]
    }
    
    start_time = time.time()
    for _ in range(100):
        optimizer.optimize(resolved_context)
    opt_time = (time.time() - start_time) / 100
    return opt_time

# --- 3. Queue Load Test ---
async def run_queue_benchmark(msg_per_sec=100, duration_sec=2):
    class MockQueue(BackgroundQueue):
        def __init__(self):
            self.processed = 0
            self.q = asyncio.Queue()
        async def enqueue(self, task):
            await self.q.put(task)
        async def worker(self):
            while True:
                task = await self.q.get()
                self.processed += 1
                self.q.task_done()
    
    queue = MockQueue()
    worker_task = asyncio.create_task(queue.worker())
    
    total_msgs = msg_per_sec * duration_sec
    start_time = time.time()
    for _ in range(total_msgs):
        await queue.enqueue({"type": "test"})
    
    await queue.q.join()
    elapsed = time.time() - start_time
    worker_task.cancel()
    return elapsed, total_msgs

if __name__ == "__main__":
    print("--- Sprint 10.5 Phase B Benchmark Suite ---")
    
    # 1. SQLite
    w_std, r_std = run_sqlite_benchmark("bench_std.db", wal_mode=False)
    w_wal, r_wal = run_sqlite_benchmark("bench_wal.db", wal_mode=True)
    print(f"SQLite Standard (1000 inserts) - Write: {w_std:.4f}s, Read: {r_std:.4f}s")
    print(f"SQLite WAL      (1000 inserts) - Write: {w_wal:.4f}s, Read: {r_wal:.4f}s")
    
    # 2. Token Optimizer
    opt_ms = run_memory_metrics_benchmark() * 1000
    print(f"TokenOptimizer Latency: {opt_ms:.4f} ms per call")
    
    # 3. Queue
    elapsed, msgs = asyncio.run(run_queue_benchmark(100, 2))
    print(f"Background Queue: Processed {msgs} messages in {elapsed:.4f}s (Rate: {msgs/elapsed:.2f} msg/s)")
