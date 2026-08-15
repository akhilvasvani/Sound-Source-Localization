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
import uuid

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class AppDataDirError(RuntimeError):
    """Raised when APP_DATA_DIR can't be created or isn't actually writable.

    Deliberately a plain, readable message rather than a bare OSError --
    this is what demo/app.py's generic exception handler shows the user
    (`st.error(f"DOA pipeline failed: {exc}")`), so it needs to point at
    the fix, not just repeat errno text. See the Dockerfile and
    scripts/check_app_data_dir.sh, which should catch this before
    Streamlit ever starts in the deployed container -- if it surfaces
    here instead, that startup check was bypassed or the directory
    ownership doesn't match the running user.
    """


def _ensure_dir_writable(path):
    """Create `path` if needed and verify it's writable by actually
    writing and removing a scratch file (not just checking permission
    bits, which can be misleading on some filesystems/ACLs).
    """
    try:
        os.makedirs(path, exist_ok=True)
        probe = os.path.join(path, f".write_test_{uuid.uuid4().hex}")
        with open(probe, "w"):
            pass
        os.remove(probe)
    except OSError as exc:
        raise AppDataDirError(
            f"APP_DATA_DIR resolved to {path!r} but it could not be created or "
            f"is not writable by the current process (uid={os.getuid()}): {exc}. "
            "In the deployed container, this directory must be created and "
            "chowned to the runtime user at image build time (see Dockerfile)."
        ) from exc
    return path


def get_app_data_dir():
    """Root runtime-writable directory, created if it doesn't exist."""
    base = os.environ.get("APP_DATA_DIR") or os.path.join(REPO_ROOT, "app_data")
    return _ensure_dir_writable(base)


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
