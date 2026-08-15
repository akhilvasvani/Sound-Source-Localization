# Interactive demo -- local run instructions

Single-page interactive demo: pick a preset (mix of the heart-proxy
signal and real-world audio) or upload your own multi-channel
recording, run the existing DOA + triangulation pipeline on it, and see
the estimated vs. true source position/bearing in a 3-D view plus a
results panel.

**Stack:** a single Streamlit process (`demo/app.py`) that calls
`src/service.py` -> `src/pipeline.py` directly, in-process. There is no
separate backend server to start -- see the root [`README.md`](../README.md)'s
"Architecture" section for why.

## Run locally

```bash
# from the repo root, with the venv activated and `pip install -r requirements.txt` done
streamlit run demo/app.py
```

Then open the URL Streamlit prints (typically http://localhost:8501).

## Run via Docker (single container, single process)

```bash
docker build -t doa-demo -f ../Dockerfile ..   # or from the repo root: docker build -t doa-demo .
docker run -p 8080:8080 -e PORT=8080 doa-demo
```

Then open http://localhost:8080. See the root [`Dockerfile`](../Dockerfile),
[`docker-entrypoint.sh`](../docker-entrypoint.sh), and
[`README.md`](../README.md)'s "Deploying to Render" section for the full
deployment story.

## Optional: the FastAPI wrapper (`api/app.py`)

`api/app.py` exposes the same logic (`src/service.py`) as a small REST
API, purely for local `curl`/scripting convenience and for
`test/unit/test_api.py`'s endpoint tests. It is **not** started by
`docker-entrypoint.sh` and is not required to use the Streamlit demo --
you can ignore it entirely unless you specifically want a REST interface:

```bash
uvicorn api.app:app --host 0.0.0.0 --port 8000
```

- `GET /api/health` -- liveness check
- `GET /api/presets` -- the 4 preset examples, available algorithms, RT60 levels
- `GET /api/upload-mic-geometry` -- the mic layout an uploaded recording is assumed to use
- `POST /api/run/preset` -- `{"preset_id", "algorithm", "rt60_level", "n_grid"}` -> report
- `POST /api/run/upload` -- multipart form: `file` (.wav/.flac), `algorithm`, optional `room_dim` ("x,y,z"), optional `true_source_m` ("x,y,z") -> report

## Known limitation: single-array uploads

If you upload your own multi-channel recording, the demo assumes it
came from ONE small (~15 cm) 4-mic tetrahedral array (geometry available
via `src.service.UPLOAD_MIC_GEOMETRY`, or `GET /api/upload-mic-geometry`
if using the optional API). A single array/cluster can only resolve a
bearing (azimuth + colatitude), not a full 3-D position fix --
triangulating a position needs at least two spatially-separated arrays.
This is a real, physical limitation of DOA-only localization, not a demo
bug; the response's `position_available: false` and `note` fields make
this explicit rather than silently showing a meaningless number. The 4
built-in presets don't have this limitation because they simulate 4
separated mic clusters (matching `src/pipeline.py`'s
`DEFAULT_CLUSTER_CENTERS`), so they always return a full 3-D estimate.
