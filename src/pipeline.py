#!/usr/bin/env python
"""High-level, single-entry-point pipeline: audio (preset simulation or a
real multi-channel upload) -> DOA estimation -> ray triangulation ->
a single report dict.

This module exists so `experiments/real_world_benchmark.py` (Part 1) and
the demo backend (`api/app.py`, Part 2) share exactly one wiring of
`ExperimentalMicData` / `PrepareData` / `SoundSourceLocation` /
`src.triangulation`, instead of each re-implementing it slightly
differently.

Two entry points:

  run_doa_from_source_file()   -- "preset" mode: a real (or synthetic)
      single-channel source audio file is emitted by a simulated point
      source at a KNOWN position inside a pyroomacoustics room; ground
      truth is therefore exact by construction. Used for the heart-sound
      proxy signal and the LibriSpeech/ESC-50 real-world presets.

  run_doa_from_multichannel_upload() -- "upload" mode: an already
      multi-channel recording (one real captured signal per channel,
      e.g. a user's own array recording) is used directly, with no room
      simulation. True source position is optional (unknown for a real
      upload unless the user also supplies it).

Both return the same report shape (see `_run_doa_and_report`) so the
demo's frontend can render either case identically.
"""

import os
import time

import numpy as np

from src.experiment import ExperimentalMicData
from src.paths import get_generated_dir
from src.preprocess import PrepareData
from src.sound_source_localization import SoundSourceLocation
from src.audio_source import load_multichannel_recording, build_mic_data_dict_from_arrays
from src.triangulation import (
    spherical_to_cartesian,
    triangulate_rays,
    huber_weighted_triangulate,
    ransac_triangulate,
    perpendicular_residuals,
    pairwise_ray_intersections,
)

DEFAULT_ROOM_DIM = [4.0, 3.0, 2.5]

# Small (~15 cm), non-planar tetrahedral cluster aperture -- see README
# "Why microphone clusters must be small AND non-planar" for why this
# specific shape/size was chosen.
_APERTURE = 0.15
TETRA_POSITIONS = [
    [0.00, 0.00, 0.00], [_APERTURE, 0.00, 0.00],
    [0.00, _APERTURE, 0.00],
    [_APERTURE / 2, _APERTURE / 2, _APERTURE],
]
DEFAULT_CLUSTER_CENTERS = [
    [0.4, 0.4, 0.4], [0.4, 2.6, 1.3], [3.6, 0.4, 1.3], [3.6, 2.6, 2.1],
]

# Three named reverberation conditions used throughout Part 1 and the
# demo. `absorption`/`max_order` are pyroomacoustics ShoeBox parameters;
# the ACTUAL resulting RT60 (reported alongside every experiment result)
# is measured from the simulated room's own impulse response via
# `pyroomacoustics.Room.measure_rt60()`, not assumed from these inputs.
# These exact (absorption, max_order) pairs intentionally match
# validation/run_validation.py's three named conditions ("near-anechoic
# best case", "lightly-furnished room", "heavily reverberant room"), so
# Part 1's real-world-vs-heart-proxy comparison is apples-to-apples with
# the existing README numbers rather than a differently-tuned rebuild.
RT60_LEVELS = {
    "low": dict(absorption=0.99, max_order=0),
    "medium": dict(absorption=0.97, max_order=1),
    "high": dict(absorption=0.25, max_order=10),
}

ALGORITHMS = ["SRP", "MUSIC", "TOPS", "CSSM", "WAVES"]


def default_mic_clusters(cluster_centers=None):
    centers = cluster_centers or DEFAULT_CLUSTER_CENTERS
    return [{"center": c, "positions": TETRA_POSITIONS} for c in centers]


def measure_room_rt60(room_dim, absorption, max_order, fs=16000):
    """Measures the actual RT60 (seconds) of a room with the given
       absorption/max_order, via pyroomacoustics's own impulse-response
       based estimator -- an honest, measured number rather than a
       theoretical Sabine-formula guess."""
    import pyroomacoustics as pra

    room = pra.ShoeBox(np.array(room_dim, dtype=float), fs=fs,
                        materials=pra.Material(absorption), max_order=max_order)
    room.add_source([room_dim[0] / 2, room_dim[1] / 2, room_dim[2] / 2])
    room.add_microphone_array(
        pra.MicrophoneArray(np.array([[0.5], [0.5], [0.5]]), fs=fs))
    room.compute_rir()
    try:
        rt60 = room.measure_rt60()[0, 0]
        return float(rt60) if np.isfinite(rt60) else None
    except Exception:
        return None


def _rays_for_mic_groups(estimator, sound_data, mic_groups):
    """Computes one (origin, direction) ray per mic group, sequentially
       (no multiprocessing -- deliberate for the demo/API context: a
       single web request handling 4 small clusters is fast enough
       single-threaded, and avoids spawning worker processes inside a
       long-lived server process)."""
    origins, directions = [], []
    for group in mic_groups:
        origin, direction = estimator.get_estimates(sound_data, *group)
        origins.append(origin)
        directions.append(direction)
    return np.array(origins), np.array(directions)


def _triangulate(origins, directions, method="huber"):
    if method == "ls":
        estimate = triangulate_rays(origins, directions)
        weights = np.ones(len(origins))
    elif method == "ransac":
        estimate, inlier_mask = ransac_triangulate(
            origins, directions, min_samples=min(3, len(origins)),
            residual_threshold=0.05, max_trials=500)
        weights = inlier_mask.astype(float)
    else:
        estimate, weights = huber_weighted_triangulate(origins, directions)
    return estimate, weights


def _angle_from_reference(point, reference):
    """Azimuth/colatitude (degrees) of `point` as seen from `reference`,
       using the same convention as `src.triangulation.spherical_to_cartesian`
       (colatitude from +z, azimuth from +x toward +y)."""
    diff = np.asarray(point, dtype=float) - np.asarray(reference, dtype=float)
    azimuth = np.degrees(np.arctan2(diff[1], diff[0]))
    colatitude = np.degrees(np.arctan2(np.hypot(diff[0], diff[1]), diff[2]))
    return float(azimuth), float(colatitude)


def _run_doa_and_report(sound_data, mic_groups, room_dim, true_source_position,
                         algo_name, freq_range, n_grid, triangulation_method,
                         sampling_rate=16000):
    center_of_room = np.array(room_dim, dtype=float) / 2

    estimator = SoundSourceLocation(
        algo_name, number_of_mic_splits=max(1, len(mic_groups)),
        sampling_rate=sampling_rate, n_grid=n_grid,
        x_dim_max=room_dim[0], y_dim_max=room_dim[1], z_dim_max=room_dim[2],
        freq_range=freq_range, triangulation_method=triangulation_method,
    )

    t0 = time.time()
    origins_centered, directions = _rays_for_mic_groups(estimator, sound_data, mic_groups)

    # A single mic cluster/array produces exactly one ray: a bearing
    # (azimuth/colatitude) from that array, but NOT a 3-D position fix
    # -- triangulation needs >= 2 spatially-separated rays to intersect.
    # This is a real, physical limitation of DOA-only localization (see
    # README "Why microphone clusters must be small AND non-planar"),
    # not a bug: handle it explicitly rather than letting the
    # triangulation call raise, so the demo can show "direction only"
    # for a single-array upload instead of crashing.
    position_available = len(mic_groups) >= 2
    if position_available:
        estimate_centered, weights = _triangulate(origins_centered, directions, triangulation_method)
        residuals = perpendicular_residuals(estimate_centered, origins_centered, directions)
        pairwise_points_centered = pairwise_ray_intersections(origins_centered, directions)
    else:
        estimate_centered = origins_centered[0] + directions[0]  # 1 m along the bearing, for display only
        weights = np.ones(1)
        residuals = np.zeros(1)
        pairwise_points_centered = np.empty((0, 3))
    elapsed_s = time.time() - t0

    estimate_abs = center_of_room + estimate_centered
    origins_abs = center_of_room[None, :] + origins_centered

    pairwise_points_abs = (center_of_room[None, :] + pairwise_points_centered
                            if len(pairwise_points_centered) else pairwise_points_centered)

    # A common reference point (mean of cluster centers, absolute room
    # coordinates) to compare "true angle" vs "estimated angle" from the
    # SAME vantage point -- position error (meters) and angle error
    # (degrees) are reported as two distinct, complementary metrics.
    reference_point = origins_abs.mean(axis=0)
    est_azimuth, est_colatitude = _angle_from_reference(
        estimate_abs if position_available else origins_abs[0] + directions[0],
        reference_point)

    report = {
        "algorithm": algo_name,
        "position_available": position_available,
        "estimate_m": estimate_abs.tolist() if position_available else None,
        "reference_point_m": reference_point.tolist(),
        "estimated_azimuth_deg": est_azimuth,
        "estimated_colatitude_deg": est_colatitude,
        "elapsed_s": elapsed_s,
        "n_rays": len(mic_groups),
        "mean_ray_residual_m": float(np.mean(residuals)),
        "ray_weights": weights.tolist(),
        "rays": [
            {"origin_m": origins_abs[i].tolist(), "direction": directions[i].tolist(),
             "weight": float(weights[i]), "residual_m": float(residuals[i])}
            for i in range(len(mic_groups))
        ],
        "pairwise_intersection_points_m": pairwise_points_abs.tolist() if len(pairwise_points_abs) else [],
        "room_dim_m": list(room_dim),
    }
    if not position_available:
        report["note"] = (
            "Only one microphone cluster/array was supplied, so this is a "
            "single DOA bearing (azimuth/colatitude), not a triangulated 3-D "
            "position -- at least 2 spatially-separated clusters are needed "
            "to intersect rays into a position fix."
        )

    if true_source_position is not None:
        true_abs = np.asarray(true_source_position, dtype=float)
        true_azimuth, true_colatitude = _angle_from_reference(true_abs, reference_point)
        report["true_source_m"] = true_abs.tolist()
        report["true_azimuth_deg"] = true_azimuth
        report["true_colatitude_deg"] = true_colatitude
        report["error_m"] = (float(np.linalg.norm(estimate_abs - true_abs))
                              if position_available else None)
        report["angle_error_deg"] = float(np.hypot(
            _angular_diff(est_azimuth, true_azimuth), est_colatitude - true_colatitude))

    return report


def _angular_diff(a, b):
    """Smallest signed difference between two angles in degrees, wrapped to [-180, 180]."""
    d = (a - b + 180) % 360 - 180
    return d


def run_doa_from_source_file(source_wav_path, source_position, algo_name="SRP",
                              rt60_level="medium", room_dim=None, freq_range=None,
                              n_grid=4000, triangulation_method="huber",
                              cluster_centers=None):
    """"Preset" mode: simulate a room, emit `source_wav_path` from
       `source_position`, and run one DOA algorithm + triangulation.

       Returns a report dict (see `_run_doa_and_report`), plus
       `rt60_config` (the absorption/max_order used) and `rt60_s`
       (the room's actually-measured RT60, seconds).
    """
    room_dim = room_dim or DEFAULT_ROOM_DIM
    rt60_cfg = RT60_LEVELS[rt60_level]
    mic_clusters = default_mic_clusters(cluster_centers)

    # APP_DATA_DIR-derived directory for the deployed app (see src/paths.py);
    # falls back to a local ./app_data/generated directory when APP_DATA_DIR
    # is unset (e.g. plain local development). This scratch .mat file is
    # read back once (below, via PrepareData) within this same function
    # call and is not needed afterward -- it is not durable application data.
    (distance, true_azimuth_local, true_colatitude_local), out_file, converted_mics, \
        sample_rate, mic_groups = ExperimentalMicData(
            source_wav_path, number_of_mics=1, room_dim=room_dim,
            source_dim=source_position, mic_location=[0.0, 0.0, 0.0],
            mic_clusters=mic_clusters,
            absorption=rt60_cfg["absorption"], max_order=rt60_cfg["max_order"],
            output_dir=get_generated_dir(),
        ).run(plot=False)

    data = next(PrepareData(out_file, *converted_mics).load_file())

    # Scratch file is fully consumed above; remove it immediately rather
    # than letting per-request .mat files accumulate under APP_DATA_DIR.
    try:
        os.remove(out_file)
    except OSError:
        pass

    report = _run_doa_and_report(
        data, mic_groups, room_dim, source_position, algo_name,
        freq_range, n_grid, triangulation_method, sampling_rate=sample_rate)

    report["rt60_level"] = rt60_level
    report["rt60_config"] = rt60_cfg
    report["rt60_s"] = measure_room_rt60(room_dim, rt60_cfg["absorption"],
                                          rt60_cfg["max_order"], fs=sample_rate)
    return report


def run_doa_from_multichannel_upload(upload_wav_path, mic_locations, room_dim,
                                      algo_name="SRP", freq_range=None, n_grid=4000,
                                      triangulation_method="huber",
                                      true_source_position=None, mic_groups=None):
    """"Upload" mode: an already multi-channel recording, no simulation."""
    sample_rate, channels = load_multichannel_recording(upload_wav_path)
    data = build_mic_data_dict_from_arrays(channels, mic_locations)
    if mic_groups is None:
        n = len(mic_locations)
        mic_groups = [tuple(f"mic{i + 1}" for i in range(n))]

    return _run_doa_and_report(
        data, mic_groups, room_dim, true_source_position, algo_name,
        freq_range, n_grid, triangulation_method, sampling_rate=sample_rate)
