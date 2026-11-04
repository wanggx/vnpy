"""Python 调 C：对比纯 Python / C 单线程 / C 多线程。"""
from __future__ import annotations

import os
import threading
import time

from cwork import last_worker_tids, parallel_sum, serial_sum


def python_sum(n: int) -> int:
    s = 0
    for i in range(1, n + 1):
        s += i
    return s


def timed(label: str, fn):
    t0 = time.perf_counter()
    result = fn()
    dt = time.perf_counter() - t0
    print(f"{label:<28} result={result}  {dt:.3f}s")
    return result, dt


def main():
    n = 400_000_000
    print(f"sum 1..{n:,}")
    print(f"Python 进程 PID={os.getpid()}  主线程 ident={threading.get_ident()}\n")

    # 纯 Python 循环只跑小一点的 N，否则太慢
    n_py = 8_000_000
    timed("Python for-loop", lambda: python_sum(n_py))
    print(f"  (Python 只用了 n={n_py:,}，C 下面用全量 n)\n")

    timed("C serial_sum  (1 thread)", lambda: serial_sum(n))
    timed("C parallel_sum (N cores)", lambda: parallel_sum(n, 0))

    tids = last_worker_tids()
    print(f"\nC 工作线程 TID: {tids}")
    print(f"互不相同的 TID 个数: {len(set(tids))}  → 这是真正的 OS 多线程/可多核")

    formula = n * (n + 1) // 2
    print(f"\n公式核对 n*(n+1)/2 = {formula}")


if __name__ == "__main__":
    main()
