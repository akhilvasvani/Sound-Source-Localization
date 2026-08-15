"""Smoke tests for the FastAPI demo backend (api/app.py), using FastAPI's
TestClient (no real server/socket needed). These are intentionally light
-- the real DOA/triangulation logic is already covered by
test_pipeline.py; these tests just confirm the API wiring (routes,
request/response shapes, error handling) works.
"""

import io

import numpy as np
import pytest
import soundfile as sf
from fastapi.testclient import TestClient

from api.app import app

client = TestClient(app)


def test_health():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_list_presets():
    resp = client.get("/api/presets")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["presets"]) == 3
    ids = {p["id"] for p in body["presets"]}
    assert {"librispeech_0", "librispeech_1", "esc50_rain"} == ids
    assert "SRP" in body["algorithms"]
    assert "medium" in body["rt60_levels"]


def test_upload_mic_geometry():
    resp = client.get("/api/upload-mic-geometry")
    assert resp.status_code == 200
    assert len(resp.json()["positions_m"]) == 4


def test_run_preset_unknown_id_returns_404():
    resp = client.post("/api/run/preset", json={"preset_id": "does_not_exist"})
    assert resp.status_code == 404


def test_run_preset_bad_algorithm_returns_400():
    resp = client.post("/api/run/preset", json={"preset_id": "librispeech_0", "algorithm": "NOT_REAL"})
    assert resp.status_code == 400


def test_run_preset_librispeech_end_to_end():
    resp = client.post(
        "/api/run/preset",
        json={"preset_id": "librispeech_0", "algorithm": "SRP", "rt60_level": "low", "n_grid": 500},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["position_available"] is True
    assert body["preset_id"] == "librispeech_0"
    assert body["error_m"] >= 0.0
    assert len(body["rays"]) == 4


def test_run_upload_single_cluster_bearing_only():
    rng = np.random.default_rng(1)
    data = rng.normal(scale=0.1, size=(8000, 4)).astype(np.float32)
    buf = io.BytesIO()
    sf.write(buf, data, 16000, format="WAV")
    buf.seek(0)

    resp = client.post(
        "/api/run/upload",
        files={"file": ("test.wav", buf, "audio/wav")},
        data={"algorithm": "SRP", "true_source_m": "3.0,1.0,1.7"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["position_available"] is False
    assert body["estimate_m"] is None
    assert "note" in body


def test_run_upload_rejects_unsupported_extension():
    resp = client.post(
        "/api/run/upload",
        files={"file": ("test.mp3", io.BytesIO(b"not audio"), "audio/mpeg")},
        data={"algorithm": "SRP"},
    )
    assert resp.status_code == 400
