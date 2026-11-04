#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <stdlib.h>

/*
 * 碰 PyObject：全程拿着 GIL，用 Python C API 读 list 里的整数。
 * PyList_GET_ITEM / PyLong_AsLongLong / PyLong_FromLongLong 都在碰对象。
 */
static PyObject *
sum_touch(PyObject *self, PyObject *args)
{
    PyObject *lst;
    Py_ssize_t i, n;
    long long s = 0;

    if (!PyArg_ParseTuple(args, "O", &lst)) {
        return NULL;
    }
    if (!PyList_Check(lst)) {
        PyErr_SetString(PyExc_TypeError, "need a list");
        return NULL;
    }

    n = PyList_GET_SIZE(lst);                 /* 碰：读 list 对象 */
    for (i = 0; i < n; i++) {
        PyObject *item = PyList_GET_ITEM(lst, i);  /* 碰：取出元素 PyObject* */
        s += PyLong_AsLongLong(item);              /* 碰：读 int 对象 */
        if (PyErr_Occurred()) {
            return NULL;
        }
    }
    return PyLong_FromLongLong(s);            /* 碰：新建一个 int 对象 */
}

/*
 * 不碰 PyObject：先在有 GIL 时把值拷进 C 数组，
 * 放锁后的循环只加 long long，最后再拿回 GIL 包装成 Python int。
 */
static PyObject *
sum_no_touch(PyObject *self, PyObject *args)
{
    PyObject *lst;
    Py_ssize_t i, n;
    long long *buf;
    long long s = 0;

    if (!PyArg_ParseTuple(args, "O", &lst)) {
        return NULL;
    }
    if (!PyList_Check(lst)) {
        PyErr_SetString(PyExc_TypeError, "need a list");
        return NULL;
    }

    n = PyList_GET_SIZE(lst);
    buf = (long long *)malloc(sizeof(long long) * (size_t)n);
    if (buf == NULL) {
        return PyErr_NoMemory();
    }

    for (i = 0; i < n; i++) {
        PyObject *item = PyList_GET_ITEM(lst, i);  /* 仍有 GIL，可以碰 */
        buf[i] = PyLong_AsLongLong(item);
        if (PyErr_Occurred()) {
            free(buf);
            return NULL;
        }
    }

    Py_BEGIN_ALLOW_THREADS                     /* 放下 GIL */
    for (i = 0; i < n; i++) {
        s += buf[i];                           /* 只碰 C 的 long long，不碰 PyObject */
    }
    Py_END_ALLOW_THREADS                       /* 拿回 GIL */

    free(buf);
    return PyLong_FromLongLong(s);             /* 又碰：给 Python 返回对象 */
}

/*
 * 反例（不要学、不要跑）：放锁之后还 PyList_GET_ITEM。
 * 此时别的线程可能改 list / 释放元素，轻则读到垃圾，重则崩溃。
 *
 * Py_BEGIN_ALLOW_THREADS
 * item = PyList_GET_ITEM(lst, i);   // 错误：没 GIL 还碰 PyObject
 * Py_END_ALLOW_THREADS
 */

static PyMethodDef Methods[] = {
    {"sum_touch",    sum_touch,    METH_VARARGS, "sum list, always touching PyObject"},
    {"sum_no_touch", sum_no_touch, METH_VARARGS, "copy out then sum without GIL"},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef module = {
    PyModuleDef_HEAD_INIT,
    "pyobjdemo",
    NULL,
    -1,
    Methods
};

PyMODINIT_FUNC
PyInit_pyobjdemo(void)
{
    return PyModule_Create(&module);
}
