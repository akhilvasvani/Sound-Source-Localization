# Single-container deployment for the Part 2 demo: runs the FastAPI
# backend (api/app.py) and the Streamlit frontend (demo/app.py) as two
# processes inside one container, since Cloud Run (and most simple PaaS
# targets) expose exactly one port per service. The entrypoint script
# starts uvicorn in the background on an internal port, then starts
# Streamlit in the foreground bound to Cloud Run's $PORT.
#
# Build:  docker build -t doa-demo .
# Run:    docker run -p 8080:8080 -e PORT=8080 doa-demo
# Then visit http://localhost:8080
#
# Deploy to Cloud Run (requires `gcloud` + a GCP project -- NOT
# available in this session's connectors; see reports/part1_results.md
# / the PR description for the honest deployment-attempt writeup):
#   gcloud run deploy doa-demo --source . --port 8080 --memory 1Gi

FROM python:3.11-slim

# pyroomacoustics needs a C/C++ toolchain to build its Cython extensions,
# and libsndfile1 is required by the `soundfile` package used for audio I/O.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libsndfile1 \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir streamlit>=1.30 plotly>=5.20 requests>=2.31

COPY . .
RUN pip install --no-cache-dir -e .

ENV PORT=8080
EXPOSE 8080

RUN chmod +x docker-entrypoint.sh
CMD ["./docker-entrypoint.sh"]
