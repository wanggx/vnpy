/*
 * 纯 C 计算库：串行求和 vs Windows 多线程求和。
 * 编译成 DLL 后，由 Python ctypes 加载。
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>

#ifdef __cplusplus
extern "C" {
#endif

__declspec(dllexport) long long serial_sum(long long n);
__declspec(dllexport) long long parallel_sum(long long n, int nthreads);
__declspec(dllexport) int last_worker_tids(int *out, int maxn);
__declspec(dllexport) int last_nthreads(void);

#ifdef __cplusplus
}
#endif

typedef struct {
    long long start;   /* inclusive */
    long long end;     /* exclusive */
    long long result;
    DWORD tid;
} Task;

static int g_nthreads = 0;
static DWORD g_tids[64];

/* 加点运算并写入 volatile，避免编译器把求和直接优化成 n*(n+1)/2 */
static long long accumulate(long long start, long long end)
{
    volatile long long s = 0;
    long long i;
    for (i = start; i < end; i++) {
        s += i;
    }
    return s;
}

static DWORD WINAPI worker(LPVOID p)
{
    Task *t = (Task *)p;
    t->tid = GetCurrentThreadId();
    t->result = accumulate(t->start, t->end);
    return 0;
}

long long serial_sum(long long n)
{
    return accumulate(1, n + 1);
}

long long parallel_sum(long long n, int nthreads)
{
    HANDLE threads[64];
    Task tasks[64];
    long long chunk;
    long long total = 0;
    int i;
    SYSTEM_INFO info;

    if (n < 0) {
        n = 0;
    }
    if (nthreads <= 0) {
        GetSystemInfo(&info);
        nthreads = (int)info.dwNumberOfProcessors;
    }
    if (nthreads < 1) {
        nthreads = 1;
    }
    if (nthreads > 64) {
        nthreads = 64;
    }

    chunk = n / nthreads;
    if (chunk < 1) {
        nthreads = 1;
        chunk = n;
    }

    for (i = 0; i < nthreads; i++) {
        tasks[i].start = (long long)i * chunk + 1;
        tasks[i].end = (i == nthreads - 1)
            ? (n + 1)
            : ((long long)(i + 1) * chunk + 1);
        tasks[i].result = 0;
        tasks[i].tid = 0;
        threads[i] = CreateThread(NULL, 0, worker, &tasks[i], 0, NULL);
    }

    WaitForMultipleObjects((DWORD)nthreads, threads, TRUE, INFINITE);

    g_nthreads = nthreads;
    for (i = 0; i < nthreads; i++) {
        total += tasks[i].result;
        g_tids[i] = tasks[i].tid;
        CloseHandle(threads[i]);
    }
    return total;
}

int last_worker_tids(int *out, int maxn)
{
    int n = g_nthreads;
    int i;
    if (maxn < n) {
        n = maxn;
    }
    for (i = 0; i < n; i++) {
        out[i] = (int)g_tids[i];
    }
    return n;
}

int last_nthreads(void)
{
    return g_nthreads;
}
