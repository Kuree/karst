from setuptools import setup


setup(
    name='karst',
    packages=[
        "karst"
    ],
    install_requires=[
        "astor",
        "z3-solver",
    ],
)
