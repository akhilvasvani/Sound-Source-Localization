"""Tests for the `mic_clusters` (non-planar, 'positions'-based) microphone
cluster support added to `ExperimentalMicData` -- new code from this fix
with no prior test coverage.
"""
import os
import tempfile
import unittest

import numpy as np
from scipy.io import wavfile

from src.experiment import ExperimentalMicData


def _write_tiny_wav(path, duration_s=0.1, sample_rate=16000):
    rng = np.random.default_rng(0)
    signal = rng.normal(scale=0.1, size=int(duration_s * sample_rate))
    wavfile.write(path, sample_rate,
                  np.clip(signal * 32767, -32768, 32767).astype(np.int16))


class MicClustersPositionsTestCase(unittest.TestCase):
    """Tests the 'positions' (explicit, non-planar) cluster spec."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.wav_path = os.path.join(self.tmpdir.name, "tiny.wav")
        _write_tiny_wav(self.wav_path)
        self.room_dim = [4.0, 3.0, 2.5]
        self.source_dim = [2.0, 1.5, 1.0]

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_builds_one_group_per_cluster_with_correct_mic_counts(self):
        tetra = [[0, 0, 0], [0.04, 0, 0], [0, 0.04, 0], [0.02, 0.02, 0.04]]
        mic_clusters = [
            {'center': [0.5, 0.5, 0.5], 'positions': tetra},
            {'center': [3.5, 2.5, 2.0], 'positions': tetra},
        ]
        exp = ExperimentalMicData(self.wav_path, number_of_mics=1,
                                  room_dim=self.room_dim,
                                  source_dim=self.source_dim,
                                  mic_location=[0.0, 0.0, 0.0],
                                  mic_clusters=mic_clusters)

        # One mic_group per cluster, 4 mics each, sequentially numbered.
        self.assertEqual(exp.mic_group_names,
                         [('mic1', 'mic2', 'mic3', 'mic4'),
                          ('mic5', 'mic6', 'mic7', 'mic8')])
        self.assertEqual(exp.number_of_mics, 8)
        self.assertEqual(exp.mics.shape, (3, 8))

    def test_non_planar_cluster_has_more_than_one_unique_z(self):
        # The whole point of 'positions' over the legacy CustomMicrophoneSetUp
        # layouts is that a single cluster's own mics are NOT coplanar, so it
        # can resolve elevation without mixing in another, far-away cluster.
        tetra = [[0, 0, 0], [0.04, 0, 0], [0, 0.04, 0], [0.02, 0.02, 0.04]]
        mic_clusters = [{'center': [1.0, 1.0, 1.0], 'positions': tetra}]
        exp = ExperimentalMicData(self.wav_path, number_of_mics=1,
                                  room_dim=self.room_dim,
                                  source_dim=self.source_dim,
                                  mic_location=[0.0, 0.0, 0.0],
                                  mic_clusters=mic_clusters)
        z_values = exp.mics[2]
        self.assertGreater(len(set(np.round(z_values, 6))), 1)

    def test_out_of_bounds_cluster_raises_value_error(self):
        # A cluster placed right at a room wall, with an offset that pushes
        # one mic past the wall, must fail loudly instead of silently
        # producing an invalid microphone position (see tools/utilities.py's
        # analogous CustomMicrophoneSetUp bounds check).
        tetra = [[0, 0, 0], [0.04, 0, 0], [0, 0.04, 0], [0.02, 0.02, 0.04]]
        mic_clusters = [{'center': [3.99, 0.01, 0.01], 'positions': tetra}]
        with self.assertRaises(ValueError):
            ExperimentalMicData(self.wav_path, number_of_mics=1,
                               room_dim=self.room_dim,
                               source_dim=self.source_dim,
                               mic_location=[0.0, 0.0, 0.0],
                               mic_clusters=mic_clusters)


if __name__ == '__main__':
    unittest.main()
