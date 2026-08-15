#!/usr/bin/env python
"""Shared application layer between the Streamlit demo (demo/app.py, the
only process that actually runs in production) and the optional FastAPI
dev/test wrapper (api/app.py, not deployed -- see README.md's
"Architecture" section for why).

Both previously duplicated this preset catalog and request-validation
logic; it now lives in exactly one place so there is a single source of
truth for "what a preset run or an upload run means," regardless of
which caller (Streamlit process or FastAPI test client) invokes it.

Functions here raise plain Python exceptions (ValueError / KeyError /
FileNotFoundError) instead of framework-specific ones, so:
  - demo/app.py can catch them and render `st.error(...)`, and
  - api/app.py can catch them and translate to HTTPException.
"""

import os
import uuid

from src.audio_source import SUPPORTED_EXTENSIONS
from src.paths import REPO_ROOT, get_uploads_dir
from src.pipeline import (
    ALGORITHMS,
    DEFAULT_ROOM_DIM,
    RT60_LEVELS,
    TETRA_POSITIONS,
    run_doa_from_multichannel_upload,
    run_doa_from_source_file,
)

# --------------------------------------------------------------------------
# Preset catalog -- real-world audio examples (LibriSpeech speech,
# ESC-50 environmental sound). Ground truth source position is known
# exactly because these are room-simulated with a known source location.
# --------------------------------------------------------------------------
PRESETS = [
    {
        "id": "librispeech_0",
        "label": "Speech (LibriSpeech)",
        "description": "Real human speech, HuggingFace hf-internal-testing/librispeech_asr_dummy.",
        "wav_path": os.path.join(REPO_ROOT, "data", "librispeech_samples", "sample_0.wav"),
        "true_source_m": [1.0, 2.0, 0.6],
        "freq_range": [300, 3400],
    },
    {
        "id": "librispeech_1",
        "label": "Speech, second clip (LibriSpeech)",
        "description": "A second, different real speech clip from the same dataset.",
        "wav_path": os.path.join(REPO_ROOT, "data", "librispeech_samples", "sample_1.wav"),
        "true_source_m": [2.0, 1.5, 2.0],
        "freq_range": [300, 3400],
    },
    {
        "id": "esc50_rain",
        "label": "Rain (ESC-50)",
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


def list_presets():
    """Public catalog: presets (without internal wav_path), algorithms, RT60 levels."""
    return {
        "presets": [{k: v for k, v in p.items() if k != "wav_path"} for p in PRESETS],
        "algorithms": ALGORITHMS,
        "rt60_levels": list(RT60_LEVELS.keys()),
    }


def run_preset(preset_id, algorithm="SRP", rt60_level="medium", n_grid=4000):
    """Run the DOA pipeline on a built-in preset.

    Raises:
        KeyError: unknown preset_id, algorithm, or rt60_level.
    """
    preset = PRESETS_BY_ID.get(preset_id)
    if preset is None:
        raise KeyError(f"Unknown preset_id '{preset_id}'. Valid ids: {list(PRESETS_BY_ID)}")
    if algorithm not in ALGORITHMS:
        raise KeyError(f"Unknown algorithm '{algorithm}'. Valid: {ALGORITHMS}")
    if rt60_level not in RT60_LEVELS:
        raise KeyError(f"Unknown rt60_level '{rt60_level}'. Valid: {list(RT60_LEVELS)}")

    report = run_doa_from_source_file(
        preset["wav_path"], preset["true_source_m"], algo_name=algorithm,
        rt60_level=rt60_level, freq_range=preset["freq_range"], n_grid=n_grid,
    )
    report["preset_id"] = preset_id
    report["preset_label"] = preset["label"]
    return report


def run_upload(file_bytes, filename, algorithm="SRP", room_dim=None, true_source_m=None):
    """Run the DOA pipeline on an uploaded multi-channel recording.

    Args:
        file_bytes: raw bytes of the uploaded file.
        filename: original filename (used only to determine the extension).
        algorithm: DOA algorithm name.
        room_dim: optional [x, y, z] meters; defaults to DEFAULT_ROOM_DIM.
        true_source_m: optional [x, y, z] meters, if known.

    Raises:
        KeyError: unknown algorithm.
        ValueError: unsupported file extension.
    """
    if algorithm not in ALGORITHMS:
        raise KeyError(f"Unknown algorithm '{algorithm}'. Valid: {ALGORITHMS}")

    ext = os.path.splitext(filename or "")[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type '{ext}'. Supported: {SUPPORTED_EXTENSIONS}")

    room = room_dim or DEFAULT_ROOM_DIM

    # Staged under APP_DATA_DIR/uploads (see src/paths.py) rather than the
    # system temp dir, per the single-configurable-data-directory
    # requirement. Removed immediately after the pipeline consumes it --
    # this is transient per-request scratch data, not durable storage.
    tmp_path = os.path.join(get_uploads_dir(), f"upload_{uuid.uuid4().hex[:12]}{ext}")
    with open(tmp_path, "wb") as f:
        f.write(file_bytes)

    try:
        report = run_doa_from_multichannel_upload(
            tmp_path, UPLOAD_MIC_GEOMETRY["positions_m"], room_dim=room,
            algo_name=algorithm, freq_range=[300, 3400], n_grid=4000,
            true_source_position=true_source_m,
        )
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass

    return report
