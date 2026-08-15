#!/usr/bin/env python
"""Optional FastAPI wrapper around src/service.py -- kept for local
development / `curl` testing and for the existing test suite
(test/unit/test_api.py), but NOT started in the deployed architecture.

The deployed app is a single Streamlit process (demo/app.py) that calls
src/service.py's functions directly, in-process -- no HTTP hop, no
second server to run/monitor/keep alive. This file is not imported or
started anywhere in the Docker image's runtime command; it exists purely
as an optional convenience for anyone who wants a REST API on top of the
same pipeline (e.g. for scripting/automation against a locally-run
instance), and to keep the existing endpoint-level tests exercising the
request/response contract.

  GET  /api/presets             -- list the 4 preset examples
  POST /api/run/preset           -- run the DOA pipeline on a preset
  POST /api/run/upload           -- run the DOA pipeline on an uploaded
                                     multi-channel .wav/.flac recording
  GET  /api/upload-mic-geometry  -- the mic layout an upload is assumed to use
  GET  /api/health                -- liveness check

No auth, no database -- everything is computed on demand and returned in
the response; nothing is persisted beyond the request's lifetime (see
src/service.py for exactly where any scratch files briefly land and get
cleaned up).

Run locally (optional, not required to use the Streamlit demo):
    uvicorn api.app:app --host 0.0.0.0 --port 8000
"""

from fastapi import FastAPI, File, HTTPException, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.service import (
    UPLOAD_MIC_GEOMETRY,
    list_presets,
    run_preset,
    run_upload,
)

app = FastAPI(
    title="Sound Source Localization -- Demo API (optional, dev-only)",
    description="Optional REST wrapper over src/service.py. Not part of the "
                "deployed architecture -- see this file's module docstring.",
    version="1.0",
)

# Permissive CORS: this is a no-auth, no-database, optional dev-only API
# with no sensitive data -- broad CORS is a deliberate, documented
# simplification, not an oversight.
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)


class PresetRunRequest(BaseModel):
    preset_id: str
    algorithm: str = "SRP"
    rt60_level: str = "medium"
    n_grid: int = 4000


@app.get("/api/presets")
def presets_endpoint():
    return list_presets()


@app.get("/api/upload-mic-geometry")
def upload_mic_geometry():
    return UPLOAD_MIC_GEOMETRY


@app.post("/api/run/preset")
def run_preset_endpoint(req: PresetRunRequest):
    try:
        return run_preset(req.preset_id, algorithm=req.algorithm,
                           rt60_level=req.rt60_level, n_grid=req.n_grid)
    except KeyError as exc:
        message = str(exc).strip("'")
        status_code = 404 if "preset_id" in message else 400
        raise HTTPException(status_code=status_code, detail=message)


@app.post("/api/run/upload")
def run_upload_endpoint(
    file: UploadFile = File(...),
    algorithm: str = Form("SRP"),
    room_dim: str = Form(None),  # optional "x,y,z" in meters
    true_source_m: str = Form(None),  # optional "x,y,z" if visitor knows the true position
):
    room = [float(x) for x in room_dim.split(",")] if room_dim else None
    true_pos = [float(x) for x in true_source_m.split(",")] if true_source_m else None

    try:
        return run_upload(file.file.read(), file.filename, algorithm=algorithm,
                           room_dim=room, true_source_m=true_pos)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc).strip("'"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"DOA pipeline failed: {exc}")


@app.get("/api/health")
def health():
    return {"status": "ok"}
