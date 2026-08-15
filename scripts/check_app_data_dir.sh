#!/usr/bin/env bash
# Verifies that the app-data directory exists and is genuinely writable
# by the user currently running this script -- by creating and removing
# a real scratch file, not just by inspecting permission bits (which can
# be misleading across some filesystems/ACLs).
#
# Used by docker-entrypoint.sh as a fail-fast startup check, before
# Streamlit (and the slower pyroomacoustics/scipy imports behind it)
# ever starts. Also exercised directly, as a subprocess, by
# test/unit/test_app_data_dir.py as a regression test for the incident
# where Render's APP_DATA_DIR=/var/data was not writable by the non-root
# container user (/var is root-owned, mode 755, in the base image, so a
# non-root process cannot create /var/data itself at runtime -- see
# reports/deployment_status.md).
#
# Usage: check_app_data_dir.sh [directory]
#   Defaults to $APP_DATA_DIR, falling back to /app/app_data.
set -euo pipefail

DIR="${1:-${APP_DATA_DIR:-/app/app_data}}"
WHOAMI="$(id -un 2>/dev/null || echo unknown)"
UID_NUM="$(id -u 2>/dev/null || echo unknown)"

echo "app-data check: resolved APP_DATA_DIR=${DIR} (running as ${WHOAMI}, uid ${UID_NUM})"

if ! mkdir -p "$DIR"; then
    echo "FATAL: could not create directory '${DIR}' as ${WHOAMI} (uid ${UID_NUM})." >&2
    echo "       Fix: ensure '${DIR}' is created and chowned to this user's uid" >&2
    echo "       at image build time (see Dockerfile) -- a non-root process cannot" >&2
    echo "       create new directories under a root-owned parent (e.g. /var) at runtime." >&2
    exit 1
fi

TESTFILE="${DIR}/.startup_write_test_$$"
if ! ( : > "$TESTFILE" ) 2>/dev/null; then
    echo "FATAL: '${DIR}' exists but is not writable by ${WHOAMI} (uid ${UID_NUM})." >&2
    echo "       Fix: chown '${DIR}' to this user's uid at image build time (see Dockerfile)." >&2
    exit 1
fi
rm -f "$TESTFILE"

echo "app-data check: OK -- ${DIR} is writable by ${WHOAMI} (uid ${UID_NUM})"
