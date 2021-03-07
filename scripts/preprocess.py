# !/usr/bin/env python
"""In this script, preprocess will extract the sound data ond locations into
one list."""

import sys
import pathlib
import scipy.io as sio

from scripts.validations import validate_file_path, validate_signal_data


class PrepareData(object):
    """PrepareData extracts the sound data from the .mat file and lines up
       the sound data (the signals) with the corresponding microphone and
       the microphone's location.

        Attributes:
            filepath: (string) filepath of where the data is located
            recovered: (boolean) specifies whether to use recovered sound
                       cycles. Default is False
            s1_bool: (boolean) specifies whether to look for S1 or S2
                     sound source. Default: True
            default: (boolean) Used for my original project purpose.
    """

    @validate_file_path
    def __init__(self, filepath, recovered=False):
        """Initializes PrepareData with filepath and recovered."""

        self.filepath = filepath
        self.recovered = recovered

        self.s1_bool = True
        self.default = True

    @staticmethod
    def _set_microphone_locations(**kwargs):
        """Returns microphone locations list. The x dimension,
           y dimension, and z dimension serve as optional input
           arguments.

           Example:
               mic_list = set_microphone_locations(x_locations = [-0.102235, -0.052197, -0.027304],
                                 y_locations = [-0.109982],
                                 z_locations = [0.056388, 0.001524, -0.053340, -0.108204])

           Args:
               **kwargs: takes in as input the x dimension,
                         y dimension, and z dimension
                         inputs.
          Returns:
              List of lists which has the coordinates
        """

        if not kwargs:
            # Microphone x,y,z locations
            x_locations = [-0.102235, -0.052197, -0.027304]
            y_locations = [-0.109982]
            z_locations = [0.056388, 0.001524, -0.053340, -0.108204]

            # Return the microphone list
            return [[x, y, z] for x in x_locations for y in y_locations for z in z_locations]

        list_of_dimension_names = list(kwargs.keys())

        x_locations = kwargs.get(list_of_dimension_names[0])
        y_locations = kwargs.get(list_of_dimension_names[1])
        z_locations = kwargs.get(list_of_dimension_names[2])

        return [[x, y, z] for x in x_locations for y in y_locations for z in z_locations]

    def _read_mat_file(self, sample_filepath):
        try:
            sio.loadmat(sample_filepath)
        except OSError:
            # Check if the file does in fact exist

            # Check if the python version is 3.6 or greater
            if sys.version_info[1] >= 6:
                if pathlib.Path(sample_filepath).resolve(strict=True):
                    pass
                raise FileNotFoundError("Error. File not found.")
            else:
                if pathlib.Path(sample_filepath).resolve():
                    pass
                raise FileNotFoundError("Error. File not found.")

    def get_signal(self, name_of_source):
        """Reads in the .mat file. However, if is_default is True,
           returns the sound data depending on the specific sound source
           and cycle number.

            Args:
                name_of_source: (string) specifies each sound cycle

            Returns:
                sound_data: (numpy array) matrix of all the sound data

            Raises:
                TypeError: Recovered is not a boolean type
                NameError: name_of_source is not in the dictionary of
                            source names
        """

        def is_default(self):
            if not isinstance(self.recovered, bool):
                raise TypeError("recovered is supposed to be a boolean.\n {}"
                                " is not a boolean.".format(self.recovered))

            # Create a dictionary with all cycles:
            # Recovered S1 and S2 (top),
            # Regular S1 and S1 (bottom)
            if self.recovered:
                source_name_dict = {f'S{x}_Cycle{y}': [f'Recovered_S{x}/S{x}_Cycle{y}',
                                                       f'S{x}'] for x in range(1, 3) for y in range(24)}
            else:
                source_name_dict = {f'S{x}_Cycle{y}': [f'S{x}/S{x}_Cycle{y}', f'S{x}']
                                    for x in range(1, 3) for y in range(24)}

            if name_of_source not in source_name_dict.keys():
                raise NameError("{} name not in cycle list".format(name_of_source))

            # Match the correct data with the name
            full_data_file_path = "".join([self.filepath,
                                           source_name_dict.get(name_of_source)[0]])

            # TODO: Need to figure out how to use _read_mat_file here,
            #       but for now this works
            data = sio.loadmat(full_data_file_path)
            return data.get(source_name_dict.get(name_of_source)[1])

        return is_default(self) if self.default and name_of_source else self._read_mat_file(self.filepath)

    @validate_signal_data
    def _get_mic_signal_location(self, data):
        """Returns for each of the n microphones, its locations and associated
           signal. Note: The microphone locations are under a new coordinate
           system in relation to the center of the box
           (whose center = [(0.34925/2),(0.219964/2),(0.2413/2)] is the origin)

            Args:
                data: (numpy array) the signal associated with each microphone

            Returns:
                signal_list: (list) list of the associated signals
                microphone locations: (list) list of the microphone locations

            Raises:
                 ValueError: The signal list associated with
                             each microphone is empty
                 ValueError: The signal list associated with
                             each microphone contains None
                 ValueError: The signal list associated with
                             each microphone contains an empty string
                 ValueError: The microphone list is empty
        """

        # if not data.tolist() or (data.size == 1 and None in data.tolist()):
        #     raise ValueError("Error. The signal is empty.")
        #
        # if None in data:
        #     raise ValueError('Error. The signal contains None.')
        #
        # if "" in data.tolist():
        #     raise ValueError('Error. The signal contains an empty string.')

        # Numbered 1 - 12
        all_microphone_locations = self._set_microphone_locations()

        if len(all_microphone_locations) == len(data):

            # Each microphone location MUST match the corresponding microphone data
            all_microphone_locations_and_data = list(zip(all_microphone_locations,
                                                         (row for row in data)))

            # Dictionary of the microphone locations and their respective signals
            # The key is the specific microphone, and the value is a list--
            # the first is the microphone location, followed by the signal.
            # Note: order is mic number (from 1 -12), followed by
            # location of channel (to get actual signal)
            microphones_locations_and_signals_dict = {"".join(['mic', str(j+1)]): all_microphone_locations_and_data[j]
                                                      for j in range(len(all_microphone_locations_and_data))}

            return microphones_locations_and_signals_dict

        return f"Error. Mismatch in length of microphone location list " \
               f"and length of signal list."

    def load_file(self):
        """Loads in .mat file. Otherwise yield a list-- microphones, signals,
           microphone locations-- and S1 boolean.
        """

        if self.default:
            cycles = ["".join(['Cycle', str(k)]) for k in range(24)]
            sound_sources = ["".join(['S', str(k)]) for k in range(1, 3)]
            sound_list = ["_".join([sound_source, cycle])
                          for sound_source in sound_sources for cycle in cycles]

            for source_name in sound_list:
                if source_name in ["".join(["_".join(['S2', 'Cycle']),
                                            str(j)]) for j in range(24)]:
                    self.s1_bool = False

                # Microphone, microphone signal, location lists, and S1_bool
                yield self._get_mic_signal_location(self.get_signal(source_name)), \
                      self.s1_bool

        return self.get_signal(None)
