"""Unit tests for src.audio_source (generic .wav/.flac loading)."""

import os
import tempfile

import numpy as np
import pytest
import soundfile as sf

from src.audio_source import (
    load_source_signal,
    load_multichannel_recording,
    build_mic_data_dict_from_arrays,
)


def _write_wav(path, data, sr=16000):
    sf.write(path, data, sr)


def test_load_source_signal_mono_wav():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "mono.wav")
        signal = np.sin(np.linspace(0, 10, 1600)).astype(np.float32)
        _write_wav(path, signal)

        sr, loaded = load_source_signal(path)
        assert sr == 16000
        assert loaded.ndim == 1
        assert loaded.shape[0] == 1600


def test_load_source_signal_multichannel_mixed_to_mono():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "stereo.wav")
        left = np.ones(800, dtype=np.float32) * 0.5
        right = np.ones(800, dtype=np.float32) * -0.5
        stereo = np.stack([left, right], axis=1)
        _write_wav(path, stereo)

        sr, loaded = load_source_signal(path, mono=True)
        assert loaded.ndim == 1
        # Averaging +0.5 and -0.5 should be ~0
        assert np.allclose(loaded, 0.0, atol=1e-6)


def test_load_source_signal_flac():
    with tempfile.TemporaryDirectory() as tmp:
        wav_path = os.path.join(tmp, "s.wav")
        flac_path = os.path.join(tmp, "s.flac")
        signal = np.sin(np.linspace(0, 20, 3200)).astype(np.float32) * 0.3
        _write_wav(wav_path, signal)
        data, sr = sf.read(wav_path)
        sf.write(flac_path, data, sr)

        sr2, loaded = load_source_signal(flac_path)
        assert sr2 == sr
        assert loaded.shape[0] == 3200


def test_load_source_signal_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        load_source_signal("/tmp/does_not_exist_at_all_123.wav")


def test_load_source_signal_bad_extension_raises():
    with pytest.raises(ValueError):
        load_source_signal("/tmp/whatever.mp3")


def test_load_source_signal_resamples():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "mono.wav")
        signal = np.sin(np.linspace(0, 10, 1600)).astype(np.float32)
        _write_wav(path, signal, sr=16000)

        sr, loaded = load_source_signal(path, target_sr=8000)
        assert sr == 8000
        # resampling halves the sample count (approximately)
        assert 750 < loaded.shape[0] < 850


def test_load_multichannel_recording_returns_channels_first():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "multi.wav")
        n_channels, n_samples = 4, 500
        data = np.random.default_rng(0).normal(size=(n_samples, n_channels)).astype(np.float32) * 0.1
        _write_wav(path, data)

        sr, channels = load_multichannel_recording(path)
        assert channels.shape == (n_channels, n_samples)


def test_load_multichannel_recording_rejects_mono():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "mono.wav")
        _write_wav(path, np.zeros(500, dtype=np.float32))
        with pytest.raises(ValueError):
            load_multichannel_recording(path)


def test_build_mic_data_dict_from_arrays_matches_shapes():
    channels = np.zeros((3, 100))
    locations = [[0, 0, 0], [1, 0, 0], [0, 1, 0]]
    result = build_mic_data_dict_from_arrays(channels, locations)
    assert set(result.keys()) == {"mic1", "mic2", "mic3"}
    assert result["mic2"][0] == [1, 0, 0]
    assert result["mic2"][1].shape == (100,)


def test_build_mic_data_dict_from_arrays_mismatch_raises():
    channels = np.zeros((2, 100))
    locations = [[0, 0, 0]]
    with pytest.raises(ValueError):
        build_mic_data_dict_from_arrays(channels, locations)
