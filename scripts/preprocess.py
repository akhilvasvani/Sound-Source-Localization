# !/usr/bin/env python
"""In this script, preprocess will extract the sound data ond locations into
one dictionary."""

import sys
import pathlib
import scipy.io as sio

from scripts.validations import validate_file_path, validate_signal_data


class PrepareData:
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
                     Default: False
    """

    @validate_file_path
    def __init__(self, filepath, *args, default=False, recovered=False):
        """Initializes PrepareData with filepath, default, and recovered."""

        self.filepath = filepath
        self.default = default
        self.recovered = recovered

        self.s1_bool = True

        self._microphone_locations = args or None

    def set_microphone_locations(self):
        """Returns microphone locations list. The x dimension,
           y dimension, and z dimension serve as optional input
           arguments. Note: For the default case, the microphone
           locations are under a new coordinate system in relation
           to the center of the room
           (whose center = [(0.34925/2),(0.219964/2),(0.2413/2)] is the origin)

          Returns:
              List of lists which contains the microphone coordinates
        """

        if self.default:
            # Microphone x,y,z locations
            x_locations = [-0.102235, -0.052197, -0.027304]
            y_locations = [-0.109982]
            z_locations = [0.056388, 0.001524, -0.053340, -0.108204]

            return [[x, y, z] for x in x_locations
                    for y in y_locations for z in z_locations]

        return list(self._microphone_locations)

    def _read_mat_file(self, sample_filepath):
        """Reads in the .mat file and check if the file does in fact exist.

           Args:
                sample_filepath: (string) name of file path

           Returns:
               dictionary of microphone locations and signal data

            Raises:
                FileNotFoundError: if .mat file cannot be found
        """

        try:
            data = {key: value[0] for key, value in
                    sio.loadmat(sample_filepath).items() if 'mic' in key}
            return self._get_mic_signal_location(list(data.values()))

        except OSError:
            # Check if the python version is 3.6 or greater
            if sys.version_info[1] >= 6:
                if pathlib.Path(sample_filepath).resolve(strict=True):
                    pass
                raise FileNotFoundError("Error. File not found.") from None
            if pathlib.Path(sample_filepath).resolve():
                pass
            raise FileNotFoundError("Error. File not found.") from None

    def get_signal(self, name_of_source):
        """Retrieves the signal data (sound data) from the .mat file. If
           is_default is set to True, return the sound data depending on the
           specific sound source and cycle number.

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
                source_name_dict = {f'S{x}_Cycle{y}': [f'Recovered_S{x}/S{x}_Cycle{y}', f'S{x}']
                                    for x in range(1, 3) for y in range(24)}
            else:
                source_name_dict = {f'S{x}_Cycle{y}': [f'S{x}/S{x}_Cycle{y}', f'S{x}']
                                    for x in range(1, 3) for y in range(24)}

            if name_of_source not in source_name_dict.keys():
                raise NameError("{} name not in cycle list".format(name_of_source))

            # Match the correct data with the name
            full_data_file_path = "".join([self.filepath,
                                           source_name_dict.get(name_of_source)[0],
                                           ".mat"])

            data = sio.loadmat(full_data_file_path)
            return data.get(source_name_dict.get(name_of_source)[1])

        return is_default(self) if self.default and name_of_source \
            else self._read_mat_file(self.filepath)

    @validate_signal_data
    def _get_mic_signal_location(self, data):
        """Returns for each of the n microphones, its locations and associated
           signal.

            Args:
                data: (numpy array) the signal associated with each microphone

            Returns:
                signal_list: (list) list of the associated signals
                microphone locations: (list) list of the microphone locations
        """

        all_microphone_locations = self.set_microphone_locations()

        if len(all_microphone_locations) == len(data):

            # Each microphone location MUST match the corresponding microphone data
            all_mic_loc_and_data = list(zip(all_microphone_locations,
                                            (row for row in data)))

            # Dictionary of the microphone locations and their respective signals
            # The key is the specific microphone, and the value is a list--
            # the first is the microphone location, followed by the signal.
            # Note: order is mic number (from 1 -12), followed by
            # location of channel (to get actual signal)
            microphones_locations_and_signals_dict = {"".join(['mic',
                                                               str(j+1)]): all_mic_loc_and_data[j]
                                                      for j in range(len(all_mic_loc_and_data))}

            return microphones_locations_and_signals_dict

        return "Error. Mismatch in length of microphone location list " \
               "and length of signal list."

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

                # Microphone, microphone signal, location lists, S1_bool, and sound cycle
                yield self._get_mic_signal_location(self.get_signal(source_name)), \
                      self.s1_bool, source_name

        yield self.get_signal(None)
