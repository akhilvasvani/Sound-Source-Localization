# !/usr/bin/env python
"""This is the main driver file."""

import os

from scripts.experiment import ExperimentalMicData
from scripts.preprocess import PrepareData
from scripts.sound_source_localization import SoundSourceLocation
from scripts.determine_source import DetermineSourceLocation

# TODO: Test CustomMicrophone


def main():

    head = '/home/akhil/Sound-Source-Localization/data/CMU_ARCTIC/cmu_us_bdl_arctic/wav/'
    sample_filename = "".join([head, 'arctic_a0001.wav'])

    _, tail = os.path.split(sample_filename)

    method_name = 'SRP'

    room_dimensions = [50/100, 50/100, 50/100]
    microphone_location = [15 / 100, 0 / 100, 3 / 100]
    source_location = [2.5 / 100, 4.5 / 100, 7.8 / 100]

    distance, *true_angles, output_file_name, converted_mic_locations, \
    sample_rate = ExperimentalMicData(sample_filename,
                                      number_of_mics=3,
                                      custom_mic_setup='square',
                                      room_dim=room_dimensions,
                                      source_dim=source_location,
                                      mic_location=microphone_location,
                                      n=3,
                                      phi=0.2,
                                      d=0.4).run(plot=True)
    test_data = PrepareData(output_file_name, *converted_mic_locations).load_file()
    sample_mic_signal_loc_dict = next(test_data)
    source_estimates = SoundSourceLocation(method_name,
                                           number_of_mic_splits=3,
                                           s1_bool=None,
                                           x_dim_max=room_dimensions[0],
                                           y_dim_max=room_dimensions[1],
                                           z_dim_max=room_dimensions[2]).run_estimates(sample_mic_signal_loc_dict)
    ts1 = DetermineSourceLocation(method_name, tail, *source_estimates,
                                  *converted_mic_locations,
                                  room_dim=room_dimensions).sprint()


if __name__ == '__main__':
    main()
