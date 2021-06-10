# !/usr/bin/env python
"""This is the main driver file."""

from scripts.sound_source_localization import SoundSourceLocation
from experiment import ExperimentalMicData
from preprocess import PrepareData
# from scripts.determine_source import TrueSourceLocation


def main(experi=True):

    if not experi:
        head = '/home/akhil/Sound-Source-Localization/data/heart sound/raw/'
        method_name = 'SRP'

        test_data = PrepareData(head).load_file()

        for _ in range(2):
            sample_mic_signal_loc_dict, s1_bool = next(test_data)
            sound_cycle, source_estimates = SoundSourceLocation(head, method_name).run(sample_mic_signal_loc_dict,
                                                                                       s1_bool)
            print(sound_cycle, source_estimates)

    if experi:
        head = '/home/akhil/Sound-Source-Localization/data/CMU_ARCTIC/cmu_us_bdl_arctic/wav/'
        sample_filename = "".join([head, 'arctic_a0001.wav'])

        method_name = 'SRP'

        room_dimensions = [50/100, 50/100, 50/100]
        microphone_location = [15 / 100, 0 / 100, 3 / 100]
        source_location = [2.5 / 100, 4.5 / 100, 7.8 / 100]

        distance, *true_angles, output_file_name, mic_locs = ExperimentalMicData(sample_filename,
                                                                       room_dim=room_dimensions,
                                                                       source_dim=source_location,
                                                                       mic_location=microphone_location).run()

        sample_mic_signal_loc_dict = PrepareData(output_file_name, *mic_locs, default=False).load_file()
        a = next(sample_mic_signal_loc_dict)
        print(a)

    # ## OLD OLD OLD
    #
    # # Add in arguments to read in file
    # head = '/home/akhil/Sound-Source-Localization/data/raw/'
    #
    # method_name = 'SRP'
    #
    # src1 = SoundSourceLocation(head, method_name)
    # sound_cycle, source_estimates = src1.run()
    # # ts1 = TrueSourceLocation(method_name, sound_cycle, source_estimates)
    # # print(ts1.room_filter_out())
    #
    # # DEBUG:
    # # sound_cycle = 'S1_Cycle0'
    # # source_estimates_1 = read_csv('test_transform.csv')
    # # source_estimates_2 = read_csv('test_no_transform.csv')
    # # ts1 = TrueSourceLocation(method_name, sound_cycle, source_estimates_1)
    # # ts2 = TrueSourceLocation(method_name, sound_cycle, source_estimates_2)


if __name__ == '__main__':
    main(experi=False)
