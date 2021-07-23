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
    """

    @validate_file_path
    def __init__(self, filepath, *args, recovered=False):
        """Initializes PrepareData with filepath, and recovered."""

        self.filepath = filepath
        self.recovered = recovered

        self.s1_bool = True

        self._microphone_locations = args or None

    def set_microphone_locations(self):
        """Returns microphone locations list. The x dimension,
           y dimension, and z dimension serve as optional input
           arguments. Note: the microphone locations are under
           a new coordinate system in relation to the center of
           the room.

          Returns:
              List of lists which contains the microphone coordinates
        """
        return list(self._microphone_locations)

    def load_file(self):
        """Loads in .mat file. Otherwise yield a list-- microphones, signals,
           microphone locations-- and S1 boolean.
        """
        yield self._read_mat_file(self.filepath)

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

    @validate_signal_data
    def _get_mic_signal_location(self, data):
        """Returns for each of the n microphones, its locations and associated
           signal.

            Args:
                data: (numpy array) the signal associated with each microphone

            Returns:
                signal_list: (list) list of the associated signals
                microphone locations: (list) list of the microphone locations

            Raises:
                ValueError: When the microphone location list does not match the
                            match the microphone signal list.
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

        raise ValueError("Error. Mismatch in length of microphone "
                         "location list and length of signal list.")
