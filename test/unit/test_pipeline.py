"""Unit tests for src.pipeline -- the shared preset-simulation /
multichannel-upload -> DOA -> triangulation -> report wiring used by
both experiments/real_world_benchmark.py and the demo API.
"""

import os
import numpy as np
import pytest
import soundfile as sf

from src.pipeline import (
    default_mic_clusters,
    measure_room_rt60,
    run_doa_from_multichannel_upload,
    run_doa_from_source_file,
    DEFAULT_CLUSTER_CENTERS,
    TETRA_POSITIONS,
    RT60_LEVELS,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LIBRISPEECH_SAMPLE = os.path.join(REPO_ROOT, "data", "librispeech_samples", "sample_0.wav")


def test_default_mic_clusters_shape():
    clusters = default_mic_clusters()
    assert len(clusters) == len(DEFAULT_CLUSTER_CENTERS)
    for cluster, center in zip(clusters, DEFAULT_CLUSTER_CENTERS):
        assert cluster["center"] == center
        assert cluster["positions"] == TETRA_POSITIONS


def test_rt60_levels_have_expected_keys():
    assert set(RT60_LEVELS) == {"low", "medium", "high"}
    for cfg in RT60_LEVELS.values():
        assert "absorption" in cfg and "max_order" in cfg


def test_measure_room_rt60_low_is_smaller_than_high():
    rt60_low = measure_room_rt60([4.0, 3.0, 2.5], **RT60_LEVELS["low"])
    rt60_high = measure_room_rt60([4.0, 3.0, 2.5], **RT60_LEVELS["high"])
    assert rt60_low is not None and rt60_high is not None
    assert rt60_low < rt60_high


@pytest.mark.skipif(not os.path.exists(LIBRISPEECH_SAMPLE), reason="sample audio not present")
def test_run_doa_from_source_file_preset_returns_full_report():
    report = run_doa_from_source_file(
        LIBRISPEECH_SAMPLE, [3.0, 1.0, 1.7], algo_name="SRP", rt60_level="low",
        freq_range=[300, 3400], n_grid=500,
    )
    assert report["position_available"] is True
    assert report["algorithm"] == "SRP"
    assert len(report["estimate_m"]) == 3
    assert report["error_m"] >= 0.0
    assert report["angle_error_deg"] >= 0.0
    assert report["n_rays"] == 4
    assert len(report["rays"]) == 4
    # 4 rays -> 4*3/2 = 6 pairwise intersection points
    assert len(report["pairwise_intersection_points_m"]) == 6
    assert report["rt60_s"] is not None
    assert report["rt60_level"] == "low"


def test_run_doa_from_multichannel_upload_single_cluster_reports_bearing_only(tmp_path):
    path = tmp_path / "multi.wav"
    rng = np.random.default_rng(0)
    data = rng.normal(scale=0.1, size=(8000, 4)).astype(np.float32)
    sf.write(str(path), data, 16000)

    mic_locs = [[0.0, 0.0, 0.0], [0.15, 0.0, 0.0], [0.0, 0.15, 0.0], [0.075, 0.075, 0.15]]
    report = run_doa_from_multichannel_upload(
        str(path), mic_locs, room_dim=[4.0, 3.0, 2.5], algo_name="SRP",
        freq_range=[300, 3400], n_grid=500, true_source_position=[3.0, 1.0, 1.7],
    )

    assert report["position_available"] is False
    assert report["estimate_m"] is None
    assert report["error_m"] is None
    assert "note" in report
    assert report["n_rays"] == 1
    # angle error is still reported even without a 3-D position fix
    assert report["angle_error_deg"] >= 0.0
