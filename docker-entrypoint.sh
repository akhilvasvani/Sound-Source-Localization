#!/usr/bin/env bash
# Starts the FastAPI backend (internal port 8000) in the background, then
# the Streamlit frontend in the foreground bound to $PORT (Cloud Run's
# externally-exposed port). Container exits if either process exits.
set -euo pipefail

uvicorn api.app:app --host 0.0.0.0 --port 8000 &
API_PID=$!

# Wait for the backend to become healthy before starting the frontend.
for i in $(seq 1 30); do
    if curl -sf "http://localhost:8000/api/health" > /dev/null 2>&1; then
        break
    fi
    sleep 1
done

export DOA_API_BASE_URL="http://localhost:8000"

streamlit run demo/app.py \
    --server.port "${PORT:-8080}" \
    --server.address 0.0.0.0 \
    --server.headless true &
STREAMLIT_PID=$!

# If either process dies, bring the container down so the platform restarts it.
wait -n "$API_PID" "$STREAMLIT_PID"
exit $?
