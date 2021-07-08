# !/usr/bin/env python
"""This is the main driver file."""

import os
import numpy as np

from scripts.experiment import ExperimentalMicData
from scripts.preprocess import PrepareData
from scripts.sound_source_localization import SoundSourceLocation
from scripts.determine_source import DetermineSourceLocation


def main(experi=True):

    if not experi:
        head = '/home/akhil/Sound-Source-Localization/data/heart sound/raw/'
        method_name = 'SRP'

        test_data = PrepareData(head, default=True).load_file()

        for _ in range(2):
            sample_mic_signal_loc_dict, s1_or_not, sound_cycle = next(test_data)
            source_estimates = SoundSourceLocation(method_name,
                                                   s1_bool=s1_or_not,
                                                   default=True).run(sample_mic_signal_loc_dict)
            ts1 = DetermineSourceLocation(method_name, sound_cycle,
                                          *source_estimates, default=True).run()

    if experi:
        head = '/home/akhil/Sound-Source-Localization/data/CMU_ARCTIC/cmu_us_bdl_arctic/wav/'
        sample_filename = "".join([head, 'arctic_a0001.wav'])

        _, tail = os.path.split(sample_filename)

        method_name = 'SRP'

        room_dimensions = [50/100, 50/100, 50/100]
        microphone_location = [15 / 100, 0 / 100, 3 / 100]
        source_location = [2.5 / 100, 4.5 / 100, 7.8 / 100]

        distance, *true_angles, output_file_name, converted_mic_locs, sample_rate = ExperimentalMicData(sample_filename,
                                                                       room_dim=room_dimensions,
                                                                       source_dim=source_location,
                                                                       mic_location=microphone_location).run(plot=True)
        print(*converted_mic_locs)
        test_data = PrepareData(output_file_name, *converted_mic_locs).load_file()
        sample_mic_signal_loc_dict = next(test_data)
        source_estimates = SoundSourceLocation(method_name,
                                               number_of_mic_splits=3,
                                               s1_bool=None,
                                               x_dim_max=room_dimensions[0],
                                               y_dim_max=room_dimensions[1],
                                               z_dim_max=room_dimensions[2]).run(sample_mic_signal_loc_dict)
        ts1 = DetermineSourceLocation(method_name, tail, *source_estimates,
                                      np.subtract(np.array(microphone_location),
                                                  np.array(room_dimensions) / 2).tolist(),
                                      room_dim=room_dimensions).run()


if __name__ == '__main__':
    main(experi=True)
