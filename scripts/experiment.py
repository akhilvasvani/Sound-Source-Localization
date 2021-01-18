# !/usr/bin/env python
"""In this script, experiment will use the pyroomacoustics library to
create the mat file to be used in sound_source_localization"""

import numpy as np
import matplotlib.pyplot as plt

from scipy.io import wavfile, savemat
from mpl_toolkits.mplot3d import Axes3D

import pyroomacoustics as pra

# TODO:
#       2) Determine the angle, and distance source from microphones are
#       3) Edit the x, y, z axis to match the heart source project


class ExperimentalMicData(object):

    def __init__(self, filename, number_of_mics=4, **kwargs):
        self.filename = None or filename
        self.number_of_mics = number_of_mics

        *self.room_dim, = iter(kwargs.get('room_dim'))
        *self.source_dim, = iter(kwargs.get('source_dim'))
        *self.microphone_location, = iter(kwargs.get('mic_location'))

        self.room = None
        self.microphone_location_to_use = 0

    def _read_wav_file(self):
        fs, signal = wavfile.read(self.filename)
        return fs, signal

    def set_room(self, sample_fs):
        self.room = pra.ShoeBox(self.set_room_dimensions(), fs=sample_fs)

    def set_room_dimensions(self):
        """Returns the numpy array of the room dimensions with the format:
           Width, Depth, and Length.
           Note: all the dimensions are measured in meters.
           Default: Dimensions of Room (cm): [35, 22, 24]
           room_dim = np.array([0.34925, 0.219964, 0.2413])
        """
        return np.array(self.room_dim)

    def set_sound_source(self, sample_signal):
        """Add a source somewhere in the room"""
        self.room.add_source(self.source_dim, signal=sample_signal)

    def set_microphone(self, sample_fs):
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

    def _plot(self):

        # Create a Figure, label the axis, Title the plot, and set the limits
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')
        ax.set_xlabel('Width (X axis)')
        ax.set_ylabel('Depth (Z axis)')
        ax.set_zlabel('Length (Y axis)')
        ax.set_title("All the Clusters")
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

    @staticmethod
    def _save_file(dict_to_save):
        name_to_save_file = "".join(["output/", "test_first_fun", ".mat"])
        savemat(name_to_save_file, dict_to_save)
        print("Saved file: {}".format(name_to_save_file))

    def run(self):

        fs, signal = self._read_wav_file()

        self.set_room(fs)

        self.set_sound_source(signal)
        self.set_microphone(fs)

        # # DEBUG:
        # self._plot()

        mic_list = ['mic'+str(i) for i in range(1, self.number_of_mics + 1)]
        test_dict = dict(zip(mic_list, self.room.mic_array.signals))

        self._save_file(test_dict)


head = '/home/akhil/Sound-Source-Localization/data/CMU_ARCTIC/cmu_us_bdl_arctic/wav/'
sample_filename = "".join([head, 'arctic_a0001.wav'])

ExperimentalMicData(sample_filename, room_dim=[4, 6, 9],
                    source_dim=[2.5, 4.5, 7.8], mic_location=[2, 1.5, 0]).run()
