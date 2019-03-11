from setuptools import setup


setup(
    name='karst',
    packages=[
        "karst"
    ],
    install_requires=[
        "hwtypes",
        "astor",
        "z3-solver",
    ],
)
