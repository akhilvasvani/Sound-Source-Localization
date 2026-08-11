#!/usr/bin/env python
"""Setup script for Sound-Source-Localization.

Installs the `src` and `tools` packages so the project's modules and
tests can be run/imported from anywhere, e.g.:

    pip install -e .
    python -m src.main
    pytest test/
"""

from setuptools import setup, find_packages

with open("requirements.txt") as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="sound-source-localization",
    version="0.2.0",
    description="Reverberant sound-source localization via DOA estimation "
                "and robust ray triangulation (pyroomacoustics).",
    packages=find_packages(include=["src", "src.*", "tools", "tools.*"]),
    install_requires=requirements,
    python_requires=">=3.8",
)
