# !/usr/bin/env python
"""This is the main driver file."""

# from scripts.sound_source_localization import SoundSourceLocation
from experiment import ExperimentalMicData
from preprocess import PrepareData
# from scripts.determine_source import TrueSourceLocation


def main():

    # head = '/home/akhil/Sound-Source-Localization/data/CMU_ARCTIC/cmu_us_bdl_arctic/wav/'
    # sample_filename = "".join([head, 'arctic_a0001.wav'])
    #
    # microphone_location = [15 / 100, 3 / 100, 0 / 100]
    # source_location = [2.5 / 100, 4.5 / 100, 7.8 / 100]
    #
    # distance, *true_angles, output_file_name = ExperimentalMicData(sample_filename,
    #                                              source_dim=source_location,
    #                                              mic_location=microphone_location).run()

    # Truth
    # test_data = PrepareData(output_file_name).load_file()
    # a = next(test_data)

    output_file_name = '/home/akhil/Sound-Source-Localization/scripts/output/test_first_fun.mat'

    test_data = PrepareData(output_file_name, default=False)
    b = test_data.load_file()
    print(*b)
    # a = next(b)
    # print(a)



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
    main()
