# Deployment status (honest report)

**Bottom line: the demo is now a single Dockerized Streamlit service,
verified working end-to-end locally through the exact command Render
will run in production. It has not been deployed to a live Render URL
from this session** -- there is no Render connector/CLI available here
(only GitHub, Vercel, a finance data tool, and a sports-odds tool are
connected), so the actual `render.yaml` apply step has to be done by
the repo owner in the Render dashboard. Everything up to that last step
has been built and tested.

This supersedes the previous version of this report, which covered a
different, now-abandoned architecture (FastAPI backend + Streamlit
frontend as two processes, targeting Cloud Run/Vercel). That direction
was explicitly replaced: no Google Cloud services of any kind, single
Dockerized Streamlit service on Render. See `README.md`'s "Architecture"
section for the reasoning behind the current design.

## What changed and why

- **One process, not two.** `demo/app.py` (Streamlit) now calls
  `src/service.py` -> `src/pipeline.py` directly, in-process. The
  previous architecture ran a FastAPI backend and a Streamlit frontend
  as two processes in one container, talking over HTTP
  (`DOA_API_BASE_URL`). That HTTP hop added no value for a
  single-container deployment with no other consumer of the API, so it
  was removed. `api/app.py` still exists and still works (same
  `src/service.py` underneath), but it is optional and not started in
  the deployed container -- see `demo/README.md`.
- **No GCP anywhere.** The old `Dockerfile`/`docker-entrypoint.sh`
  header comments referenced `gcloud run deploy` as a suggested next
  step; no actual GCP SDK, Terraform, Cloud Build config, or
  service-account file ever existed in this repo (confirmed by
  searching the full repository tree). Those comments have been
  removed/replaced with Render-specific instructions.
- **`vercel.json` removed.** It routed the old FastAPI backend through
  Vercel's Python serverless runtime. With no separate backend process
  in the new architecture, and no separate Next.js/static marketing
  frontend anywhere in this repo, there is nothing left for Vercel to
  deploy -- see `README.md`'s "Vercel" section.
- **Storage now goes through `APP_DATA_DIR`.** Uploaded recordings and
  generated `.mat` scratch files used to land in the system temp
  directory (`tempfile.NamedTemporaryFile`) and a hardcoded
  `output/test_first_fun.mat` path respectively -- neither was
  configurable. Both now derive from a single `APP_DATA_DIR` environment
  variable (`src/paths.py`), defaulting to `./app_data` locally and set
  to `/var/data` in `render.yaml`. See `README.md`'s "Storage &
  persistence" section for why no persistent disk is attached.

## What was actually tested this session (verified, not assumed)

There is still no `docker` binary in this development sandbox (confirmed:
`which docker` returns nothing), so `docker build`/`docker run` could not
be executed literally. To validate as much of the real deployment path
as possible without a Docker daemon, the exact command the container
will run was executed directly:

```bash
APP_DATA_DIR=/tmp/app_data_test PORT=8091 ./docker-entrypoint.sh
```

This runs the identical `docker-entrypoint.sh` script that `CMD` invokes
inside the image, with `$PORT` expansion exercised for real (not just
read as source). Results:

- The script correctly expanded `${PORT:-8080}` to `8091` and bound
  Streamlit to `0.0.0.0:8091` (confirmed in the process's own startup log).
- `curl http://localhost:8091/` returned `HTTP 200` with real Streamlit
  HTML (not an error page).
- `curl http://localhost:8091/_stcore/health` returned `HTTP 200` with
  body `ok` -- Streamlit's built-in health path, a viable
  `healthCheckPath` alternative to Render's default TCP check (see
  README).
- `APP_DATA_DIR=/tmp/app_data_test` was created and confirmed writable.
- A full **Playwright browser click-through** against the running app
  (not just an HTTP status check) exercised both modes end-to-end:
  - **Preset mode:** selected a preset (the heart-proxy preset at the
    time of this validation run; it has since been removed from the
    demo -- see README.md and PR #3), clicked "Run DOA pipeline,"
    confirmed the Results panel, Algorithm/Runtime metrics, and 3-D
    visualization all rendered with real computed numbers.
  - **Upload mode:** uploaded a synthetic 4-channel `.wav`, clicked "Run
    DOA pipeline," confirmed the "No 3-D position fix" messaging
    rendered correctly (expected for a single mic cluster, per the
    documented physical limitation).
  - After both runs, `APP_DATA_DIR`'s `generated/` and `uploads/`
    subdirectories were confirmed **empty** -- scratch files are
    created, consumed, and deleted within the same request, as designed.
- `pytest test/` -- **104/104 passing** after the refactor (unchanged
  count from before this round; `api/app.py`'s tests still pass against
  the same endpoints, now backed by the shared `src/service.py`).
- Missing-secret handling: this app has no optional secrets at all
  (`DOA_API_BASE_URL`, the only env var the old architecture read, was
  removed entirely). Bad *inputs* (unknown preset id, unknown algorithm,
  unsupported upload file extension) were confirmed to raise plain
  `KeyError`/`ValueError` from `src/service.py`, which `demo/app.py`
  catches and renders as `st.error(...)` rather than an unhandled
  stack trace, and which `api/app.py` translates to a 4xx `HTTPException`.

**What was not literally tested:** the actual `docker build` step (no
Docker daemon available) and an actual live deploy to Render (no Render
connector/CLI available in this session). The entrypoint script,
`$PORT` handling, Streamlit process behavior, and full pipeline logic it
wraps were all verified directly; the remaining risk is narrow --
mainly whether the `Dockerfile`'s `apt-get`/`pip install` steps succeed
in a real Docker build environment, which could not be executed here.

## Recommended next step

1. Run `docker build -t doa-demo .` and `docker run -p 8080:8080 -e
   PORT=8080 doa-demo` locally (wherever Docker is available) as a final
   sanity check before deploying -- the app logic itself is already
   verified end-to-end via the method above.
2. Push to GitHub, then either apply `render.yaml` via Render's
   Blueprint flow, or create the Web Service manually using the exact
   values in `README.md`'s "Deploying to Render" section.
3. No further Vercel action needed -- there is no separate frontend for
   this app.

## Incident: `/var/data` permission denied on Render (fixed)

After the first real Render deploy, the app failed at runtime with:

```
DOA pipeline failed: [Errno 13] Permission denied: '/var/data'
```

**Cause:** `python:3.11-slim` (like most Debian-based images) ships
`/var` as root-owned, mode `755`. The old `Dockerfile` only created and
chowned the local-dev default (`/app/app_data`) to the non-root
`appuser` at build time -- it never touched `/var/data`, the path
Render actually sets `APP_DATA_DIR` to in production. At runtime,
`appuser` (uid 1000) tried to `os.makedirs("/var/data")` and was denied,
since a non-root process cannot create a new directory under a
root-owned, non-writable parent.

**Fix:**
- `Dockerfile` now creates **both** `/app/app_data` and `/var/data` and
  chowns both to `appuser`, while still root, before the `USER appuser`
  switch -- so `/var/data` already exists and is writable by the time
  the container starts, regardless of which `APP_DATA_DIR` value is set.
- `docker-entrypoint.sh` now runs `scripts/check_app_data_dir.sh` before
  starting Streamlit: it resolves `APP_DATA_DIR`, logs the running user,
  and creates + removes a real scratch file to verify actual
  writability -- failing fast with a clear `FATAL` message instead of a
  cryptic error the first time a user clicks "Run".
- `src/paths.py`'s `get_app_data_dir()` now performs the same real
  write-probe and raises a clear `AppDataDirError` (naming the resolved
  path, the uid, and pointing at the Dockerfile) if it's ever wrong
  again, instead of letting a bare `PermissionError` bubble up.

**Verified (as the actual non-root sandbox user, uid 2000, no Docker
daemon available -- same limitation as the rest of this report):**
- `test/unit/test_app_data_dir.py` (7 new tests, all passing): confirms
  `get_app_data_dir()`/`get_uploads_dir()`/`get_generated_dir()` create
  and write/remove scratch files successfully; confirms a clear
  `AppDataDirError` (not a bare `OSError`) is raised when pointed at an
  unwritable directory; runs `scripts/check_app_data_dir.sh` directly as
  a subprocess and confirms it succeeds (and leaves no scratch file
  behind) against a writable directory, and fails with `FATAL` in
  `stderr` against an unwritable one.
- Ran the real `docker-entrypoint.sh` twice: once pointed at a
  deliberately unwritable directory (a `chmod 555` parent, simulating
  root-owned `/var`) -- confirmed it fails immediately with the `FATAL`
  message and never starts Streamlit; once pointed at a plain writable
  directory (simulating the new build-time chown) -- confirmed the
  check passes, Streamlit starts, `curl` gets `HTTP 200`, and no probe
  files are left under `APP_DATA_DIR` afterward.
- Full suite: **111/111 passing** (104 previous + 7 new).
