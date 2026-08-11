# !/usr/bin/env python
"""In this script, SoundSourceLocation estimates a DOA (azimuth/colatitude)
angle for every microphone-triplet combination, converts each angle pair to
a 3-D ray, and triangulates all the rays into a single estimated sound
source location.

This replaces the original approach, which sampled ~500 candidate points
along a fixed 0-0.5 m radius sweep per ray and never reduced that raw point
cloud to a single estimate (no clustering/intersection step existed --
`use_kd_tree` built a tree and immediately returned None). See
`src/triangulation.py` for the actual ray-intersection math.
"""

from itertools import combinations

import numpy as np
import pyroomacoustics as pra

from tools.utilities import MultiProcessingWithReturnValue
from tools.validations import validate_difference_of_arrivals, \
    ValidateCentroid, validate_get_mic_with_sound_data, validate_splits,\
    validate_instance_type
from src.triangulation import (spherical_to_cartesian, triangulate_rays,
                               huber_weighted_triangulate, ransac_triangulate,
                               perpendicular_residuals)


class SoundSourceLocation:
    """SoundSourceLocation estimates the 3-D location of a sound source
       using a distance-of-arrival (DOA) method applied to every
       microphone-triplet combination, then triangulates the resulting
       rays into a single estimate.

    Attributes:
        algo_name: (string) specific distance of arrival (DOA) method,
                   one of pyroomacoustics's DOA algorithm names
                   (e.g. 'SRP', 'MUSIC', 'TOPS', 'CSSM', 'WAVES').
        num_sources: (integer) number of sources to find. Default is 1.
                     NOTE: only num_sources=1 is currently supported by the
                     triangulation step below; multi-source separation
                     would require clustering rays into per-source groups
                     first, which is out of scope for this fix.
        number_of_mic_splits: (integer) the number of splits for
                      multiprocessing. Default: 5
        sound_speed: (float) speed of sound in m/s used by the DOA solver.
                     Default: 343.0 (standard speed of sound in air at
                     ~20C). NOTE: the original code hardcoded this to 30,
                     which is neither air nor any other physically
                     meaningful medium's speed of sound, and silently
                     corrupted every angle estimate.
        mic_combinations_number: (integer) number of microphones per
                      DOA sub-array (a "triplet" by default -- 3).

        sampling_rate: (integer) specific sampling frequency.
                       Default is 16000 Hz
        fft_size: (integer) specific FFT size. Default is 256
        freq_range: (list) specific frequency range (Hz) to isolate for
                    the DOA search. Default [0, 250] targets the very low
                    frequency content of heart sounds (S1/S2), matching
                    this project's original use case -- override with a
                    range matching your actual signal's spectral content
                    for other use cases (e.g. [300, 3500] for speech/noise).
        n_grid: (integer) number of grid points pyroomacoustics searches
                over for the DOA estimate. Higher values give finer
                angular resolution at the cost of runtime. Default: 4000
                (the original default of 1000 corresponds to an average
                angular spacing of several degrees over the full sphere).
        triangulation_method: (string) one of 'ls' (ordinary least
                squares), 'huber' (Huber-loss IRLS, default -- robust to a
                modest fraction of noisy/reflected rays), or 'ransac'
                (most robust; use when many rays may be corrupted by
                reverberation).

        s1_bool: (boolean) indicates whether to find S1 or S2 sound source.
                  Default is True
        x_dim_max: (float) the maximum x dimension (in meters)
        y_dim_max: (float) the maximum y dimension (in meters)
        z_dim_max: (float) the maximum z dimension (in meters)
        transform: (boolean) whether to use the (deprecated) `pra.stft`
                    call instead of `pra.transform.stft.analysis`.
    """

    def __init__(self, algo_name, num_sources=1, number_of_mic_splits=5,
                 sampling_rate=16000, s1_bool=True, x_dim_max=0.34925,
                 y_dim_max=0.219964, z_dim_max=0.2413, transform=False,
                 sound_speed=343.0, freq_range=None, n_grid=4000,
                 triangulation_method='huber'):
        """Initializes SoundSourceLocation with algo_name, num_sources."""

        self.algo_name = algo_name
        self.num_sources = num_sources
        self.number_of_mic_splits = number_of_mic_splits

        # Bug fix: sound_speed used to be hardcoded to 30 (m/s), which is
        # not the speed of sound in any common medium and corrupted every
        # DOA angle estimate. Default is now air's actual speed of sound
        # and is configurable to stay consistent with the room's
        # simulated propagation speed.
        self.sound_speed = sound_speed
        self.mic_combinations_number = 3

        self.sampling_rate = sampling_rate
        self.fft_size = 256
        self.freq_range = freq_range if freq_range is not None else [0, 250]
        self.n_grid = n_grid
        self.triangulation_method = triangulation_method

        self.s1_bool = s1_bool

        self.x_dim_max = x_dim_max
        self.y_dim_max = y_dim_max
        self.z_dim_max = z_dim_max

        self.transform = transform

        # Diagnostics from the most recent triangulation, populated by
        # process_potential_estimates(): per-ray residuals and (for
        # RANSAC) the inlier mask, useful for reporting fit quality.
        self.last_diagnostics = {}

    @staticmethod
    @ValidateCentroid
    def get_centroid(*args):
        """Returns the center of n number of microphones (centroid).

            Args:
                *args: (list) location of each n microphone

            Returns:
                (numpy array) the center of the microphones
        """
        microphone_array = np.array(*args)
        return np.sum(microphone_array, axis=0) / len(*args)

    def set_room_dimensions(self):
        """Returns the numpy array of the room dimensions with the format:
           Width, Depth, and Length.
           Note: all the dimensions are measured in meters.
           Default: Dimensions of Room (cm): [35, 22, 24]
           room_dim = np.array([0.34925, 0.219964, 0.2413])
        """
        return np.array([self.x_dim_max, self.y_dim_max, self.z_dim_max])

    @staticmethod
    @validate_get_mic_with_sound_data
    def get_mic_match_with_sound_data(mic_sound_data_and_loc_dict, *args):
        """Using the dictionary--with microphones as keys, and its
           corresponding sound data and location, get the data of
           specific microphones. Note: this is the look up.

            Args:
                mic_sound_data_and_loc_dict: dictionary of microphone,
                                             sound_data, and locations
                *args: (list) list of the microphones

            Returns:
                signal_list: list of the microphone signals
                mic_location: list of the microphone locations
        """

        signal_list, mic_location = [], []

        # Look for the microphone location and the microphone signal
        # in the list in the dictionary
        for arg in args:
            if arg in mic_sound_data_and_loc_dict.keys():
                mic_location.append(mic_sound_data_and_loc_dict.get(arg)[0])
                signal_list.append(mic_sound_data_and_loc_dict.get(arg)[1])

        return signal_list, mic_location

    @validate_difference_of_arrivals
    def get_difference_of_arrivals(self, signal_list, *mic_location):
        """Returns an azimuth and co-latitude for each pair of
           microphones combinations. Note: all angles are returned in radians

            Args:
                signal_list: (list) microphones signals
                *mic_location: (list) location of each microphone

            Returns:
                 doa.azimuth_recon: (float) Azimuth angle
                 doa.colatitude_recon: (float) Co-latitude angle
        """

        # Add n-microphone array in [x,y,z] order
        microphones = np.vstack(list(zip(*mic_location)))

        if self.transform:
            stft_signal = np.array([pra.stft(signal,
                                             self.fft_size,
                                             self.fft_size // 2,
                                             transform=np.fft.rfft).T
                                    for signal in signal_list])
        else:
            stft_signal = np.array([pra.transform.stft.analysis(signal,
                                                                self.fft_size,
                                                                self.fft_size // 2).T
                                    for signal in signal_list])

        # Construct the new DOA object
        # Note: Transpose order of microphones
        doa = pra.doa.algorithms.get(self.algo_name)(L=microphones.T,
                                                     fs=self.sampling_rate,
                                                     nfft=self.fft_size,
                                                     c=self.sound_speed,
                                                     num_src=self.num_sources,
                                                     max_four=4, dim=3,
                                                     n_grid=self.n_grid)

        doa.locate_sources(stft_signal, freq_range=self.freq_range)

        return doa.azimuth_recon, doa.colatitude_recon

    def get_estimates(self, sound_data, *mic_split):
        """Returns a single ray (origin, direction) for one microphone
           combination and its associated sound data: the DOA-estimated
           azimuth/colatitude are converted into a 3-D unit direction
           vector originating at the sub-array's centroid.

           Args:
               sound_data: (numpy array) the specific sound data for microphone
                           pairings split
               *mic_split: (list) the specific microphone pairings split

            Returns:
                (origin, direction): a pair of (3,) numpy arrays.
        """

        signal, mic_locations = self.get_mic_match_with_sound_data(sound_data,
                                                                   *mic_split)
        centroid = self.get_centroid(mic_locations)
        azimuth_recon, colatitude_recon = self.get_difference_of_arrivals(signal,
                                                                          mic_locations)

        direction = spherical_to_cartesian(azimuth_recon, colatitude_recon)
        # pyroomacoustics may return a length-1 array per angle (one per
        # num_src); flatten to a plain (3,) direction vector for num_src=1.
        direction = np.asarray(direction, dtype=float).reshape(-1)[:3]

        return np.asarray(centroid, dtype=float), direction

    def process_potential_estimates(self, all_sound_data, mic_groups=None):
        """Builds one ray per microphone group (computed in parallel), then
           triangulates them into a single estimated source location.

           Args:
               all_sound_data: (numpy array) the entire microphone signal data
               mic_groups: (list of tuples, optional) explicit microphone
                    groups to use, one ray computed per group -- e.g. the
                    mic names belonging to each of several physically
                    separate, spatially-distributed sub-arrays. This is
                    the recommended mode for real triangulation: keep each
                    group's own microphones close together (a few cm) so a
                    single DOA computation over that group is not corrupted
                    by spatial aliasing (which occurs once inter-mic
                    spacing approaches half a wavelength of the signal's
                    highest analyzed frequency), while the GROUPS themselves
                    are spread far apart across the room so their resulting
                    rays triangulate to a well-conditioned intersection.
                    If omitted, falls back to the legacy behavior: every
                    combination of `self.mic_combinations_number` mics drawn
                    from ALL available microphones (appropriate only when
                    all the mics belong to a single physical array whose
                    full aperture is already within the spatial-aliasing
                    limit for the signal's frequency content).

            Returns:
                (numpy array) the single estimated source location,
                re-centered to absolute room coordinates.
        """

        if mic_groups is not None:
            mic_list_comb = list(mic_groups)
        else:
            mics = ["".join(['mic', str(i+1)]) for i in range(len(list(all_sound_data.keys())))]
            mic_list_comb = list(combinations(mics, self.mic_combinations_number))

        # Note: earlier versions of this method computed a "splits" chunk
        # size (len(mic_list_comb) // number_of_mic_splits) and then
        # re-flattened fixed-size chunks with `range(self.number_of_mic_splits)`
        # x `range(splits)` -- whenever the combination count wasn't an
        # exact multiple of number_of_mic_splits, the leftover combinations
        # in the final (shorter) chunk were silently never visited/dropped.
        # Every combination in `mic_list_comb` is mapped across worker
        # processes directly below instead, so none are silently skipped
        # regardless of how evenly `number_of_mic_splits` divides the count.
        validate_splits(min(self.number_of_mic_splits, len(mic_list_comb)))

        sound_data_and_each_mic_combo = ((all_sound_data, combo) for combo in mic_list_comb)
        rays = MultiProcessingWithReturnValue(self.get_estimates,
                                              *sound_data_and_each_mic_combo).pooled()

        origins = np.array([r[0] for r in rays])
        directions = np.array([r[1] for r in rays])

        if self.triangulation_method == 'ls':
            estimate = triangulate_rays(origins, directions)
            weights = np.ones(len(origins))
        elif self.triangulation_method == 'ransac':
            estimate, inlier_mask = ransac_triangulate(
                origins, directions, min_samples=3,
                residual_threshold=0.05, max_trials=500)
            weights = inlier_mask.astype(float)
        else:  # 'huber' (default) -- robust to a modest fraction of bad rays
            estimate, weights = huber_weighted_triangulate(origins, directions)

        residuals = perpendicular_residuals(estimate, origins, directions)
        self.last_diagnostics = {
            'n_rays': len(origins),
            'residuals_m': residuals,
            'weights': weights,
            'mean_residual_m': float(np.mean(residuals)),
            'median_residual_m': float(np.median(residuals)),
        }

        # Re-center: rays were computed in the room-centered coordinate
        # frame (mic locations are stored relative to the room center), so
        # shift the final estimate back to absolute room coordinates.
        center_of_room = self.set_room_dimensions() / 2
        return np.add(center_of_room, estimate)

    def run_estimates(self, *args, mic_groups=None):
        """Runs process_potential_estimates to produce the single
           triangulated source-location estimate, plus fit diagnostics.

           Args:
               *args: the microphone/signal/location dict (see
                    `process_potential_estimates`).
               mic_groups: optional explicit microphone groups -- see
                    `process_potential_estimates` for when/why to use this
                    (spatially-distributed sub-arrays).

           Yields:
               (estimate, diagnostics): (3,) numpy array and a dict with
               per-ray residuals/weights, from `self.last_diagnostics`.
        """

        mic_info = args[0]
        estimate = self.process_potential_estimates(mic_info, mic_groups=mic_groups)
        yield estimate, self.last_diagnostics
