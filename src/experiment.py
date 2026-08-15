# !/usr/bin/env python
"""In this script, experiment will use the pyroomacoustics library to
convert a wav file to a mat file to be used in sound_source_localization."""

import math
import os
import pathlib
import sys
import uuid
import numpy as np
import matplotlib.pyplot as plt

from scipy.io import wavfile, savemat
from mpl_toolkits.mplot3d import Axes3D

import pyroomacoustics as pra

from tools.validations import validate_room_source_dim_and_mic_loc, \
    validate_file_path
from tools.utilities import CustomMicrophoneSetUp
from src.audio_source import load_source_signal


class ExperimentalMicData:
    """ExperimentalMicData creates an simulation using the Pyroomaoustics library
       to record the sound data from the microphones into a mat file.

        Attributes:
            filename: (string) name of the file
            number_of_mics: (integer) the number of microphones to use
            **kwargs: the room dimensions and the source dimensions and
                      microphone locations
    """

    @validate_file_path
    @validate_room_source_dim_and_mic_loc
    def __init__(self, filename, number_of_mics=4, custom_mic_setup=None,
                 **kwargs):
        """Initializes ExperimentalMicData with filename, number_of_mics, and
           **kwargs."""
        self.filename = filename
        self.number_of_mics = number_of_mics

        *self.room_dim, = iter(kwargs.get('room_dim'))
        *self.source_dim, = iter(kwargs.get('source_dim'))
        *self.microphone_location, = iter(kwargs.get('mic_location'))

        # Multi-cluster support (new): a single CustomMicrophoneSetUp call
        # always produces a COPLANAR sub-array (every generated microphone
        # shares the same z-height -- see tools/utilities.py). A DOA
        # estimate from mics that all lie in one horizontal plane suffers
        # an inherent elevation (colatitude) mirror ambiguity: a source at
        # colatitude theta and one at (180 - theta) relative to that plane
        # are physically indistinguishable from arrival-time differences
        # alone. This was verified empirically: a single 6-mic circular
        # array at a fixed height produced colatitude estimates matching
        # (180 - true_colatitude) to within a fraction of a degree.
        # `mic_clusters`, if supplied, places several independent
        # sub-arrays at different (x, y, z) centers (e.g. near different
        # corners/heights of the room); microphone COMBINATIONS that mix
        # mics from different, non-coplanar clusters are then genuinely
        # 3-D and are not subject to this ambiguity.
        self.mic_clusters_spec = kwargs.get('mic_clusters')
        self.custom_mic_setup = custom_mic_setup
        # `mic_group_names`: list of tuples of 1-indexed mic names
        # ('mic1', 'mic2', ...), one tuple per physical cluster, in the
        # same global mic numbering used for the saved .mat file and
        # `PrepareData`/`SoundSourceLocation`. Populated only when
        # `mic_clusters` is used; consumers pass this straight to
        # `SoundSourceLocation.run_estimates(..., mic_groups=...)` to get
        # exactly one triangulation ray per physical cluster.
        self.mic_group_names = None

        if self.mic_clusters_spec is not None:
            cluster_mic_arrays = []
            mic_group_names = []
            total_mics = 0
            for cluster in self.mic_clusters_spec:
                cluster = dict(cluster)
                center = cluster.pop('center')

                if 'positions' in cluster:
                    # Explicit relative [dx, dy, dz] offsets from `center`,
                    # for a small, deliberately NON-planar physical mic
                    # cluster (e.g. a compact tetrahedral mount): unlike
                    # CustomMicrophoneSetUp's 2-D pre-arranged layouts
                    # (linear/circular/square/poisson/spiral), which always
                    # share one z-height per cluster, this lets a single
                    # cluster's own microphones disambiguate elevation
                    # (colatitude) on their own, without needing to mix
                    # microphones from other, far-apart clusters -- which
                    # would otherwise create spatial aliasing (inter-mic
                    # spacing approaching/exceeding half a wavelength).
                    offsets = np.asarray(cluster.pop('positions'), dtype=float)
                    sub_array = (np.asarray(center, dtype=float)[:, None] + offsets.T)
                    bounds = np.asarray(self.room_dim, dtype=float)
                    mics_xyz = sub_array.T
                    out_of_bounds = (mics_xyz < 0.0) | (mics_xyz > bounds[None, :])
                    if np.any(out_of_bounds):
                        bad = mics_xyz[np.any(out_of_bounds, axis=1)].tolist()
                        raise ValueError(
                            f"Error. Cluster at center {center} has microphone(s) "
                            f"outside room bounds {self.room_dim}: {bad}."
                        )
                else:
                    custom = cluster.pop('custom')
                    n_mics = cluster.pop('n')
                    sub_array = CustomMicrophoneSetUp(custom, center, n_mics,
                                                      self.room_dim,
                                                      **cluster).run()

                n_this_cluster = sub_array.shape[-1]
                mic_group_names.append(tuple(
                    "".join(['mic', str(total_mics + i + 1)])
                    for i in range(n_this_cluster)))
                cluster_mic_arrays.append(sub_array)
                total_mics += n_this_cluster

            self.mics = np.hstack(cluster_mic_arrays)
            self.number_of_mics = total_mics
            self.mic_group_names = mic_group_names
        elif self.custom_mic_setup is not None:
            custom_mic_kwargs = {k: v for k, v in kwargs.items() if k not in ['room_dim',
                                                                              'source_dim',
                                                                              'mic_location',
                                                                              'absorption',
                                                                              'max_order',
                                                                              'mic_clusters']}
            # Bug fix: this used to pass `len(self.room_dim)` (i.e. just the
            # integer 3) as "room_dimension", which made it IMPOSSIBLE for
            # CustomMicrophoneSetUp to bounds-check generated microphone
            # positions against the room. Pass the actual physical room
            # bounds instead, so out-of-room microphone layouts are caught
            # immediately with a clear error instead of crashing deep
            # inside pyroomacoustics's reflection computation.
            self.mics = CustomMicrophoneSetUp(self.custom_mic_setup,
                                              self.microphone_location,
                                              self.number_of_mics,
                                              self.room_dim,
                                              **custom_mic_kwargs).run()
            if self.custom_mic_setup == 'square':
                self.number_of_mics *= kwargs.get('n')
        else:
            self.mics = self.microphone_location

        self.room = None

        # Reverberation configuration. Previously these were never set,
        # so `pra.ShoeBox` silently fell back to library defaults
        # (max_order=1 to a handful of reflections, no explicit
        # absorption/material), meaning the shipped example never
        # deliberately produced meaningful reverberation. Both are now
        # explicit and configurable via kwargs.
        self.absorption = kwargs.get('absorption', 0.25)
        self.max_order = kwargs.get('max_order', 10)

        self.dist = 0
        self.true_azimuth, self.true_colatitude = 0, 0

        # Configurable output directory (defaults to the original "output/"
        # relative path for CLI scripts -- src/main.py, validation/run_validation.py --
        # so their behavior is unchanged). The deployed app (src/pipeline.py)
        # passes an APP_DATA_DIR-derived path instead, see src/paths.py.
        # The filename includes a random suffix so concurrent runs (e.g. two
        # browser tabs hitting the deployed Streamlit app at once) can't
        # clobber each other's scratch .mat file mid-run.
        self.output_dir = kwargs.get('output_dir', 'output')
        self.name_to_save_file = os.path.join(
            self.output_dir, "test_first_fun_{}.mat".format(uuid.uuid4().hex[:12]))

    def _read_wav_file(self):
        """Reads in the source audio file (.wav or .flac) and checks that
           it does in fact exist. Multi-channel source files are mixed
           down to mono, since this is the single "dry" signal emitted
           by one simulated point source (see `src.audio_source` for the
           generic loader, and `src.audio_source.load_multichannel_recording`
           for the separate case of an already multi-channel *recording*
           that should bypass room simulation entirely).

           Note: this used to call `scipy.io.wavfile.read` directly,
           which only supports .wav and silently mishandles some wav
           sub-formats soundfile handles correctly (e.g. float32 wav).
           It now delegates to `src.audio_source.load_source_signal`,
           which also accepts .flac.

           Returns:
               fs: (integer) sampling frequency
               signal: (numpy array) mono signal data

            Raises:
                FileNotFoundError: if the file cannot be found
        """
        try:
            rate, signal = load_source_signal(self.filename, mono=True)
            return rate, signal
        except OSError:
            # Check if the python version is 3.6 or greater
            if sys.version_info[1] >= 6:
                if pathlib.Path(self.filename).resolve(strict=True):
                    pass
                raise FileNotFoundError("Error. File not found.") from None
            if pathlib.Path(self.filename).resolve():
                pass
            raise FileNotFoundError("Error. File not found.") from None

    def set_room_dimensions(self):
        """Returns the numpy array of the room dimensions with the format:
           Width, Depth, and Length. Note: all the dimensions are measured
           in centimeters.
        """
        return np.array(self.room_dim)

    def setup_room(self, sample_fs):
        """Sets up the simulated room (shoebox) with the room dimensions
           and the sampling rate of the sound source. Explicitly sets an
           absorption/material and a max reflection order so the room
           actually produces deliberate, meaningful reverberation instead
           of relying on pyroomacoustics's bare defaults."""
        self.room = pra.ShoeBox(self.set_room_dimensions(), fs=sample_fs,
                                materials=pra.Material(self.absorption),
                                max_order=self.max_order)

    def set_sound_source(self, sample_signal):
        """Add a source somewhere in the room"""
        self.room.add_source(self.source_dim, signal=sample_signal)

    def set_microphone(self, sample_fs):
        """Sets the microphone location inside the pra.shoebox. At the moment,
           the microphone arrangement is in a linear order.

           Args:
               sample_fs: (float) sampling rate

            Raises:
                ValueError: if the microphone location is empty.
        """
        self.room.add_microphone_array(pra.MicrophoneArray(self.mics,
                                                           fs=sample_fs))
        self.room.simulate()

    def determine_angle_and_distance(self):
        """Finds the azimuth and colatitude angles in relation to the center of
           the microphone array (centroid). In addition, determines the
           distance between the centroid and the sound source."""

        # Bug fix: this used to divide by `len(self.room_dim)` (always 3,
        # the number of spatial dimensions) instead of the actual number of
        # microphones, which is only coincidentally correct when there are
        # exactly 3 microphones. Divide by the true microphone count.
        centroid = np.sum(self.mics, axis=-1) / self.mics.shape[-1]
        self.dist = math.sqrt(sum([(a - b)**2 for a, b in zip(list(centroid),
                                                              self.source_dim)]))
        difference = np.subtract(np.array(self.source_dim), centroid)
        self.true_azimuth = np.arctan2(difference[1], difference[0])
        # Bug fix: `np.arctan` only returns values in (-90, 90) degrees, so
        # it can never represent a true colatitude greater than 90 degrees
        # (i.e. any source below the microphone-array plane) -- it silently
        # produces a wrong angle (verified: off by up to 180 degrees) whenever
        # difference[-1] (z) is negative. `np.arctan2` with the correct
        # numerator/denominator ordering handles the full [0, 180] degree
        # range and matches the same colatitude convention used everywhere
        # else in this project (see src/triangulation.py).
        self.true_colatitude = np.arctan2(math.sqrt(difference[0]**2 +
                                                    difference[1]**2), difference[-1])

        return self.dist, self.true_azimuth * 180 / np.pi, \
               self.true_colatitude * 180 / np.pi

    def _plot(self):
        """Plots the microphones and sound source on a 3-d plot."""

        # Create a Figure, label the axis, Title the plot, and set the limits
        fig = plt.figure()
        axes = fig.add_subplot(111, projection='3d')
        axes.set_xlabel('Width (X axis)')
        axes.set_ylabel('Depth (Z axis)')
        axes.set_zlabel('Length (Y axis)')
        axes.set_title("Demo: Microphone and Source Location")
        axes.set_xlim(0, self.room_dim[0])
        axes.set_ylim(0, self.room_dim[1])
        axes.set_zlim(0, self.room_dim[2])  # for 3-d

        # Plot the microphones
        axes.scatter(self.mics[0], self.mics[1],
                     self.mics[2],
                     label='Microphones 1-{:d}'.format(self.number_of_mics))

        # Plot the S1 or S2 location
        axes.scatter(self.source_dim[0], self.source_dim[1],
                     self.source_dim[2], 'b', label='Source Location')
        axes.legend()
        plt.show()

    def _save_file(self, dict_to_save):
        savemat(self.name_to_save_file, dict_to_save)
        print("Saved file: {}".format(self.name_to_save_file))

    def run(self, plot=False):
        """Sets the sound source and microphones. Records, and saves data
           into a mat file. Plots the microphones and sound source in a 3-d
           plot if necessary. Note: the microphone locations are recorded
           under a new coordinate system in relation to the center of the room.
           """

        sampling_rate, signal = self._read_wav_file()

        self.setup_room(sampling_rate)

        self.set_sound_source(signal)
        self.set_microphone(sampling_rate)

        if plot:
            self._plot()

        mic_list = ['mic'+str(i) for i in range(1, self.number_of_mics + 1)]
        test_dict = dict(zip(mic_list, self.room.mic_array.signals))

        self._save_file(test_dict)

        # Note: transposed microphones, so that one row is x,y,z order
        converted_mic_locations = np.subtract(self.mics.T,
                                              self.set_room_dimensions()/2).tolist()

        return self.determine_angle_and_distance(), self.name_to_save_file, \
               converted_mic_locations, sampling_rate, self.mic_group_names
