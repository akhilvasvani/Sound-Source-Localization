# Single-process deployment: one Streamlit app (demo/app.py), one
# container, one Render Web Service. No separate backend process is
# started -- demo/app.py calls src/service.py -> src/pipeline.py
# in-process (see README.md's "Architecture" section for why no
# long-running worker/queue is needed for this workload).
#
# Build:  docker build -t doa-demo .
# Run:    docker run -p 8080:8080 -e PORT=8080 doa-demo
# Then visit http://localhost:8080

FROM python:3.11-slim

# pyroomacoustics needs a C/C++ toolchain to build its Cython extensions,
# and libsndfile1 is required by the `soundfile` package used for audio I/O.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN pip install --no-cache-dir -e .

RUN chmod +x docker-entrypoint.sh

# Local default data directory for `docker run` without APP_DATA_DIR set;
# Render sets APP_DATA_DIR=/var/data explicitly (see render.yaml).
ENV APP_DATA_DIR=/app/app_data
RUN mkdir -p "$APP_DATA_DIR"

# Run as a non-root user. Render injects $PORT at runtime; we don't
# hard-code a value here (see docker-entrypoint.sh, which expands it).
RUN useradd --create-home --uid 1000 appuser \
    && chown -R appuser:appuser /app
USER appuser

# Documents the conventional local port; Render overrides $PORT itself,
# and docker-entrypoint.sh falls back to this value if $PORT is unset.
EXPOSE 8080

# Streamlit does not expose a distinct HTTP health-check JSON endpoint by
# default; Render's default TCP check against $PORT is used instead (see
# render.yaml). Streamlit's own `/_stcore/health` path does exist and
# returns 200 with body "ok", so it's documented as an optional HTTP
# health-check path if a stricter check is ever wanted.

CMD ["./docker-entrypoint.sh"]
