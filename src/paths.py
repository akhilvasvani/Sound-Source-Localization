#!/usr/bin/env python
"""Single configurable data directory for everything the deployed app
writes at runtime: uploaded recordings, generated .mat scratch files,
caches, and logs.

Controlled entirely by the APP_DATA_DIR environment variable so the same
code works unchanged in local development and in the single Dockerized
Render Web Service:

    - Local dev: APP_DATA_DIR unset -> falls back to ./app_data at the
      repo root (created on demand, already gitignored).
    - Production (Render): APP_DATA_DIR=/var/data, set in render.yaml.

Nothing under here is expected to be a system-of-record. Uploaded files
and generated .mat files are per-request scratch data, read back once
within the same request/run and never needed again afterward -- see
README.md's "Storage & persistence" section for the full reasoning on
why no persistent disk is attached by default.
"""

import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_app_data_dir():
    """Root runtime-writable directory, created if it doesn't exist."""
    base = os.environ.get("APP_DATA_DIR") or os.path.join(REPO_ROOT, "app_data")
    os.makedirs(base, exist_ok=True)
    return base


def get_uploads_dir():
    """Subdirectory for temporarily-staged user uploads."""
    path = os.path.join(get_app_data_dir(), "uploads")
    os.makedirs(path, exist_ok=True)
    return path


def get_generated_dir():
    """Subdirectory for generated .mat scratch files produced mid-pipeline."""
    path = os.path.join(get_app_data_dir(), "generated")
    os.makedirs(path, exist_ok=True)
    return path
