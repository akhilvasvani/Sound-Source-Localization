#!/usr/bin/env bash
# Single process: Streamlit bound to 0.0.0.0:$PORT. Used as an entrypoint
# script (rather than a literal Dockerfile CMD) purely so $PORT is
# reliably expanded at container start -- Render sets $PORT dynamically
# and CMD's exec-form JSON array does not perform shell expansion.
set -euo pipefail

exec streamlit run demo/app.py \
    --server.address 0.0.0.0 \
    --server.port "${PORT:-8080}" \
    --server.headless true
