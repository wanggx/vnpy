import pyobjdemo

data = list(range(1, 1_000_001))  # 100 万个 Python int（每个都是 PyObject）

print("sum_touch   ", pyobjdemo.sum_touch(data))     # 循环里一直碰 PyObject
print("sum_no_touch", pyobjdemo.sum_no_touch(data))  # 抽出 C 数组后再加
print("python sum  ", sum(data))
