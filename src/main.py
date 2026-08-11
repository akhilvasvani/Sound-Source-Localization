# !/usr/bin/env python
"""This is the main driver file: it builds a small reverberant room in
pyroomacoustics, places a sound source and a spread-out microphone array,
estimates the source's azimuth/colatitude from several microphone triplets,
triangulates those direction rays into a single 3-D estimate, and reports
the error (in meters) against the known, simulated source location.

Note: the original version of this script depended on an external CMU_ARCTIC
dataset file at a hardcoded absolute path
(`/home/akhil/Sound-Source-Localization/data/...`) that is not included in
this repository and does not exist on other machines. This version generates
a short synthetic broadband signal on the fly instead, so the example is
fully self-contained and reproducible.
"""

import os
import tempfile

import numpy as np
from scipy.io import wavfile

from src.experiment import ExperimentalMicData
from src.preprocess import PrepareData
from src.sound_source_localization import SoundSourceLocation
from src.determine_source import DetermineSourceLocation


def _make_synthetic_signal_wav(path, duration_s=1.5, sample_rate=16000, seed=0):
    """Writes a short broadband (white noise) signal to `path` as a 16-bit
       PCM wav file, standing in for the missing CMU_ARCTIC dataset."""
    rng = np.random.default_rng(seed)
    signal = rng.normal(scale=0.3, size=int(duration_s * sample_rate))
    signal_int16 = np.clip(signal * 32767, -32768, 32767).astype(np.int16)
    wavfile.write(path, sample_rate, signal_int16)


def main(absorption=0.99, max_order=0, duration_s=1.5, seed=0):
    """Runs the full synthetic-audio pipeline once and prints the real,
       measured position error against the known source location.

       `absorption`/`max_order` control how reverberant the simulated room
       is (pyroomacoustics ShoeBox parameters: absorption close to 1.0 and
       max_order=0 approximate an anechoic, direct-path-only room; lower
       absorption and higher max_order add more/stronger echoes). The
       defaults here (absorption=0.99, max_order=0) reproduce the
       best-case, low-reverberation scenario documented in the README,
       which empirically gets closest to the <1 cm target. Realistic,
       more reverberant rooms (e.g. absorption=0.25, max_order=10) give
       much larger, honestly-worse errors -- see README "Accuracy" section
       and `validation/run_validation.py` for a side-by-side comparison.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        sample_filename = os.path.join(tmpdir, "synthetic_source.wav")
        _make_synthetic_signal_wav(sample_filename, duration_s=duration_s, seed=seed)

        method_name = 'SRP'

        room_dimensions = [4.0, 3.0, 2.5]
        source_location = [3.0, 1.0, 1.7]

        # Four small (compact, ~5 cm aperture) microphone clusters spread
        # to different corners AND heights of the room. Two design points
        # matter here, both confirmed empirically while building this fix:
        #
        # 1) A cluster whose own mics are all at the SAME height cannot
        #    resolve whether the source is above or below its plane --
        #    colatitude theta and (180-theta) give identical inter-mic
        #    delays for a purely planar array. Each cluster below uses
        #    explicit non-planar `positions` (a small tetrahedron: 3 base
        #    mics + 1 raised apex) so it can disambiguate elevation using
        #    only its own, tightly-spaced mics.
        # 2) DOA/SRP estimation over mics that are METERS apart (i.e.
        #    mixing mics from different, far-apart clusters into one DOA
        #    computation) suffers severe spatial aliasing once inter-mic
        #    spacing approaches half a wavelength of the analyzed
        #    frequency band, producing near-random angle estimates. Each
        #    cluster's own DOA is therefore computed using ONLY its own 4
        #    (few-cm-spaced) mics -- see `mic_groups` below -- and
        #    triangulation combines the resulting one-ray-per-cluster
        #    bearings, which is exactly the well-conditioned, spatially
        #    diverse geometry ray triangulation needs.
        # 15 cm tetrahedron aperture, tuned empirically (see
        # validation/run_validation.py) as the best tradeoff found between
        # angular resolution (bigger aperture = finer resolution) and
        # spatial aliasing (bigger aperture = more phase wrap at a given
        # frequency). Its worst-case pairwise spacing (~0.212 m, between
        # the two base corners) is slightly ABOVE the strict
        # half-wavelength anti-aliasing limit at 1000 Hz (343/(2*1000) =
        # 0.1715 m); in practice the SRP grid search tolerates this well
        # for a handful of mic pairs and this config outperformed smaller,
        # fully alias-safe apertures in direct measurement -- a real,
        # imperfect engineering tradeoff, not a hard guarantee.
        aperture = 0.15
        tetra_positions = [[0.00, 0.00, 0.00], [aperture, 0.00, 0.00],
                           [0.00, aperture, 0.00],
                           [aperture / 2, aperture / 2, aperture]]
        mic_clusters = [
            {'center': [0.4, 0.4, 0.4], 'positions': tetra_positions},
            {'center': [0.4, 2.6, 1.3], 'positions': tetra_positions},
            {'center': [3.6, 0.4, 1.3], 'positions': tetra_positions},
            {'center': [3.6, 2.6, 2.1], 'positions': tetra_positions},
        ]

        os.makedirs("output", exist_ok=True)

        (distance, true_azimuth, true_colatitude), output_file_name, \
        converted_mic_locations, sample_rate, mic_groups = ExperimentalMicData(
            sample_filename,
            number_of_mics=1,
            room_dim=room_dimensions,
            source_dim=source_location,
            mic_location=[0.0, 0.0, 0.0],
            mic_clusters=mic_clusters,
            absorption=absorption,
            max_order=max_order).run(plot=False)

        print(f"True distance (centroid-to-source): {distance:.4f} m, "
              f"true azimuth: {true_azimuth:.2f} deg, "
              f"true colatitude: {true_colatitude:.2f} deg")

        test_data = PrepareData(output_file_name, *converted_mic_locations).load_file()
        sample_mic_signal_loc_dict = next(test_data)

        # freq_range overridden from the [0, 250] Hz heart-sound default to
        # match this demo's broadband synthetic noise signal, and kept
        # within the spatial-aliasing-safe band noted above for the 15 cm
        # cluster aperture (empirically the best-performing band found
        # while tuning this pipeline -- see validation/run_validation.py).
        estimator = SoundSourceLocation(method_name,
                                        number_of_mic_splits=4,
                                        s1_bool=None,
                                        n_grid=8000,
                                        x_dim_max=room_dimensions[0],
                                        y_dim_max=room_dimensions[1],
                                        z_dim_max=room_dimensions[2],
                                        freq_range=[300, 1000],
                                        triangulation_method='huber')
        estimate, diagnostics = next(estimator.run_estimates(sample_mic_signal_loc_dict,
                                                             mic_groups=mic_groups))

        result = DetermineSourceLocation(method_name, "synthetic_demo",
                                         estimate, diagnostics,
                                         *converted_mic_locations,
                                         room_dim=room_dimensions,
                                         true_source=source_location).sprint(
                                             save_plot=True, write_to_file=True)
        return result


if __name__ == '__main__':
    main()
