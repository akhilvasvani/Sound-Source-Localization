# !/usr/bin/env python
"""In this script, experiment will use the pyroomacoustics library to
convert a wav file to a mat file to be used in sound_source_localization."""

import math
import pathlib
import sys
import numpy as np
import matplotlib.pyplot as plt

from scipy.io import wavfile, savemat
from mpl_toolkits.mplot3d import Axes3D

import pyroomacoustics as pra

from scripts.validations import validate_room_source_dim_and_mic_loc, \
    validate_file_path


class ExperimentalMicData(object):
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
    def __init__(self, filename, number_of_mics=4, **kwargs):
        """Initializes ExperimentalMicData with filename, number_of_mics, and
           **kwargs."""
        self.filename = filename
        self.number_of_mics = number_of_mics

        *self.room_dim, = iter(kwargs.get('room_dim'))
        *self.source_dim, = iter(kwargs.get('source_dim'))
        *self.microphone_location, = iter(kwargs.get('mic_location'))

        self.room = None
        self.microphone_location_to_use = 0
        self.dist = 0
        self.true_azimuth, self.true_colatitude = 0, 0

        self.output_file_name = None

    def _read_wav_file(self):
        """Reads in the .wav file and check if the file does in fact exist.

           Returns:
               fs: (integer) sampling frequency
               signal: (numpy array) signal data

            Raises:
                FileNotFoundError: if .mat file cannot be found
        """
        try:
            fs, signal = wavfile.read(self.filename)
            return fs, signal
        except OSError:
            # Check if the python version is 3.6 or greater
            if sys.version_info[1] >= 6:
                if pathlib.Path(self.filename).resolve(strict=True):
                    pass
                raise FileNotFoundError("Error. File not found.")
            else:
                if pathlib.Path(self.filename).resolve():
                    pass
                raise FileNotFoundError("Error. File not found.")

    def set_room_dimensions(self):
        """Returns the numpy array of the room dimensions with the format:
           Width, Depth, and Length. Note: all the dimensions are measured
           in centimeters.
        """
        return np.array(self.room_dim)

    def set_room(self, sample_fs):
        self.room = pra.ShoeBox(self.set_room_dimensions(), fs=sample_fs)

    def set_sound_source(self, sample_signal):
        """Add a source somewhere in the room"""
        self.room.add_source(self.source_dim, signal=sample_signal)

    def set_microphone(self, sample_fs):
        """Sets the microphone location inside the pra.shoebox. At the moment,
           the microphone arrangement is in a linear order.

           Args:
               sample_fs: (float) sample frequency

            Raises:
                ValueError: if the microphone location is empty.
        """

        # Create a linear array with 4 microphones
        # with angle 0 degrees and inter mic distance 10 cm
        if len(self.room_dim) == 3:  # 3-D
            self.microphone_location_to_use = self.microphone_location[:-1]
            self.R = pra.linear_2D_array(self.microphone_location_to_use, self.number_of_mics, 0, 0.1)
            self.R = np.array(list(self.R) + [np.zeros(self.number_of_mics)])
        elif 0 < len(self.room_dim) < 3:  # 2-D and 1-D
            self.microphone_location_to_use = self.microphone_location
            self.R = pra.linear_2D_array(self.microphone_location_to_use, self.number_of_mics, 0, 0.1)
        else:
            raise ValueError("Error. Need a microphone location to use")

        self.room.add_microphone_array(pra.MicrophoneArray(self.R, fs=sample_fs))
        self.room.simulate()

    def determine_angle_and_distance(self):
        """Finds the azimuth and colatitude angles in relation to the center of
           the microphone array (centroid). In addition, determines the
           distance between the centroid and the sound source."""

        centroid = np.sum(self.R, axis=-1) / len(self.room_dim)
        self.dist = math.sqrt(sum([(a - b)**2 for a, b in zip(list(centroid), self.source_dim)]))
        difference = np.subtract(np.array(self.source_dim), centroid)
        self.true_azimuth = np.arctan2(difference[1], difference[0])
        self.true_colatitude = np.arctan(math.sqrt(difference[0]**2 + difference[1]**2)/(difference[-1]))

        return self.dist, self.true_azimuth * 180 / np.pi, self.true_colatitude * 180 / np.pi,

    def _plot(self):
        """Plots the microphones and sound source on a 3-d plot."""

        # Create a Figure, label the axis, Title the plot, and set the limits
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')
        ax.set_xlabel('Width (X axis)')
        ax.set_ylabel('Depth (Z axis)')
        ax.set_zlabel('Length (Y axis)')
        ax.set_title("Demo: Microphone and Source Location")
        ax.set_xlim(0, self.room_dim[0])
        ax.set_ylim(0, self.room_dim[1])
        ax.set_zlim(0, self.room_dim[2])  # for 3-d

        # Plot the microphones
        ax.scatter(self.R[0],
                   self.R[1],
                   self.R[2],
                   label='Microphones 1-{:d}'.format(self.number_of_mics))

        # Plot the S1 or S2 location
        ax.scatter(self.source_dim[0], self.source_dim[1],
                   self.source_dim[2], 'b', label='Source Location')
        ax.legend()
        plt.show()

    def _save_file(self, dict_to_save):
        self.name_to_save_file = "".join(["output/", "test_first_fun", ".mat"])
        savemat(self.name_to_save_file, dict_to_save)
        print("Saved file: {}".format(self.name_to_save_file))

    def run(self, plot=False):
        """Sets the sound source and microphones. Records, and saves data
           into a mat file. Plots the microphones and sound source in a 3-d
           plot if necessary. Note: the microphone locations are recorded
           under a new coordinate system in relation to the center of the room.

           """

        fs, signal = self._read_wav_file()

        self.set_room(fs)

        self.set_sound_source(signal)
        self.set_microphone(fs)

        if plot:
            self._plot()

        mic_list = ['mic'+str(i) for i in range(1, self.number_of_mics + 1)]
        test_dict = dict(zip(mic_list, self.room.mic_array.signals))

        self._save_file(test_dict)

        # Note: transposed microphone locations, so list is in x, y, z order
        reconverted_mic_locs = np.subtract(self.R.T, self.set_room_dimensions()/2).tolist()

        return self.determine_angle_and_distance(), self.name_to_save_file, reconverted_mic_locs, fs
