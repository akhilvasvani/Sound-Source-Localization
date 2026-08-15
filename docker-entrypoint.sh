#!/usr/bin/env bash
# Single process: Streamlit bound to 0.0.0.0:$PORT. Used as an entrypoint
# script (rather than a literal Dockerfile CMD) purely so $PORT is
# reliably expanded at container start -- Render sets $PORT dynamically
# and CMD's exec-form JSON array does not perform shell expansion.
set -euo pipefail

APP_DATA_DIR="${APP_DATA_DIR:-/app/app_data}"
export APP_DATA_DIR

# Fail fast, with a clear message, if the app-data directory isn't
# actually writable by this process -- before Streamlit and the slower
# pyroomacoustics/scipy imports behind it even start. The directory
# should already exist and be chowned to this user from the Docker
# build (see Dockerfile); this is a startup assertion, not the primary
# fix -- it exists so a misconfiguration surfaces as a clear one-line
# log message instead of a cryptic PermissionError deep inside the DOA
# pipeline the first time a user clicks "Run".
"$(dirname "$0")/scripts/check_app_data_dir.sh" "$APP_DATA_DIR"

exec streamlit run demo/app.py \
    --server.address 0.0.0.0 \
    --server.port "${PORT:-8080}" \
    --server.headless true
