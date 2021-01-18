# !/usr/bin/env python
"""This is the main driver file."""


from scripts.sound_source_localization import SoundSourceLocation
from scripts.determine_source import TrueSourceLocation


# def read_csv(filename):
#     import numpy as np
#     return np.genfromtxt(filename, delimiter=',')


def main():

    # Add in arguments to read in file
    head = '/home/akhil/Sound-Source-Localization/data/raw/'

    method_name = 'SRP'

    src1 = SoundSourceLocation(head, method_name)
    sound_cycle, source_estimates = src1.run()
    # ts1 = TrueSourceLocation(method_name, sound_cycle, source_estimates)
    # print(ts1.room_filter_out())

    # DEBUG:
    # sound_cycle = 'S1_Cycle0'
    # source_estimates_1 = read_csv('test_transform.csv')
    # source_estimates_2 = read_csv('test_no_transform.csv')
    # ts1 = TrueSourceLocation(method_name, sound_cycle, source_estimates_1)
    # ts2 = TrueSourceLocation(method_name, sound_cycle, source_estimates_2)



if __name__ == '__main__':
    main()
