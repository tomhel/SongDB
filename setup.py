# coding=utf-8

from setuptools import setup, find_packages

setup(
    name="SongDB",
    version="0.4",
    description="SongDB indexes your music collection",
    author="Tommy Hellstrom",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "Flask",
        "waitress"
    ],
    entry_points={
        "console_scripts": [
            "songdb_server=songdb.server:main"
        ]
    },
    classifiers=[
        "Python :: 3"
    ],
    python_requires='>=3'
)
