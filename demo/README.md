# Part 2 demo -- local run instructions

Single-page interactive demo: pick a preset (mix of the heart-proxy
signal and real-world audio) or upload your own multi-channel
recording, run the existing DOA + triangulation pipeline on it, and see
the estimated vs. true source position/bearing in a 3-D view plus a
results panel.

**Stack:** FastAPI backend (`api/app.py`, wraps `src/pipeline.py`) +
Streamlit frontend (`demo/app.py`, calls the backend over plain HTTP).

## Run locally (two terminals)

```bash
# from the repo root, with the venv activated and `pip install -r requirements.txt`
# plus `pip install streamlit plotly requests` already done

# Terminal 1 -- backend
uvicorn api.app:app --host 0.0.0.0 --port 8000

# Terminal 2 -- frontend
streamlit run demo/app.py
```

Then open the URL Streamlit prints (typically http://localhost:8501).

## Run via Docker (single container, both processes)

```bash
docker build -t doa-demo .
docker run -p 8080:8080 -e PORT=8080 doa-demo
```

Then open http://localhost:8080. See the root `Dockerfile` and
`docker-entrypoint.sh` for how the two processes are started inside one
container (needed because most simple hosting targets, including Cloud
Run, expose exactly one port per service).

**Note:** this Dockerfile has NOT been build-tested in the development
sandbox used to write this demo (no Docker daemon was available there).
The two processes it runs (`uvicorn api.app:app` and
`streamlit run demo/app.py`) were each verified working directly in
that sandbox; the container packaging itself is untested. Please build
and run it once locally before relying on it.

## API reference (for the curious / for `curl` testing)

- `GET /api/health` -- liveness check
- `GET /api/presets` -- the 4 preset examples, available algorithms, RT60 levels
- `GET /api/upload-mic-geometry` -- the mic layout an uploaded recording is assumed to use
- `POST /api/run/preset` -- `{"preset_id", "algorithm", "rt60_level", "n_grid"}` -> report
- `POST /api/run/upload` -- multipart form: `file` (.wav/.flac), `algorithm`, optional `room_dim` ("x,y,z"), optional `true_source_m` ("x,y,z") -> report

## Known limitation: single-array uploads

If you upload your own multi-channel recording, the demo assumes it
came from ONE small (~15 cm) 4-mic tetrahedral array (geometry at
`GET /api/upload-mic-geometry`). A single array/cluster can only
resolve a bearing (azimuth + colatitude), not a full 3-D position fix
-- triangulating a position needs at least two spatially-separated
arrays. This is a real, physical limitation of DOA-only localization,
not a demo bug; the response's `position_available: false` and `note`
fields make this explicit rather than silently showing a meaningless
number. The 4 built-in presets don't have this limitation because they
simulate 4 separated mic clusters (matching `src/pipeline.py`'s
`DEFAULT_CLUSTER_CENTERS`), so they always return a full 3-D estimate.
