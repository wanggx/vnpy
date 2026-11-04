from setuptools import Extension, setup

setup(
    name="pyobjdemo",
    ext_modules=[
        Extension("pyobjdemo", ["pyobj_demo.c"]),
    ],
)
