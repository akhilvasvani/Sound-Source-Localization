# !/usr/bin/env python
"""In this script, run_sound_source will find the all potential candidates for
where the sound source is located."""

import numpy as np
import pyroomacoustics as pra

from itertools import combinations

from scripts.utils import MultiProcessingWithReturnValue
from scripts.validations import validate_difference_of_arrivals, \
    ValidateCentroid, validate_get_mic_with_sound_data, validate_splits,\
    validate_instance_type


# TODO:
#    1) Determine how to use the "new" updated transform attribute in method,
#       get_difference_of_arrivals--i.e. will the deprecated version impact
#       the desired result?


class SoundSourceLocation(object):
    """SoundSourceLocation finds the potential location points of a
       sound source using a distance of arrival (DOA) method via a
       combination of microphone pairings.

    Attributes:
        algo_name: (string) specific distance of arrival (DOA) method
        num_sources: (integer) number of sources to find. Default is 1
        number_of_mic_splits: (integer) the number of splits for
                      multiprocessing. Default: 5
        sound_speed: (float) specific speed of sound
        mic_combinations_number: (integer) number of microphone to use

        fs: (integer) specific sampling frequency. Default is 16000
        fft_size: (integer) specific FFT size. Default is 256
        freq_range: (list) specific frequency range to isolate for.
                    Default range is 0 - 256
        tol: (float) specific tolerance to use for distance between
             each point in the radius
        radius: (numpy array) values for radius

        s1_bool: (boolean) indicates whether to find S1 or S2 sound source
        x_dim_max: (float) the maximum x length (in meters) - ex. width
        y_dim_max: (float) the maximum y length (in meters) -- ex. height
        z_dim_max: (float) the maximum z length (in meters) -- ex. depth
        transform: (boolean) DEBUG -- figure out whether to use the new version
           or the deprecated version
    """

    def __init__(self, algo_name, num_sources=1, number_of_mic_splits=5,
                 sampling_rate=16000, s1_bool=True, x_dim_max=0.34925,
                 y_dim_max=0.219964, z_dim_max=0.2413, transform=False, default=False):
        """Initializes SoundSourceLocation with algo_name, num_sources."""

        self.algo_name = algo_name
        self.num_sources = num_sources
        self.number_of_mic_splits = number_of_mic_splits

        # Constants
        self.sound_speed = 30
        self.mic_combinations_number = 3

        self.fs = sampling_rate
        self.fft_size = 256
        self.freq_range = [0, 250]
        self.tol = 1e-3  # 3e-3
        self.radius = np.arange(0, 0.5, self.tol)[:, np.newaxis]

        self.s1_bool = s1_bool

        self.x_dim_max = x_dim_max
        self.y_dim_max = y_dim_max
        self.z_dim_max = z_dim_max

        # TODO: DEBUG
        self.transform = transform

        self.default = default

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
        m = np.vstack(list(zip(*mic_location)))

        # TODO: Figure out this deprecation
        # Create an array of a short fourier transformed frequency signal
        if self.transform:
            x = np.array([pra.stft(signal, self.fft_size, self.fft_size // 2,
                                   transform=np.fft.rfft).T for signal in signal_list])
        else:
            x = np.array([pra.transform.stft.analysis(signal, self.fft_size,
                                                      self.fft_size // 2).T for signal in signal_list])

        # Construct the new DOA object
        doa = pra.doa.algorithms.get(self.algo_name)(L=m, fs=self.fs,
                                                     nfft=self.fft_size,
                                                     c=self.sound_speed,
                                                     num_src=self.num_sources,
                                                     max_four=4, dim=3,
                                                     n_grid=1000)

        doa.locate_sources(x, freq_range=self.freq_range)

        return doa.azimuth_recon, doa.colatitude_recon

    def split_and_conquer(self, the_centroid, cartesian_arr):
        """Returns the cartesian array multiplied by the radius and recenter
           for each source when looking for multiple sources.

            Args:
                the_centroid: the specific centroid associated with each
                              microphone combination
                cartesian_arr: the cartesian array before the multiplication
                               of the radius

            Returns:
                (numpy array) cartesian coordinates for each source

            Raises:
                TypeError: Cartesian array is not a numpy array
            """

        if not validate_instance_type(cartesian_arr, np.ndarray):
            raise TypeError("Error. Cartesian array is not a numpy array")

        # Split up the array into the separate parts based on how many sources there are
        array_split = np.vsplit(cartesian_arr.T, self.num_sources)

        # Multiply each respective part by the radius and recenter it with the centroid
        for i in range(self.num_sources):
            array_split[i] = self.radius * array_split[i] + np.array(the_centroid)[np.newaxis, :]

        return np.vstack(array_split)

    def get_estimates(self, sound_data, *mic_split):
        """Returns the numpy array of location estimates for each microphone
           combination pairing and associated sound data. First, the signal
           and microphone locations are acquired. Next the centroid is gathered.
           Finally, the azimuth and co-latitude angles are generated and converted
           to cartesian coordinates, which are then multiplied by the radius.

           Args:
               sound_data: (numpy array) the specific sound data for microphone
                           pairings split
               *mic_split: (list) the specific microphone pairings split

            Returns:
                (numpy array) Array of the estimates
        """

        signal, mic_locations = self.get_mic_match_with_sound_data(sound_data,
                                                                   *mic_split)
        centroid = self.get_centroid(mic_locations)
        azimuth_recon, colatitude_recon = self.get_difference_of_arrivals(signal,
                                                                      mic_locations)

        cartesian_coordinates = np.array([np.cos(azimuth_recon)*np.sin(colatitude_recon),
                                          np.sin(azimuth_recon)*np.sin(colatitude_recon),
                                          np.cos(colatitude_recon)])

        if self.num_sources > 1:
            return self.split_and_conquer(centroid, cartesian_coordinates)
        return self.radius * cartesian_coordinates.T + np.array(centroid)[np.newaxis, :]

    def process_potential_estimates(self, all_sound_data):
        """Returns all the estimates for all the microphone combinations
           and re-centers according to the room dimension specifications.
           Microphone combinations are split up into equal chunks and
           to be used in multiple threads to decrease time to find estimates.

           Args:
               all_sound_data: (numpy array) the entire microphone signal data

            Returns:
                numpy array of the potential estimates re-centered according
                to the room specifications.
        """

        if self.default:

            if self.s1_bool:
                # List of specific microphones to quickly find S1
                # (where M and T are located)
                mics = ["".join(['mic', str(i)]) for i in [2, 3, 6, 7, 10, 11]]

            else:
                # List of specific microphones to quickly find S2
                # (where P and A are located)
                mics = ["".join(['mic', str(i)]) for i in [1, 2, 5, 6, 9, 10]]
        else:
            # microphone locations?
            mics = ["".join(['mic', str(i+1)]) for i in range(len(list(all_sound_data.keys())))]

        mic_list = list(combinations(mics, self.mic_combinations_number))

        splits = validate_splits(len(mic_list) // self.number_of_mic_splits)

        # Split up the mic list into chunks of the same size
        mic_split_list = [mic_list[i * splits:(i+1) * splits]
                          for i in range((len(mic_list)+splits-1) // splits)]

        sound_data_and_mic_split_combinations = ((all_sound_data,
                             mic_split_list[i][j]) for j in range(splits) for i in range(self.number_of_mic_splits))
        all_estimates = np.array(MultiProcessingWithReturnValue(self.get_estimates,
                                                                *sound_data_and_mic_split_combinations).pooled())

        # Reshape them to (_, 3) which is proper format
        potential_sources = np.reshape(all_estimates,
                                       (all_estimates.shape[0]*all_estimates.shape[1],
                                        all_estimates.shape[2]))

        # Re-center the points, add the x,y,z location of the center of the
        # room to the obtained point
        center_of_room = self.set_room_dimensions() / 2

        # Reconvert all the potential source points
        # Format: (Width, Depth, Length)
        return np.add(center_of_room, potential_sources)

    def run(self, *args):
        """Runs all the functions."""

        mic_info = args[0]
        yield self.process_potential_estimates(mic_info)
