#!/usr/bin/env python
"""FastAPI backend for the Part 2 demo: wraps src/pipeline.py (the same
DOA-estimation + ray-triangulation code used by experiments/
real_world_benchmark.py) as a small REST API.

Two capabilities, matching the task brief:

  GET  /api/presets        -- list 4 preset examples (mix of the
                               heart-proxy signal and real-world audio)
  POST /api/run/preset      -- run the DOA pipeline on a chosen preset
                               (room-simulated, ground truth known
                               exactly, 4 mic clusters -> full 3-D
                               position estimate)
  POST /api/run/upload       -- run the DOA pipeline on a visitor's own
                               multi-channel .wav/.flac upload (assumed
                               to already be a real recording captured
                               by one small 4-mic tetrahedral array in
                               the geometry documented at
                               /api/upload-mic-geometry; no simulation).
                               A single array gives a BEARING, not a
                               3-D fix -- see src/pipeline.py's
                               `position_available` flag, surfaced
                               here unmodified.
  GET  /api/upload-mic-geometry -- the exact mic layout an uploaded
                               recording is assumed to use.

No auth, no database -- everything is computed on demand and returned
in the response; nothing is persisted server-side beyond the request's
lifetime, per the task's "no auth, no database" scope constraint.
"""

import os
import shutil
import tempfile

from fastapi import FastAPI, File, HTTPException, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.pipeline import (
    ALGORITHMS,
    DEFAULT_ROOM_DIM,
    RT60_LEVELS,
    TETRA_POSITIONS,
    run_doa_from_multichannel_upload,
    run_doa_from_source_file,
)
from src.audio_source import SUPPORTED_EXTENSIONS

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = FastAPI(
    title="Sound Source Localization -- Demo API",
    description="Wraps the pyroomacoustics DOA/triangulation pipeline from "
                "akhilvasvani/Sound-Source-Localization as a REST endpoint.",
    version="1.0",
)

# Permissive CORS: this is a no-auth, no-database, weekend-scope demo with
# no sensitive data -- broad CORS is a deliberate, documented simplification,
# not an oversight, and would need tightening for anything beyond a demo.
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

# --------------------------------------------------------------------------
# Preset catalog -- a mix of heart-proxy and real-world examples, per the
# task brief ("3-4 preset synthetic examples (mix of heart-sound and
# real-world presets)"). Ground truth source position is known exactly
# because these are room-simulated with a known source location.
# --------------------------------------------------------------------------
PRESETS = [
    {
        "id": "heart_proxy",
        "label": "Heart-proxy signal (white noise, [300-1000 Hz])",
        "description": "Reproduces the ORIGINAL repo's baseline test signal exactly -- "
                       "band-limited Gaussian white noise, not real heart-sound audio "
                       "(no .mat heart recording exists in this repo; see "
                       "data/heart_proxy_samples/README.md).",
        "wav_path": os.path.join(REPO_ROOT, "data", "heart_proxy_samples", "white_noise_0.wav"),
        "true_source_m": [3.0, 1.0, 1.7],
        "freq_range": [300, 1000],
    },
    {
        "id": "librispeech_0",
        "label": "Real speech clip (LibriSpeech)",
        "description": "Real human speech, HuggingFace hf-internal-testing/librispeech_asr_dummy.",
        "wav_path": os.path.join(REPO_ROOT, "data", "librispeech_samples", "sample_0.wav"),
        "true_source_m": [1.0, 2.0, 0.6],
        "freq_range": [300, 3400],
    },
    {
        "id": "librispeech_1",
        "label": "Real speech clip #2 (LibriSpeech)",
        "description": "A second, different real speech clip from the same dataset.",
        "wav_path": os.path.join(REPO_ROOT, "data", "librispeech_samples", "sample_1.wav"),
        "true_source_m": [2.0, 1.5, 2.0],
        "freq_range": [300, 3400],
    },
    {
        "id": "esc50_rain",
        "label": "Real environmental sound (rain, ESC-50)",
        "description": "Real environmental audio, HuggingFace ashraq/esc50.",
        "wav_path": os.path.join(REPO_ROOT, "data", "esc50_samples", "rain.wav"),
        "true_source_m": [0.6, 0.6, 1.9],
        "freq_range": [300, 3400],
    },
]
PRESETS_BY_ID = {p["id"]: p for p in PRESETS}

UPLOAD_MIC_GEOMETRY = {
    "positions_m": TETRA_POSITIONS,
    "note": "A single small (~15 cm) non-planar tetrahedral 4-mic cluster, "
           "centered at the array's own position. A single cluster/array "
           "resolves a BEARING (azimuth + colatitude) but NOT a 3-D fix -- "
           "see the `position_available` field in the response.",
}


class PresetRunRequest(BaseModel):
    preset_id: str
    algorithm: str = "SRP"
    rt60_level: str = "medium"
    n_grid: int = 4000


@app.get("/api/presets")
def list_presets():
    return {"presets": [{k: v for k, v in p.items() if k != "wav_path"} for p in PRESETS],
            "algorithms": ALGORITHMS, "rt60_levels": list(RT60_LEVELS.keys())}


@app.get("/api/upload-mic-geometry")
def upload_mic_geometry():
    return UPLOAD_MIC_GEOMETRY


@app.post("/api/run/preset")
def run_preset(req: PresetRunRequest):
    preset = PRESETS_BY_ID.get(req.preset_id)
    if preset is None:
        raise HTTPException(status_code=404, detail=f"Unknown preset_id '{req.preset_id}'. "
                                                      f"Valid ids: {list(PRESETS_BY_ID)}")
    if req.algorithm not in ALGORITHMS:
        raise HTTPException(status_code=400, detail=f"Unknown algorithm '{req.algorithm}'. "
                                                      f"Valid: {ALGORITHMS}")
    if req.rt60_level not in RT60_LEVELS:
        raise HTTPException(status_code=400, detail=f"Unknown rt60_level '{req.rt60_level}'. "
                                                      f"Valid: {list(RT60_LEVELS)}")

    report = run_doa_from_source_file(
        preset["wav_path"], preset["true_source_m"], algo_name=req.algorithm,
        rt60_level=req.rt60_level, freq_range=preset["freq_range"], n_grid=req.n_grid,
    )
    report["preset_id"] = req.preset_id
    report["preset_label"] = preset["label"]
    return report


@app.post("/api/run/upload")
def run_upload(
    file: UploadFile = File(...),
    algorithm: str = Form("SRP"),
    room_dim: str = Form(None),  # optional "x,y,z" in meters
    true_source_m: str = Form(None),  # optional "x,y,z" if visitor knows the true position
):
    if algorithm not in ALGORITHMS:
        raise HTTPException(status_code=400, detail=f"Unknown algorithm '{algorithm}'. Valid: {ALGORITHMS}")

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=400,
                            detail=f"Unsupported file type '{ext}'. Supported: {SUPPORTED_EXTENSIONS}")

    room = [float(x) for x in room_dim.split(",")] if room_dim else DEFAULT_ROOM_DIM
    true_pos = [float(x) for x in true_source_m.split(",")] if true_source_m else None

    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        report = run_doa_from_multichannel_upload(
            tmp_path, UPLOAD_MIC_GEOMETRY["positions_m"], room_dim=room,
            algo_name=algorithm, freq_range=[300, 3400], n_grid=4000,
            true_source_position=true_pos,
        )
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"DOA pipeline failed: {exc}")
    finally:
        os.unlink(tmp_path)

    return report


@app.get("/api/health")
def health():
    return {"status": "ok"}
