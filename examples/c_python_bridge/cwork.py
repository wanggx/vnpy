"""把 C DLL 包装成普通 Python API。"""
from __future__ import annotations

import os
from ctypes import POINTER, c_int, c_longlong, cdll

_DIR = os.path.dirname(os.path.abspath(__file__))
_DLL = os.path.join(_DIR, "work.dll")

if not os.path.exists(_DLL):
    raise FileNotFoundError(f"找不到 {_DLL}，请先运行 build.bat")

_lib = cdll.LoadLibrary(_DLL)
_lib.serial_sum.argtypes = [c_longlong]
_lib.serial_sum.restype = c_longlong
_lib.parallel_sum.argtypes = [c_longlong, c_int]
_lib.parallel_sum.restype = c_longlong
_lib.last_nthreads.argtypes = []
_lib.last_nthreads.restype = c_int
_lib.last_worker_tids.argtypes = [POINTER(c_int), c_int]
_lib.last_worker_tids.restype = c_int


def serial_sum(n: int) -> int:
    """C 单线程：1 + 2 + ... + n"""
    return int(_lib.serial_sum(n))


def parallel_sum(n: int, nthreads: int = 0) -> int:
    """C 多线程：把区间切开，每条 OS 线程算一段。nthreads=0 表示用 CPU 核数。"""
    return int(_lib.parallel_sum(n, nthreads))


def last_worker_tids() -> list[int]:
    buf = (c_int * 64)()
    n = _lib.last_worker_tids(buf, 64)
    return list(buf[:n])
