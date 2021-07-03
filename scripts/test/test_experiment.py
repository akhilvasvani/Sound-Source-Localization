import unittest

from scripts.experiment import ExperimentalMicData


class ExperimentalMicDataTestCase(unittest.TestCase):
    def setUp(self):
        head = '/home/akhil/Sound-Source-Localization/data/'
        sample_filename = "".join([head, 'CMU_ARCTIC/cmu_us_bdl_arctic/wav/',
                                   'arctic_a0001.wav'])

        room_dimensions = [50/100, 50/100, 50/100]
        microphone_location = [15 / 100, 0 / 100, 3 / 100]
        source_location = [2.5 / 100, 4.5 / 100, 7.8 / 100]

        self.src1 = ExperimentalMicData(sample_filename,
                                        room_dim=room_dimensions,
                                        source_dim=source_location,
                                        mic_location=microphone_location)

class InitTestCase(ExperimentalMicDataTestCase):


if __name__ == '__main__':
    unittest.main()
