from setuptools import setup

setup(
    name = "blog",
    version = "dev",
    packages = ['blog'],
    package_data = {'blog': ['templates/*']}
)
