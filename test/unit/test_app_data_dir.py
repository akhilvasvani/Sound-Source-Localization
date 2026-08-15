"""Regression tests for the Render deployment permission incident:

    DOA pipeline failed: [Errno 13] Permission denied: '/var/data'

Root cause: /var is root-owned (mode 755) in the python:3.11-slim base
image, so the non-root container user could not create /var/data itself
at runtime. The fix creates and chowns /var/data to that user at image
build time (see Dockerfile) and adds a startup assertion
(scripts/check_app_data_dir.sh, wired into docker-entrypoint.sh) that
fails fast with a clear message if it's ever wrong again.

These tests exercise both layers as the actual, unprivileged process
running the test suite (never as root) -- proving a non-root process can
create and remove a scratch file under APP_DATA_DIR, and that clear,
actionable errors (not bare stack traces) are raised when it can't.
"""

import os
import stat
import subprocess
import sys

import pytest

from src.paths import AppDataDirError, get_app_data_dir, get_generated_dir, get_uploads_dir

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CHECK_SCRIPT = os.path.join(REPO_ROOT, "scripts", "check_app_data_dir.sh")

running_as_root = os.getuid() == 0  # permission-denial tests are meaningless as root


def test_not_running_as_root():
    """Sanity check that this test module is actually exercising the
    non-root path the fix targets (mirrors the container's appuser)."""
    assert os.getuid() != 0, "expected to run as a non-root user, like the container's appuser"


def test_get_app_data_dir_creates_and_is_writable(tmp_path, monkeypatch):
    target = tmp_path / "app_data"
    monkeypatch.setenv("APP_DATA_DIR", str(target))

    resolved = get_app_data_dir()

    assert resolved == str(target)
    assert os.path.isdir(resolved)
    # get_app_data_dir() itself performs a real write+remove probe;
    # confirm no leftover probe files were left behind.
    assert os.listdir(resolved) == []


def test_get_uploads_and_generated_dirs_writable_by_current_user(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_DATA_DIR", str(tmp_path / "app_data"))

    uploads_dir = get_uploads_dir()
    generated_dir = get_generated_dir()

    for directory in (uploads_dir, generated_dir):
        assert os.path.isdir(directory)
        scratch = os.path.join(directory, "scratch_test_file.bin")
        with open(scratch, "wb") as fh:
            fh.write(b"non-root scratch write")
        assert os.path.exists(scratch)
        os.remove(scratch)
        assert not os.path.exists(scratch)


@pytest.mark.skipif(running_as_root, reason="permission denial is meaningless for root")
def test_get_app_data_dir_raises_clear_error_when_unwritable(tmp_path, monkeypatch):
    """Regression test for the exact failure mode seen on Render: a
    directory that exists but isn't writable by this process should
    raise a clear, actionable AppDataDirError -- not a bare
    PermissionError/OSError with just an errno and a path."""
    locked_parent = tmp_path / "locked"
    locked_parent.mkdir()
    locked_parent.chmod(0o555)  # read+execute only, like a root-owned /var

    target = locked_parent / "app_data"
    monkeypatch.setenv("APP_DATA_DIR", str(target))

    try:
        with pytest.raises(AppDataDirError) as excinfo:
            get_app_data_dir()
        message = str(excinfo.value)
        assert "APP_DATA_DIR" in message
        assert str(target) in message
        assert "Dockerfile" in message  # points at the actual fix location
    finally:
        locked_parent.chmod(0o755)  # restore so tmp_path cleanup can remove it


def _run_check_script(directory):
    env = dict(os.environ)
    env["APP_DATA_DIR"] = str(directory)
    return subprocess.run(
        [CHECK_SCRIPT, str(directory)],
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )


def test_check_app_data_dir_script_is_executable():
    assert os.path.isfile(CHECK_SCRIPT)
    mode = os.stat(CHECK_SCRIPT).st_mode
    assert mode & stat.S_IXUSR, "scripts/check_app_data_dir.sh must be executable (chmod +x)"


def test_check_app_data_dir_script_succeeds_and_leaves_no_scratch_file(tmp_path):
    """This is the direct regression test for requirement: a non-root
    process can create and remove a scratch file under APP_DATA_DIR.
    Runs the exact script docker-entrypoint.sh calls at container
    startup, as whatever user is running this test (never root here)."""
    target = tmp_path / "app_data"

    result = _run_check_script(target)

    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout
    assert os.path.isdir(target)
    # The script must clean up its own probe file -- nothing should be
    # left behind under APP_DATA_DIR after a successful check.
    assert os.listdir(target) == []


@pytest.mark.skipif(running_as_root, reason="permission denial is meaningless for root")
def test_check_app_data_dir_script_fails_clearly_when_unwritable(tmp_path):
    """Mirrors the original incident: point the script at a directory
    this process cannot write to and confirm it fails fast with a clear
    FATAL message (not a Python stack trace 60 seconds into a DOA run)."""
    locked_parent = tmp_path / "locked"
    locked_parent.mkdir()
    locked_parent.chmod(0o555)
    target = locked_parent / "app_data"

    try:
        result = _run_check_script(target)
        assert result.returncode != 0
        assert "FATAL" in result.stderr
    finally:
        locked_parent.chmod(0o755)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
