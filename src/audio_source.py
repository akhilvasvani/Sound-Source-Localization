#!/usr/bin/env python
"""Generic audio-source loading for the DOA pipeline.

Historically, this project's only supported "input" format was the
project-internal .mat file written by `ExperimentalMicData` (a dict of
per-microphone signal arrays, produced by simulating a *known* source
signal in a pyroomacoustics room) and consumed by `src.preprocess.PrepareData`.
That .mat format is still fully supported (see `src/preprocess.py`,
untouched) -- it is how heart-sound (S1/S2) recordings were historically
fed into this pipeline, and it remains the default/legacy mode.

This module adds a second, generic entry point: loading an arbitrary
mono/multi-channel `.wav` or `.flac` *source* audio file (real-world
speech, environmental sound, or heart-sound audio if you have your own
recordings) to drive the SAME simulate -> DOA -> triangulate pipeline,
without requiring the caller to hand-roll a .mat file first.

Two distinct use cases are supported:

1. `load_source_signal()` -- load a single-channel (or mixed-down)
   "dry" source signal that will be *emitted* by a simulated point
   source in a pyroomacoustics room (`ExperimentalMicData`). This is
   the mode used for the real-world benchmark in
   `experiments/real_world_benchmark.py`: a real LibriSpeech/ESC-50
   recording stands in for the emitted signal, and pyroomacoustics
   simulates the room acoustics and array capture, so the ground-truth
   source position is exact by construction (see README for the
   tradeoff vs. using a real recorded multi-channel array corpus like
   LOCATA/DCASE SELD).

2. `load_multichannel_recording()` -- load an *already multi-channel*
   recording (one real microphone's real signal per channel), e.g. from
   a real array-recorded benchmark corpus (LOCATA, DCASE SELD) or a
   user's own multi-mic .wav upload in the demo. This bypasses
   `ExperimentalMicData` entirely (no simulation is needed -- the array
   already captured real acoustics) and hands the per-channel signals
   straight to the DOA/triangulation code via
   `build_mic_data_dict_from_arrays()`. This is the code path the demo
   backend (`api/`) uses for user-uploaded multi-channel files, and the
   path a future LOCATA/DCASE integration would use once that dataset's
   own mic-geometry metadata is parsed (see README "Known limitations").
"""

import os

import numpy as np
import soundfile as sf


SUPPORTED_EXTENSIONS = (".wav", ".flac")


def _validate_extension(filepath):
    ext = os.path.splitext(filepath)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Error. Unsupported audio file extension '{ext}' for "
            f"'{filepath}'. Supported: {SUPPORTED_EXTENSIONS}."
        )
    return ext


def load_source_signal(filepath, target_sr=None, mono=True):
    """Loads a generic .wav/.flac file as a single "dry" source signal.

    Args:
        filepath: path to a .wav or .flac file.
        target_sr: if given, resample to this rate (Hz). If None, the
            file's native rate is used as-is.
        mono: if True (default) and the file has multiple channels,
            mix down to mono by averaging channels (appropriate for a
            single point-source emission signal fed to
            `ExperimentalMicData.set_sound_source`). If False, returns
            the signal with its original channel layout.

    Returns:
        (sample_rate, signal): sample_rate is an int; signal is a 1-D
        (mono) or (n_samples, n_channels) float64 numpy array,
        normalized to roughly [-1, 1] (matching what
        `scipy.io.wavfile.read`-based code in this project already
        assumes for the values it multiplies into the room simulation).

    Raises:
        FileNotFoundError: if the file does not exist.
        ValueError: if the extension is not .wav/.flac, or the file is
            empty/unreadable as audio.
    """
    _validate_extension(filepath)
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"Error. Audio file not found: '{filepath}'.")

    try:
        data, sr = sf.read(filepath, always_2d=False)
    except Exception as exc:  # pragma: no cover - defensive, re-raised as ValueError
        raise ValueError(f"Error. Could not read audio file '{filepath}': {exc}") from exc

    data = np.asarray(data, dtype=np.float64)
    if data.size == 0:
        raise ValueError(f"Error. Audio file '{filepath}' contains no samples.")

    if data.ndim > 1 and mono:
        data = data.mean(axis=1)

    if target_sr is not None and target_sr != sr:
        data = _resample(data, sr, target_sr)
        sr = target_sr

    return sr, data


def load_multichannel_recording(filepath, target_sr=None):
    """Loads a real multi-channel recording (one real mic per channel).

    Unlike `load_source_signal`, this NEVER mixes channels down -- each
    channel is assumed to be one microphone's actual captured signal
    (e.g. from a real array-recorded benchmark corpus, or a user's own
    multi-mic upload), to be paired with known/assumed microphone
    positions and passed directly to
    `SoundSourceLocation.get_difference_of_arrivals` without any
    `ExperimentalMicData` room simulation.

    Args:
        filepath: path to a .wav or .flac file with N channels.
        target_sr: optional resample target rate (Hz).

    Returns:
        (sample_rate, channels): channels is a (n_channels, n_samples)
        float64 numpy array (one row per microphone channel).

    Raises:
        FileNotFoundError, ValueError: see `load_source_signal`.
        ValueError: if the file is mono (a multi-channel recording
            needs >= 2 channels to be useful for DOA).
    """
    sr, data = load_source_signal(filepath, target_sr=target_sr, mono=False)
    if data.ndim == 1:
        raise ValueError(
            f"Error. '{filepath}' is single-channel; a multi-channel DOA "
            "recording needs >= 2 microphone channels. Use "
            "load_source_signal() for single-channel source audio instead."
        )
    return sr, data.T  # (n_channels, n_samples)


def _resample(signal, orig_sr, target_sr):
    """Simple polyphase resampling via scipy, applied per-channel."""
    from scipy.signal import resample_poly
    from math import gcd

    g = gcd(int(orig_sr), int(target_sr))
    up, down = int(target_sr) // g, int(orig_sr) // g
    if signal.ndim == 1:
        return resample_poly(signal, up, down)
    return np.stack([resample_poly(signal[:, c], up, down)
                      for c in range(signal.shape[1])], axis=1)


def build_mic_data_dict_from_arrays(channels, mic_locations):
    """Builds the same {micN: (location, signal)} dict format that
       `src.preprocess.PrepareData.load_file()` yields, directly from
       in-memory arrays -- skipping the .mat save/load round trip.

       This is used by (a) the real-world benchmark, so a full
       simulate -> save .mat -> reload .mat cycle isn't needed just to
       reformat data pyroomacoustics already handed us in memory, and
       (b) the demo API's multi-channel-upload path.

       Args:
           channels: (n_mics, n_samples) array-like -- one row per
               microphone's signal.
           mic_locations: (n_mics, 3) array-like -- one
               [x, y, z] location per microphone, in the same
               room-centered coordinate convention used elsewhere in
               this project (see `ExperimentalMicData.run`'s
               `converted_mic_locations`).

       Returns:
           dict: {"mic1": (location_0, signal_0), "mic2": (...), ...}

       Raises:
           ValueError: if the mic/location counts don't match.
    """
    channels = np.asarray(channels, dtype=float)
    mic_locations = list(mic_locations)
    if channels.shape[0] != len(mic_locations):
        raise ValueError(
            "Error. Mismatch in length of microphone location list "
            f"({len(mic_locations)}) and number of signal channels "
            f"({channels.shape[0]})."
        )
    return {
        f"mic{i + 1}": (mic_locations[i], channels[i])
        for i in range(len(mic_locations))
    }
